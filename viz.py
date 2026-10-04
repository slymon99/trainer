import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import polars as pl

    from trainer.config import active_profile, profile_names
    from trainer.store import Store

    alt.data_transformers.disable_max_rows()

    CATEGORICAL_COLORS = [
        "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
        "#e87ba4", "#008300", "#4a3aa7", "#e34948",
    ]


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


    return (
        CATEGORICAL_COLORS,
        Store,
        active_profile,
        alt,
        mo,
        pl,
        profile_names,
        style_chart,
    )


@app.cell
def _(active_profile, mo, profile_names):
    # Several profiles and none active is exactly when a picker is needed —
    # start on the first rather than failing the cell.
    try:
        _current = active_profile().name
    except SystemExit:
        _current = next(iter(profile_names()), None)
    athlete = mo.ui.dropdown(options=profile_names(), value=_current, label="Athlete")
    athlete
    return (athlete,)


@app.cell
def _(Store, active_profile, athlete):
    store = Store(active_profile(athlete.value).warehouse)
    return (store,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Training dashboard

    Pulled straight from the athlete's local warehouse via `Store` —
    nothing here calls intervals.icu or Strava. Fitness/fatigue/form, weekly
    load, time by activity type, and aerobic efficiency over the last year.
    """)
    return


@app.cell
def _(store):
    wellness = store.sql(
        """
        SELECT date, ctl, atl, ctl - atl AS form, resting_hr, hrv, weight
        FROM iv_wellness
        WHERE ctl IS NOT NULL
        ORDER BY date
        """
    ).pl()
    wellness.tail()

    return (wellness,)


@app.cell
def _(alt, pl, style_chart, wellness):
    _pmc_long = wellness.unpivot(
        index="date", on=["ctl", "atl"], variable_name="metric", value_name="value"
    ).with_columns(
        pl.col("metric").replace({"ctl": "Fitness (CTL)", "atl": "Fatigue (ATL)"})
    )

    _lines = (
        alt.Chart(_pmc_long)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("value:Q", title="Load"),
            color=alt.Color(
                "metric:N",
                title=None,
                scale=alt.Scale(
                    domain=["Fitness (CTL)", "Fatigue (ATL)"],
                    range=["#2a78d6", "#eb6834"],
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[alt.Tooltip("date:T"), "metric:N", alt.Tooltip("value:Q", format=".1f")],
        )
    )

    _form = (
        alt.Chart(wellness)
        .mark_area(opacity=0.3, line={"strokeWidth": 1})
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("form:Q", title="Form"),
            color=alt.condition(alt.datum.form >= 0, alt.value("#2a78d6"), alt.value("#e34948")),
            tooltip=[alt.Tooltip("date:T"), alt.Tooltip("form:Q", title="Form (TSB)", format=".1f")],
        )
    )

    pmc_chart = style_chart(
        (_lines.properties(height=220) & _form.properties(height=90)).properties(
            title="Fitness, fatigue, and form"
        )
    )
    pmc_chart

    return


@app.cell
def _(alt, store, style_chart):
    weekly_load = store.sql(
        """
        SELECT date_trunc('week', date) AS week, sum(suffer_score) AS load
        FROM strava_activities
        WHERE suffer_score IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """
    ).pl()

    weekly_chart = style_chart(
        alt.Chart(weekly_load)
        .mark_bar(color="#2a78d6", cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X("week:T", title=None),
            y=alt.Y("load:Q", title="Weekly load (Relative Effort)"),
            tooltip=[
                alt.Tooltip("week:T", title="Week of"),
                alt.Tooltip("load:Q", title="Load", format=".0f"),
            ],
        )
        .properties(title="Weekly training load (Strava Relative Effort)", height=220)
    )
    weekly_chart

    return


@app.cell
def _(CATEGORICAL_COLORS, alt, store, style_chart):
    by_type = store.sql(
        """
        SELECT type, sum(moving_time) / 3600.0 AS hours, count(*) AS n
        FROM activities
        WHERE type IS NOT NULL
        GROUP BY 1
        ORDER BY hours DESC
        """
    ).pl()

    type_chart = style_chart(
        alt.Chart(by_type)
        .mark_bar(cornerRadiusTopRight=2, cornerRadiusBottomRight=2)
        .encode(
            x=alt.X("hours:Q", title="Hours"),
            y=alt.Y("type:N", sort="-x", title=None),
            color=alt.Color("type:N", scale=alt.Scale(range=CATEGORICAL_COLORS), legend=None),
            tooltip=["type", alt.Tooltip("hours:Q", format=".1f"), "n"],
        )
        .properties(title="Time by activity type", height=220)
    )
    type_chart

    return


@app.cell
def _(alt, store, style_chart):
    efficiency = store.sql(
        """
        SELECT date, average_watts, average_heartrate,
               average_watts / NULLIF(average_heartrate, 0) AS ef
        FROM activities
        WHERE type IN ('Ride', 'VirtualRide')
          AND average_watts IS NOT NULL AND average_heartrate IS NOT NULL
          AND average_watts > 0
        ORDER BY date
        """
    ).pl()

    ef_chart = style_chart(
        alt.Chart(efficiency)
        .mark_circle(size=60, opacity=0.7, color="#2a78d6")
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("ef:Q", title="Efficiency factor (W / HR)"),
            tooltip=[
                alt.Tooltip("date:T"),
                alt.Tooltip("average_watts:Q", title="Watts", format=".0f"),
                alt.Tooltip("average_heartrate:Q", title="HR", format=".0f"),
                alt.Tooltip("ef:Q", format=".2f"),
            ],
        )
        .properties(title="Aerobic efficiency over time (rides only)", height=240)
    )
    ef_chart

    return


if __name__ == "__main__":
    app.run()
