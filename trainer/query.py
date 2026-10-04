"""Ad-hoc SQL against the local warehouse.

    pixi run sql                                  # what's stored, and how much
    pixi run sql --schema iv_wellness             # columns of one table
    pixi run sql "SELECT date, ctl FROM iv_wellness ORDER BY date DESC LIMIT 7"
    pixi run sql --profile alex                   # another athlete's warehouse

`pixi run sql` strips the quotes inside its argument, so for SQL containing
string literals use one of these instead:

    pixi run python -m trainer.query "SELECT * FROM iv_events WHERE date > '2026-08-01'"
    echo "SELECT ..." | pixi run sql -

Tables and the joined views are all in scope — see docs/data-store.md.
"""

import argparse
import csv
import sys

from trainer import tables
from trainer.config import active_profile
from trainer.store import VIEWS, Store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("query", nargs="?", help="SQL to run, or '-' to read stdin")
    parser.add_argument("--schema", nargs="?", const="", metavar="TABLE", help="show columns")
    parser.add_argument("--csv", action="store_true", help="emit CSV instead of a table")
    parser.add_argument("--limit", type=int, default=100, help="max rows to display")
    parser.add_argument("--profile", help="athlete profile (default: the active one)")
    args = parser.parse_args(argv)

    store = Store(active_profile(args.profile).warehouse)

    if args.schema is not None:
        return _schema(store, args.schema)

    query = sys.stdin.read() if args.query == "-" else args.query
    if not query:
        return _summary(store)

    result = store.sql(query)
    if args.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(result.columns)
        writer.writerows(result.fetchall())
    else:
        result.show(max_rows=args.limit)
    return 0


def _summary(store: Store) -> int:
    print(f"{'table':<22}{'rows':>10}  span")
    for name, rows, first, last in store.summary():
        print(f"{name:<22}{rows:>10,}  {f'{first} → {last}' if rows else 'empty'}")
    print(f"\nviews: {', '.join(VIEWS)}")
    print("Field reference: docs/data-store.md")
    return 0


def _schema(store: Store, name: str) -> int:
    if name and name not in tables.TABLES and name not in VIEWS:
        print(f"unknown table {name!r}", file=sys.stderr)
        return 1
    for table in [name] if name else [*tables.TABLES, *VIEWS]:
        spec = tables.TABLES.get(table)
        print(f"\n{table}" + ("  (view)" if spec is None else ""))
        if spec is not None and spec.doc:
            print(f"  {spec.doc}")
        for column, dtype, *_ in store.sql(f"DESCRIBE {table}").fetchall():
            print(f"    {column:<26} {dtype}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
