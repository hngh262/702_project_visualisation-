"""Professional Streamlit dashboard for the BUSINFO 702 tourism project."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="NZ Tourism Resilience",
    page_icon="🇳🇿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Accessible, colour-blind-friendly palette used consistently across views.
ISLAND_COLOURS = {"North Island": "#2563EB", "South Island": "#EA580C"}
NEUTRAL = "#64748B"
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DATA_DIR = Path(__file__).resolve().parent

st.markdown(
    """
    <style>
      .block-container {max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem;}
      [data-testid="stMetric"] {
        background: #F8FAFC; border: 1px solid #E2E8F0;
        border-radius: 12px; padding: 1rem;
      }
      [data-testid="stMetricLabel"] {color: #475569;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_csv(filename: str, required: set[str], numeric: list[str]) -> pd.DataFrame:
    """Load, validate and type an exported SQLite result."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(filename)

    frame = pd.read_csv(path)
    frame.columns = frame.columns.str.strip()
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{filename} is missing: {', '.join(sorted(missing))}")

    text_columns = frame.select_dtypes(include="object").columns
    frame[text_columns] = frame[text_columns].apply(lambda col: col.str.strip())
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


try:
    vulnerability = load_csv(
        "vulnerability_results.csv",
        {
            "RTOName", "Island", "InternationalSpendSharePct",
            "Peak3MonthSpendSharePct", "VulnerabilityScore", "PeakMonths",
        },
        ["InternationalSpendSharePct", "Peak3MonthSpendSharePct", "VulnerabilityScore"],
    )
    buffer = load_csv(
        "domestic_buffer_results.csv",
        {
            "RTOName", "Island", "LowDemandMonths", "VisitorDiffPct",
            "SpendDiffPct", "GuestNightsDiffPct",
        },
        ["LowDemandMonths", "VisitorDiffPct", "SpendDiffPct", "GuestNightsDiffPct"],
    )
    seasonality = load_csv(
        "seasonality_results.csv",
        {
            "AnalysisLevel", "Island", "RTO_or_Island", "MonthNumber",
            "MonthName", "AvgMonthlySpendMillion", "SeasonalityIndex",
        },
        ["MonthNumber", "AvgMonthlySpendMillion", "SeasonalityIndex"],
    )
except FileNotFoundError as error:
    st.error(f"Required file not found: `{error.args[0]}`")
    st.info("Place all three exported CSV files in the same folder as `app.py`.")
    st.stop()
except ValueError as error:
    st.error("A CSV does not match the expected SQL output.")
    st.code(str(error))
    st.stop()


# Sidebar: persistent global controls and help.
with st.sidebar:
    st.title("Explore the data")
    st.caption("These controls update every relevant view.")
    selected_island = st.selectbox(
        "Island",
        ["All", "North Island", "South Island"],
        help="Show all RTOs or focus on one island.",
    )
    label_outliers = st.toggle(
        "Label notable RTOs",
        value=True,
        help="Labels only unusually large domestic-spending changes.",
    )
    st.divider()
    st.markdown("**Analysis period**")
    st.caption("January 2024–December 2025")
    st.markdown("**Geographic level**")
    st.caption("Regional Tourism Organisation areas")
    with st.expander("How to read the dashboard"):
        st.markdown(
            """
            - Blue represents the North Island.
            - Orange represents the South Island.
            - A seasonality index of 100 is a Normalized Monthly Index.
            - Vulnerability is an exploratory project measure.
            """
        )


def by_island(frame: pd.DataFrame) -> pd.DataFrame:
    if selected_island == "All":
        return frame.copy()
    return frame.loc[frame["Island"] == selected_island].copy()


vulnerability_view = by_island(vulnerability).dropna(subset=["VulnerabilityScore"])
buffer_view = by_island(buffer)

st.title("New Zealand Regional Tourism Resilience")
st.markdown(
    "**How seasonal is regional tourism, can domestic demand cushion weak "
    "international months, and which destinations face the greatest exposure?**"
)
st.caption(
    "BUSINFO 702 · Interactive results from MBIE tourism data and the "
    "Stats NZ RTO classification · 2024–2025"
)

if vulnerability_view.empty:
    st.warning("No vulnerability records are available for this selection.")
    st.stop()

# Summary first: progressive disclosure from key result to supporting detail.
highest = vulnerability_view.loc[vulnerability_view["VulnerabilityScore"].idxmax()]
valid_buffers = buffer_view.dropna(subset=["SpendDiffPct"])
positive_buffers = int((valid_buffers["SpendDiffPct"] > 0).sum())

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(
    "RTOs analysed", f"{vulnerability_view['RTOName'].nunique():,}",
    help="RTOs with spending observations in the vulnerability analysis.",
)
kpi2.metric(
    "Highest-risk RTO", highest["RTOName"],
    help="Highest exploratory vulnerability score in the current view.",
)
kpi3.metric(
    "Highest vulnerability score", f"{highest['VulnerabilityScore']:.1f}",
    help="Equal-weight average of international dependence and peak concentration.",
)
kpi4.metric(
    "Positive spending buffers", f"{positive_buffers} of {len(valid_buffers)}",
    help="RTOs where domestic spending rises during weak international months.",
)

st.divider()
overview_tab,method_tab, season_tab, buffer_tab, risk_tab = st.tabs(
    ["Overview", "Methodology", "RQ1. Seasonality", "RQ2. Domestic buffer", "RQ3. Vulnerability"]
)


with overview_tab:
    st.subheader("Three insights from the warehouse")
    insight1, insight2, insight3 = st.columns(3)
    with insight1:
        st.markdown("#### 1 · Seasonality is uneven")
        st.write("South Island spending has a larger summer-to-winter swing.")
    with insight2:
        st.markdown("#### 2 · Value can buffer volume")
        st.write("Domestic spending rises in some RTOs even as visitor numbers fall.")
    with insight3:
        st.markdown("#### 3 · Exposure is concentrated")
        st.write("Several South Island destinations carry both forms of tourism risk.")

    st.info(
        "**Central insight:** resilience comes from domestic demand that occurs in "
        "a different season or generates greater value—not simply from more visitors."
    )

    top_ten = vulnerability_view.nlargest(10, "VulnerabilityScore").sort_values(
        "VulnerabilityScore"
    )
    overview_fig = px.bar(
        top_ten,
        x="VulnerabilityScore", y="RTOName", color="Island", orientation="h",
        color_discrete_map=ISLAND_COLOURS, template="plotly_white",
        title="Ten highest vulnerability scores in the current view",
        labels={"VulnerabilityScore": "Vulnerability score", "RTOName": "RTO"},
        hover_data={
            "InternationalSpendSharePct": ":.1f",
            "Peak3MonthSpendSharePct": ":.1f", "PeakMonths": True,
        },
    )
    overview_fig.update_layout(
        height=500, margin=dict(l=20, r=30, t=65, b=20), legend_title_text="Island"
    )
    overview_fig.update_xaxes(rangemode="tozero")
    st.plotly_chart(overview_fig, use_container_width=True)

with method_tab:
    st.subheader("Methodology and responsible interpretation")
    st.markdown(
        """
        **Warehouse grain**  
        One fact row represents one **month × RTO × visitor type** combination.

        **Seasonality index**  
        Monthly spending divided by the area's own average monthly spending, × 100.

        **Low international demand**  
        International visitor count below that RTO's own 2024–2025 monthly average.

        **Vulnerability score**  
        Equal-weight average of international spending share and top-three-month
        spending concentration.

        **Limitations**  
        Results show associations, not causation. Visitor counts are not additive
        across RTOs. Missing and suppressed observations remain null, not zero.
        """
    )
    st.markdown("#### Data sources")
    st.markdown(
        """
        - MBIE Monthly Regional Tourism Estimates (MRTE)
        - MBIE Accommodation Data Programme (ADP)
        - MBIE Tourism Volumes and Flows (TV&F)
        - Stats NZ Regional Tourism Organisation Areas 2025
        """
    )

with season_tab:
    st.subheader("RQ1 · How does tourism spending seasonality vary across RTOs and islands?")
    st.write(
        "Each month's spending is indexed against the area's average month (100), allowing "
        "regions of different sizes to be compared on the same scale."
    )
    st.info(
        "**Key take-away:** South Island spending shows stronger "
        "seasonality, with a sharper summer peak and deeper winter "
        "trough than the North Island."
    )
    level = st.radio("Analysis level", ["Island", "RTO"], horizontal=True)
    season_view = seasonality.loc[seasonality["AnalysisLevel"] == level].copy()
    if selected_island != "All":
        season_view = season_view.loc[season_view["Island"] == selected_island]

    areas = sorted(season_view["RTO_or_Island"].dropna().unique())
    chosen = st.multiselect(
        "Areas to compare", areas, default=areas[: (2 if level == "Island" else 3)],
        max_selections=6, help="A six-line limit keeps the chart readable.",
    )
    season_chart = season_view.loc[
        season_view["RTO_or_Island"].isin(chosen)
    ].sort_values(["RTO_or_Island", "MonthNumber"])

    if season_chart.empty:
        st.warning("Select at least one area to display the chart.")
    else:
        season_fig = px.line(
            season_chart,
            x="MonthName", y="SeasonalityIndex", color="RTO_or_Island", markers=True,
            category_orders={"MonthName": MONTHS}, template="plotly_white",
        labels={
            "MonthName": "Month",
            "SeasonalityIndex":
                "Spending index (average month = 100)",
            "RTO_or_Island": "Area",
            "AvgMonthlySpendMillion":
                "Average monthly spending (NZ$ million)"
        },
            hover_data={"AvgMonthlySpendMillion": ":.2f"},
        )
        season_fig.add_hline(
            y=100, line_dash="dash", line_color=NEUTRAL,
            annotation_text="Normalized Monthly Index (Index = 100)", annotation_position="top left",
        )
        season_fig.update_layout(
            height=560, margin=dict(l=20, r=20, t=30, b=20),
            legend_title_text="Area", hovermode="x unified",
        )
        st.plotly_chart(season_fig, use_container_width=True)
        st.caption(
            "An index of 126 is 26% above the area's average month; "
            "an index of 73 is 27% below average."
        )


with buffer_tab:
    st.subheader("RQ2 · Does domestic demand fill the international trough?")
    st.write(
        "Each point compares domestic activity in months when international visitor "
        "numbers were below that RTO's own average."
    )
    st.info(
        "**Key take-away:** Domestic tourism could not serve as a buffer because domestic visitor numbers and spending decline in almost every RTO when international demand weakens, except for Ruapehu, where domestic spending more than doubles even as domestic visitors decline."
    )
    buffer_chart = buffer_view.dropna(
        subset=["VisitorDiffPct", "SpendDiffPct"]
    ).copy()
    buffer_chart["PointLabel"] = ""
    if label_outliers:
        buffer_chart.loc[
            buffer_chart["SpendDiffPct"].abs() >= 40, "PointLabel"
        ] = buffer_chart["RTOName"]

    buffer_fig = px.scatter(
        buffer_chart,
        x="VisitorDiffPct", y="SpendDiffPct", color="Island", text="PointLabel",
        size="LowDemandMonths", size_max=18, color_discrete_map=ISLAND_COLOURS,
        template="plotly_white", hover_name="RTOName",
        labels={
            "VisitorDiffPct": "Change in domestic visitors volume (%)",
            "SpendDiffPct": "Change in domestic spending (%)",
            "LowDemandMonths": "Low-demand months",
        },
        hover_data={
            "Island": True, "GuestNightsDiffPct": ":.1f",
            "LowDemandMonths": True, "PointLabel": False,
        },
    )
    buffer_fig.add_vline(x=0, line_dash="dash", line_color=NEUTRAL)
    buffer_fig.add_hline(y=0, line_dash="dash", line_color=NEUTRAL)
    buffer_fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98,
        text="Value-based buffer", showarrow=False,
        font=dict(color="#166534", size=13),
        bgcolor="rgba(220,252,231,0.85)", borderpad=5,
    )
    buffer_fig.update_traces(textposition="top center")
    buffer_fig.update_layout(
        height=620, margin=dict(l=20, r=20, t=25, b=20),
        legend_title_text="Island",
    )
    st.plotly_chart(buffer_fig, use_container_width=True)
    st.success(
        "**Upper-left quadrant:** visitor numbers fell while spending increased—"
        "evidence of a value-based, rather than volume-based, domestic buffer."
    )


with risk_tab:
    st.subheader("RQ3 · Which RTOs are most exposed to demand shocks?")
    st.write(
        "The score equally weights international spending dependence and the share "
        "of spending concentrated in each RTO's top three months."
    )
    st.info(
        "**Key takeaway:** Exposure to shocks is concentrated in the South Island, which holds 8 of the 10 most vulnerable RTOs."
    )
    count = st.slider(
        "RTOs to display", 5, max(5, len(vulnerability_view)),
        min(15, len(vulnerability_view)),
    )
    risk_chart = vulnerability_view.nlargest(count, "VulnerabilityScore").sort_values(
        "VulnerabilityScore"
    )
    risk_fig = px.bar(
        risk_chart,
        x="VulnerabilityScore", y="RTOName", color="Island", orientation="h",
        color_discrete_map=ISLAND_COLOURS, template="plotly_white",
        text="VulnerabilityScore",
        labels={"VulnerabilityScore": "Vulnerability score", "RTOName": "RTO"},
        hover_data={
            "InternationalSpendSharePct": ":.1f",
            "Peak3MonthSpendSharePct": ":.1f", "PeakMonths": True,
        },
    )
    risk_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
    risk_fig.update_layout(
        height=max(500, count * 32), margin=dict(l=20, r=60, t=25, b=20),
        legend_title_text="Island",
    )
    risk_fig.update_xaxes(rangemode="tozero")
    st.plotly_chart(risk_fig, use_container_width=True)
    st.warning(
        "This score is a project-defined screening measure, not an official MBIE "
        "indicator. Its equal weighting should be tested through sensitivity analysis."
    )

    with st.expander("View and download the ranked data"):
        ranked = vulnerability_view.sort_values("VulnerabilityScore", ascending=False)
        columns = [
            "RTOName", "Island", "InternationalSpendSharePct",
            "Peak3MonthSpendSharePct", "VulnerabilityScore", "PeakMonths",
        ]
        st.dataframe(ranked[columns], use_container_width=True, hide_index=True)
        st.download_button(
            "Download filtered CSV", ranked.to_csv(index=False).encode("utf-8"),
            "filtered_vulnerability_results.csv", "text/csv",
        )




st.divider()
st.caption(
    "BUSINFO 702 · Group 20 · Dashboard values are derived from the project's "
    "SQLite analytical queries."
)
