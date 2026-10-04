import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import math

    import altair as alt
    import marimo as mo
    import polars as pl

    from trainer.config import active_profile
    from trainer.store import Store

    alt.data_transformers.disable_max_rows()


    def style_chart(chart):
        return (
            chart.configure_view(strokeWidth=0)
            .configure_axis(
                gridColor="#e1e0d9",
                domainColor="#c3c2b7",
                tickColor="#c3c2b7",
                labelColor="#52514e",
                titleColor="#52514e",
            )
            .configure_title(color="#0b0b0b", fontSize=14)
            .configure_legend(labelColor="#52514e", titleColor="#52514e")
        )

    return Store, active_profile, alt, math, mo, pl, style_chart


@app.cell
def _(Store, active_profile):
    ATHLETE = "sabrina"
    store = Store(active_profile(ATHLETE).warehouse)
    return ATHLETE, store


@app.cell
def _(ATHLETE, mo):
    mo.md(f"""
    # {ATHLETE.title()} — HRV and resting HR

    How unusual is the past week, measured against her own recent normal?

    **Method.** HRV is compared on the log scale (lnRMSSD), as it's right-skewed.
    Each 7-day rolling mean is set against the **60 days immediately before that
    week** — mean and day-to-day SD — so the baseline never contains the days being
    judged. Deviations are in units of that baseline daily SD. Following Plews et al.,
    ±0.5 SD is the smallest worthwhile change; beyond 1 SD is clearly outside her
    normal range. These are screening signals, not a diagnosis (see `docs/stats.md`).
    """)
    return


@app.cell
def _(pl, store):
    BASELINE_DAYS = 60
    WINDOW_DAYS = 7

    _rhr = pl.col("resting_hr").cast(pl.Float64)
    wellness = (
        pl.from_arrow(
            store.sql(
                "SELECT date, hrv, resting_hr, sleep_secs / 3600.0 AS sleep_h "
                "FROM iv_wellness ORDER BY date"
            ).arrow()
        )
        .with_columns(ln_hrv=pl.col("hrv").log())
        .with_columns(
            ln_hrv_7d=pl.col("ln_hrv").rolling_mean(WINDOW_DAYS, min_samples=5),
            rhr_7d=_rhr.rolling_mean(WINDOW_DAYS, min_samples=5),
            # baseline ends the day before the 7-day window starts
            base_ln=pl.col("ln_hrv").rolling_mean(BASELINE_DAYS, min_samples=30).shift(WINDOW_DAYS),
            base_ln_sd=pl.col("ln_hrv").rolling_std(BASELINE_DAYS, min_samples=30).shift(WINDOW_DAYS),
            base_rhr=_rhr.rolling_mean(BASELINE_DAYS, min_samples=30).shift(WINDOW_DAYS),
            base_rhr_sd=_rhr.rolling_std(BASELINE_DAYS, min_samples=30).shift(WINDOW_DAYS),
        )
        .with_columns(
            hrv_7d=pl.col("ln_hrv_7d").exp(),
            hrv_z=(pl.col("ln_hrv_7d") - pl.col("base_ln")) / pl.col("base_ln_sd"),
            rhr_z=(pl.col("rhr_7d") - pl.col("base_rhr")) / pl.col("base_rhr_sd"),
        )
    )
    latest = wellness.row(-1, named=True)
    week_start = wellness.filter(pl.col("date") <= latest["date"]).item(-WINDOW_DAYS, "date")
    return BASELINE_DAYS, latest, week_start, wellness


@app.cell
def _(BASELINE_DAYS, latest, math, mo, pl, week_start, wellness):
    # each day of the past week against the single 60-day baseline that precedes it
    week = (
        wellness.filter(pl.col("date") >= week_start)
        .with_columns(
            hrv_day_z=(pl.col("ln_hrv") - latest["base_ln"]) / latest["base_ln_sd"],
            rhr_day_z=(pl.col("resting_hr") - latest["base_rhr"]) / latest["base_rhr_sd"],
        )
        .select(
            "date",
            "hrv",
            pl.col("hrv_day_z").round(2).alias("hrv vs baseline (SD)"),
            "resting_hr",
            pl.col("rhr_day_z").round(2).alias("RHR vs baseline (SD)"),
            pl.col("sleep_h").round(1).alias("sleep (h)"),
        )
    )
    mo.vstack([
        mo.md(
            f"### The past week\n"
            f"Baseline is the {BASELINE_DAYS} days before {week_start}: "
            f"HRV {math.exp(latest['base_ln']):.1f} ms (geometric mean), "
            f"RHR {latest['base_rhr']:.1f} ± {latest['base_rhr_sd']:.1f} bpm."
        ),
        week,
    ])
    return


@app.cell
def _(latest, pl, week_start, wellness):
    _before = wellness.filter(pl.col("date") < week_start)


    def _last(df, cond):
        """Most recent date before this week meeting ``cond``, or None."""
        hit = df.filter(cond).select(pl.col("date").max()).item()
        return hit


    context = {
        "hrv_7d": latest["hrv_7d"],
        "hrv_z": latest["hrv_z"],
        "rhr_7d": latest["rhr_7d"],
        "rhr_z": latest["rhr_z"],
        # same-sized windows that ended before this week began, so none overlap it
        "hrv_7d_last": _last(_before, pl.col("hrv_7d") <= latest["hrv_7d"]),
        "hrv_z_last": _last(_before, pl.col("hrv_z") <= latest["hrv_z"]),
        "rhr_7d_last": _last(_before, pl.col("rhr_7d") >= latest["rhr_7d"]),
        "rhr_z_last": _last(_before, pl.col("rhr_z") >= latest["rhr_z"]),
        "hrv_z_rank": wellness.select((pl.col("hrv_z") <= latest["hrv_z"]).mean()).item(),
        "rhr_z_rank": wellness.select((pl.col("rhr_z") >= latest["rhr_z"]).mean()).item(),
        "first_day": wellness.item(0, "date"),
        # how long the 7-day HRV mean has been more than 1 SD under baseline
        "hrv_run_start": wellness.filter(
            pl.col("date") > _last(wellness, pl.col("hrv_z") > -1)
        ).item(0, "date") if latest["hrv_z"] <= -1 else None,
    }
    context
    return (context,)


@app.cell
def _(context, latest, mo):
    def _ago(d):
        if d is None:
            return f"not since records start ({context['first_day']})"
        return f"{d} ({(latest['date'] - d).days} days ago)"


    mo.md(f"""
    ### Summary (7 days to {latest['date']})

    | | 7-day mean | vs 60-day baseline | windows this extreme | last time this bad |
    |---|---|---|---|---|
    | **HRV** | {context['hrv_7d']:.1f} ms | **{context['hrv_z']:+.2f} SD** | {context['hrv_z_rank']:.1%} | z: {_ago(context['hrv_z_last'])}<br>raw: {_ago(context['hrv_7d_last'])} |
    | **RHR** | {context['rhr_7d']:.1f} bpm | **{context['rhr_z']:+.2f} SD** ({context['rhr_7d'] - latest['base_rhr']:+.1f} bpm) | {context['rhr_z_rank']:.1%} | z: {_ago(context['rhr_z_last'])}<br>raw: {_ago(context['rhr_7d_last'])} |

    The 7-day HRV mean has sat more than 1 SD below baseline since
    **{context['hrv_run_start']}**. "Windows this extreme" is the share of all 7-day windows in
    the year at or beyond today's deviation.
    """)
    return


@app.cell
def _(alt, latest, pl, style_chart, week_start, wellness):
    _recent = wellness.filter(pl.col("date") >= latest["date"] - pl.duration(days=180))
    _band = _recent.with_columns(
        hrv_lo=(pl.col("base_ln") - pl.col("base_ln_sd")).exp(),
        hrv_hi=(pl.col("base_ln") + pl.col("base_ln_sd")).exp(),
        rhr_lo=pl.col("base_rhr") - pl.col("base_rhr_sd"),
        rhr_hi=pl.col("base_rhr") + pl.col("base_rhr_sd"),
    )
    _week = alt.Chart(pl.DataFrame({"start": [week_start], "end": [latest["date"]]})).mark_rect(
        color="#eda100", opacity=0.15
    ).encode(x="start:T", x2="end:T")


    def _panel(lo, hi, daily, rolling, title, color):
        _base = alt.Chart(_band).encode(x=alt.X("date:T", title=None))
        return alt.layer(
            _week,
            _base.mark_area(color=color, opacity=0.12).encode(
                y=alt.Y(f"{lo}:Q", title=title, scale=alt.Scale(zero=False)), y2=f"{hi}:Q"
            ),
            _base.mark_circle(color=color, opacity=0.35, size=18).encode(
                y=f"{daily}:Q",
                tooltip=[alt.Tooltip("date:T"), alt.Tooltip(f"{daily}:Q", title=title)],
            ),
            _base.mark_line(color=color, strokeWidth=2).encode(
                y=f"{rolling}:Q",
                tooltip=[alt.Tooltip("date:T"), alt.Tooltip(f"{rolling}:Q", title="7-day mean", format=".1f")],
            ),
        ).properties(width="container", height=200)


    style_chart(
        alt.vconcat(
            _panel("hrv_lo", "hrv_hi", "hrv", "hrv_7d", "HRV (ms)", "#2a78d6"),
            _panel("rhr_lo", "rhr_hi", "resting_hr", "rhr_7d", "Resting HR (bpm)", "#e34948"),
        ).properties(title="Last 6 months — daily values, 7-day mean, baseline ±1 SD band, past week shaded")
    )
    return


@app.cell
def _(alt, pl, style_chart, wellness):
    _z = wellness.select(
        "date",
        pl.col("hrv_z").alias("HRV (low is worse)"),
        pl.col("rhr_z").alias("RHR (high is worse)"),
    ).unpivot(index="date", variable_name="metric", value_name="z").drop_nulls()

    _lines = alt.Chart(_z).mark_line(strokeWidth=1.5).encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("z:Q", title="7-day mean vs 60-day baseline (SD)"),
        color=alt.Color(
            "metric:N",
            title=None,
            scale=alt.Scale(range=["#2a78d6", "#e34948"]),
            legend=alt.Legend(orient="top"),
        ),
        tooltip=[alt.Tooltip("date:T"), "metric:N", alt.Tooltip("z:Q", format="+.2f")],
    )
    _rules = alt.Chart(pl.DataFrame({"z": [-2, -1, 0, 1, 2]})).mark_rule(
        color="#c3c2b7", strokeDash=[3, 3]
    ).encode(y="z:Q")

    style_chart(
        (_rules + _lines).properties(
            width="container", height=240, title="Deviation from her own baseline, full year"
        )
    )
    return


if __name__ == "__main__":
    app.run()
