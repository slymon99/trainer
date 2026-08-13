"""The local warehouse: normalised parquet on disk, queried with DuckDB.

Layout — one directory per table, partitioned by month of the row's date:

    data/warehouse/iv_wellness/month=2026-08/data_0.parquet

Partitioning is for *incremental writes*, not query speed: a sync touches one
or two months and rewrites only those files. Everything is small enough that
queries just scan the lot.

Writes are merge-on-key. Re-syncing a window you already have is a no-op that
costs one file rewrite, so scripts can be re-run freely — which is the point of
storing this at all, given Strava allows 100 requests per 15 minutes.

    from trainer.store import Store

    store = Store()
    store.sql("SELECT date, ctl, atl FROM iv_wellness ORDER BY date DESC LIMIT 7").show()
"""

import shutil
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa

from trainer import tables
from trainer.config import ROOT
from trainer.tables import Table

WAREHOUSE = ROOT / "data" / "warehouse"

# Views defined over the raw tables, so the common joins are one name, not a
# paragraph of SQL. Kept here rather than in tables.py because they are query
# conveniences, not storage.
VIEWS = {
    "activities": """
        -- Every completed activity, intervals.icu's index joined to Strava's
        -- measurements. The id is the same number in both systems.
        SELECT
            COALESCE(s.id, i.id)                        AS id,
            COALESCE(s.date, i.date)                    AS date,
            COALESCE(s.name, i.name)                    AS name,
            COALESCE(s.type, i.type)                    AS type,
            i.source,
            COALESCE(s.moving_time, i.moving_time)      AS moving_time,
            s.elapsed_time,
            s.distance,
            s.total_elevation_gain,
            s.average_watts,
            COALESCE(s.weighted_average_watts, i.icu_weighted_avg_watts) AS np,
            s.max_watts,
            s.average_heartrate,
            s.max_heartrate,
            s.average_cadence,
            s.kilojoules,
            s.trainer,
            i.icu_training_load,
            i.icu_intensity,
            i.icu_eftp,
            s.has_detail,
            s.lap_count
        FROM iv_activities i
        FULL OUTER JOIN strava_activities s ON s.id = i.id
    """,
    "planned_vs_actual": """
        -- The prescription next to what was done, on intervals.icu's own
        -- pairing. Planned sessions with no activity show NULL actuals.
        SELECT
            e.date,
            e.name                  AS planned_name,
            e.icu_training_load     AS planned_load,
            e.moving_time           AS planned_secs,
            e.description           AS prescription,
            a.id                    AS activity_id,
            a.name                  AS actual_name,
            a.moving_time           AS actual_secs,
            a.np                    AS actual_np,
            a.average_heartrate     AS actual_avg_hr,
            a.lap_count
        FROM iv_events e
        LEFT JOIN activities a ON a.id = e.paired_activity_id
        WHERE e.category = 'WORKOUT'
    """,
}


class Store:
    def __init__(self, root: Path | str = WAREHOUSE):
        self.root = Path(root)
        self._con: duckdb.DuckDBPyConnection | None = None
        self._empties: dict[str, pa.Table] = {}

    # --- layout ------------------------------------------------------------

    def table_dir(self, table: Table) -> Path:
        return self.root / table.name

    def _glob(self, table: Table) -> str:
        """Read pattern. Partitioned tables nest one level; the rest don't."""
        pattern = "*/*.parquet" if table.partitioned else "*.parquet"
        return str(self.table_dir(table) / pattern)

    def _files(self, table: Table) -> list[Path]:
        pattern = "*/*.parquet" if table.partitioned else "*.parquet"
        return sorted(self.table_dir(table).glob(pattern))

    # --- reading -----------------------------------------------------------

    @property
    def con(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            self._con = duckdb.connect()
            for table in tables.TABLES.values():
                self._define(table)
            for name, body in VIEWS.items():
                self._con.execute(f"CREATE OR REPLACE VIEW {name} AS {body}")
        return self._con

    def _define(self, table: Table) -> None:
        """(Re)define a table's view over its parquet files.

        Unioning by name against an empty table of the declared schema means a
        column added to tables.py later reads back as NULL from older files
        instead of failing the query.
        """
        con = self._con
        empty = f"{table.name}__schema"
        self._empties[empty] = table.schema.empty_table()
        con.register(empty, self._empties[empty])

        columns = ", ".join(f.name for f in table.schema)
        if self._files(table):
            body = (
                f"SELECT {columns} FROM ("
                f"  SELECT * FROM read_parquet('{self._glob(table)}', union_by_name=true)"
                f"  UNION ALL BY NAME SELECT * FROM {empty}"
                f")"
            )
        else:
            body = f"SELECT {columns} FROM {empty}"
        con.execute(f"CREATE OR REPLACE VIEW {table.name} AS {body}")

    def sql(self, query: str, *params) -> duckdb.DuckDBPyRelation:
        """Run a query against the warehouse. Every table and view is in scope."""
        return self.con.sql(query, params=list(params) if params else None)

    def max_date(self, table: str) -> date | None:
        """Newest date held for a table — the watermark an incremental sync resumes from."""
        spec = tables.get(table)
        if spec.date_column is None:
            return None
        row = self.sql(f"SELECT max({spec.date_column}) FROM {spec.name}").fetchone()
        return row[0] if row else None

    def ids(self, table: str, column: str = "id", where: str = "true") -> set[str]:
        rows = self.sql(f"SELECT DISTINCT {column} FROM {table} WHERE {where}").fetchall()
        return {r[0] for r in rows if r[0] is not None}

    def count(self, table: str) -> int:
        return self.sql(f"SELECT count(*) FROM {table}").fetchone()[0]

    def summary(self) -> list[tuple]:
        out = []
        for name, spec in tables.TABLES.items():
            date_col = spec.date_column or "NULL"
            row = self.sql(
                f"SELECT count(*), min({date_col})::VARCHAR, max({date_col})::VARCHAR FROM {name}"
            ).fetchone()
            out.append((name, *row))
        return out

    # --- writing -----------------------------------------------------------

    def write(
        self,
        table: str,
        payloads: list[dict],
        *,
        replace_range: tuple[date, date] | None = None,
    ) -> int:
        """Merge API payloads into a table, returning the number merged in.

        Rows are keyed by the table's `key`; an incoming row replaces the held
        one. `replace_range` additionally drops held rows in that date span
        before merging, which is how a re-fetched window notices deletions —
        a workout removed from the calendar has to disappear here too.
        """
        spec = tables.get(table)
        rows = spec.rows(payloads)
        if not rows and replace_range is None:
            return 0

        arrow = pa.Table.from_pylist(rows, schema=spec.schema)
        source = f"{spec.name}__incoming"
        self._empties[source] = arrow
        self.con.register(source, arrow)
        try:
            self._merge(spec, source, replace_range)
        finally:
            self.con.unregister(source)
            self._empties.pop(source, None)
        return len(rows)

    def _merge(
        self,
        spec: Table,
        source: str,
        replace_range: tuple[date, date] | None,
    ) -> None:
        con = self.con
        columns = ", ".join(f.name for f in spec.schema)
        key = ", ".join(spec.key)
        partitions = self._partitions(spec, source, replace_range)

        # Held rows are pulled in only for the partitions being rewritten, so a
        # sync costs one month of I/O rather than the whole table.
        keep = f"{_partition_filter(spec, partitions)}"
        if replace_range is not None:
            keep += f" AND NOT ({spec.date_column} BETWEEN ? AND ?)"
        params = list(replace_range) if replace_range is not None else []

        # Materialised before the COPY, which overwrites the files being read.
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE _merged AS
            SELECT {columns} FROM (
                SELECT *, row_number() OVER (PARTITION BY {key} ORDER BY _incoming DESC) AS _rn
                FROM (
                    SELECT {columns}, true AS _incoming FROM {source}
                    UNION ALL
                    SELECT {columns}, false AS _incoming FROM {spec.name} WHERE {keep}
                )
            ) WHERE _rn = 1
            """,
            params,
        )

        self.table_dir(spec).mkdir(parents=True, exist_ok=True)
        if spec.partitioned:
            self._copy_partitioned(spec, partitions)
        else:
            con.execute(
                f"COPY (SELECT * FROM _merged ORDER BY {key}) "
                f"TO '{self.table_dir(spec) / 'data.parquet'}' (FORMAT PARQUET)"
            )
        con.execute("DROP TABLE _merged")
        self._define(spec)

    def _copy_partitioned(self, spec: Table, partitions: set[str]) -> None:
        con = self.con
        # OVERWRITE_OR_IGNORE replaces the files in the partitions this write
        # touches and leaves every other month alone; plain OVERWRITE would
        # empty the whole table directory first.
        con.execute(
            f"""
            COPY (
                SELECT *, strftime({spec.date_column}, '%Y-%m') AS month
                FROM _merged ORDER BY {", ".join(spec.key)}
            ) TO '{self.table_dir(spec)}'
            (FORMAT PARQUET, PARTITION_BY (month), OVERWRITE_OR_IGNORE)
            """
        )
        # A partition emptied by replace_range writes no file, so the stale one
        # would survive. Clear those directories explicitly.
        surviving = {
            r[0]
            for r in con.execute(
                f"SELECT DISTINCT strftime({spec.date_column}, '%Y-%m') FROM _merged"
            ).fetchall()
        }
        for month in partitions - surviving:
            shutil.rmtree(self.table_dir(spec) / f"month={month}", ignore_errors=True)

    def _partitions(
        self,
        spec: Table,
        source: str,
        replace_range: tuple[date, date] | None,
    ) -> set[str]:
        """Months this write touches: those in the incoming rows, plus every
        month the replaced range spans (which may now be empty)."""
        if not spec.partitioned:
            return set()
        months = {
            r[0]
            for r in self.con.execute(
                f"SELECT DISTINCT strftime({spec.date_column}, '%Y-%m') FROM {source}"
            ).fetchall()
            if r[0] is not None
        }
        if replace_range is not None:
            start, end = replace_range
            cursor = start.replace(day=1)
            while cursor <= end:
                months.add(cursor.strftime("%Y-%m"))
                cursor = (cursor.replace(day=28) + timedelta(days=7)).replace(day=1)
        return months


def _partition_filter(spec: Table, partitions: set[str]) -> str:
    if not spec.partitioned:
        return "true"
    if not partitions:
        return "false"
    listed = ", ".join(f"'{m}'" for m in sorted(partitions))
    return f"strftime({spec.date_column}, '%Y-%m') IN ({listed})"
