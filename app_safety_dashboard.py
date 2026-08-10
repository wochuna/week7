"""
app_safety_dashboard.py
------------------------
Interactive HSE (Health, Safety & Environment) Safety Dashboard built with Streamlit.

Design choices (documented per requirement #8):
- @st.cache_data is used on the data-loading function so the (potentially expensive)
  read/generate step only runs once per session/input, not on every widget interaction.
- All filtering happens on a copy of the cached DataFrame, driven entirely by sidebar
  widgets, so every chart/metric below re-renders reactively whenever a filter changes
  (Streamlit reruns the whole script top-to-bottom on any widget change -- no manual
  callbacks are needed).
- KPIs use st.metric's built-in "delta" coloring (green/red arrows) to visually flag
  bad trends (e.g. rising incident counts, rising severity) at a glance.
- A synthetic HSE dataset is generated as a fallback so the dashboard is runnable and
  demoable even without a real capstone file. Swap in your real CSV via the uploader
  or by setting DEFAULT_DATA_PATH below.
"""

import io
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Page configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="HSE Safety Dashboard",
    page_icon="🦺",
    layout="wide",
)

# Point this at your real Capstone dataset if you have one checked into the repo.
# Leave as None to use the file-uploader / synthetic-data fallback below.
DEFAULT_DATA_PATH = None  # e.g. "data/hse_incidents.csv"

SITES = ["Plant A", "Plant B", "Warehouse C", "Refinery D", "Site E"]
INCIDENT_TYPES = ["Near Miss", "First Aid", "Lost Time Injury", "Property Damage", "Environmental"]
SHIFTS = ["Day", "Evening", "Night"]


# ----------------------------------------------------------------------------
# 1. DATA LOADING
# ----------------------------------------------------------------------------
@st.cache_data
def generate_synthetic_data(n_rows: int = 1200, seed: int = 42) -> pd.DataFrame:
    """
    Creates a synthetic-but-realistic HSE incident log so the dashboard works
    out of the box. Cached with @st.cache_data so this (relatively cheap, but
    still non-trivial) random generation only runs once, not on every rerun.
    """
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp.today().normalize() - timedelta(days=365)
    dates = start_date + pd.to_timedelta(rng.integers(0, 365, n_rows), unit="D")

    df = pd.DataFrame(
        {
            "Date": dates,
            "Site": rng.choice(SITES, n_rows, p=[0.28, 0.22, 0.2, 0.15, 0.15]),
            "Incident_Type": rng.choice(
                INCIDENT_TYPES, n_rows, p=[0.4, 0.28, 0.12, 0.15, 0.05]
            ),
            "Shift": rng.choice(SHIFTS, n_rows, p=[0.5, 0.3, 0.2]),
            # Severity 1 (minor) - 5 (critical)
            "Severity": rng.choice([1, 2, 3, 4, 5], n_rows, p=[0.35, 0.3, 0.18, 0.12, 0.05]),
        }
    )
    df = df.sort_values("Date").reset_index(drop=True)

    # Approximate lat/lon per site so we can show a map (requirement #4, map option).
    site_coords = {
        "Plant A": (29.7604, -95.3698),      # Houston
        "Plant B": (41.8781, -87.6298),      # Chicago
        "Warehouse C": (33.4484, -112.0740), # Phoenix
        "Refinery D": (29.9511, -90.0715),   # New Orleans
        "Site E": (39.9526, -75.1652),       # Philadelphia
    }
    jitter = rng.normal(0, 0.05, (n_rows, 2))  # spread points slightly so they don't fully overlap
    df["lat"] = [site_coords[s][0] for s in df["Site"]] + jitter[:, 0]
    df["lon"] = [site_coords[s][1] for s in df["Site"]] + jitter[:, 1]

    return df


@st.cache_data
def load_csv_data(file_bytes: bytes) -> pd.DataFrame:
    """
    Loads a user-uploaded HSE CSV. Cached on the raw bytes so re-running the
    script (e.g. from a filter change) doesn't re-parse the file every time.
    Expected columns: Date, Site, Incident_Type, Shift, Severity, [lat, lon].
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_data(uploaded_file) -> pd.DataFrame:
    """Routing helper: prefer an uploaded file, then a default path, then synthetic data."""
    if uploaded_file is not None:
        return load_csv_data(uploaded_file.getvalue())
    if DEFAULT_DATA_PATH:
        try:
            df = pd.read_csv(DEFAULT_DATA_PATH)
            df["Date"] = pd.to_datetime(df["Date"])
            return df
        except FileNotFoundError:
            st.sidebar.warning(f"Couldn't find {DEFAULT_DATA_PATH}, using sample data instead.")
    return generate_synthetic_data()


# ----------------------------------------------------------------------------
# Sidebar: data source + filters
# ----------------------------------------------------------------------------
st.sidebar.title("🦺 HSE Dashboard Controls")

st.sidebar.subheader("Data Source")
uploaded_file = st.sidebar.file_uploader(
    "Upload HSE/Capstone incident CSV", type=["csv"],
    help="Columns expected: Date, Site, Incident_Type, Shift, Severity (lat/lon optional).",
)

raw_df = load_data(uploaded_file)

st.sidebar.divider()
st.sidebar.subheader("Filters")

# --- Site / Location filter ---
site_options = sorted(raw_df["Site"].unique())
selected_sites = st.sidebar.multiselect(
    "Site / Location", options=site_options, default=site_options
)

# --- Date range filter ---
min_date, max_date = raw_df["Date"].min().date(), raw_df["Date"].max().date()
date_range = st.sidebar.date_input(
    "Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
# date_input can return a single date while the user is mid-selection; guard for that.
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# --- Incident type filter ---
type_options = sorted(raw_df["Incident_Type"].unique())
selected_types = st.sidebar.multiselect(
    "Incident Type", options=type_options, default=type_options
)

st.sidebar.divider()
st.sidebar.subheader("Alerting")
critical_threshold = st.sidebar.slider(
    "Critical incident alert threshold", min_value=1, max_value=50, value=10,
    help="Trigger a warning banner if the number of Severity-5 incidents in the "
         "filtered view exceeds this value.",
)

# ----------------------------------------------------------------------------
# Apply filters -- everything downstream reads from `df`, so all charts/metrics
# automatically stay in sync with the sidebar (requirement #5: interactivity).
# ----------------------------------------------------------------------------
df = raw_df[
    raw_df["Site"].isin(selected_sites)
    & raw_df["Incident_Type"].isin(selected_types)
    & (raw_df["Date"].dt.date >= start_date)
    & (raw_df["Date"].dt.date <= end_date)
].copy()

st.title("🦺 HSE Safety Dashboard")
st.caption(
    f"Showing {len(df):,} incidents across {df['Site'].nunique()} site(s), "
    f"{start_date} to {end_date}."
)

if df.empty:
    st.info("No incidents match the current filters. Try widening your selection.")
    st.stop()


# ----------------------------------------------------------------------------
# 3. KPI METRICS  (with conditional coloring via st.metric's delta arrows)
# ----------------------------------------------------------------------------
# To show a "trend", compare the most recent half of the filtered date range
# against the prior half -- a simple, transparent way to flag worsening safety
# performance without needing a full time-series model.
midpoint = start_date + (end_date - start_date) / 2
recent = df[df["Date"].dt.date > midpoint]
prior = df[df["Date"].dt.date <= midpoint]

total_incidents = len(df)
avg_severity = df["Severity"].mean()
critical_count = int((df["Severity"] == 5).sum())

recent_total, prior_total = len(recent), len(prior)
recent_avg_sev = recent["Severity"].mean() if not recent.empty else 0
prior_avg_sev = prior["Severity"].mean() if not prior.empty else 0
recent_critical = int((recent["Severity"] == 5).sum())
prior_critical = int((prior["Severity"] == 5).sum())

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "Total Incidents",
        f"{total_incidents:,}",
        delta=f"{recent_total - prior_total:+d} vs prior period",
        delta_color="inverse",  # inverse => an increase in incidents is shown in red ("bad")
    )
with col2:
    st.metric(
        "Avg. Severity (1-5)",
        f"{avg_severity:.2f}",
        delta=f"{recent_avg_sev - prior_avg_sev:+.2f} vs prior period",
        delta_color="inverse",  # rising severity is bad -> red
    )
with col3:
    st.metric(
        "Critical Incidents (Sev. 5)",
        f"{critical_count}",
        delta=f"{recent_critical - prior_critical:+d} vs prior period",
        delta_color="inverse",
    )

# ----------------------------------------------------------------------------
# 6. ALERTING LOGIC
# ----------------------------------------------------------------------------
if critical_count > critical_threshold:
    st.warning(
        f"⚠️ **{critical_count} critical incidents** in the current selection "
        f"exceed the alert threshold of {critical_threshold}. Immediate review recommended.",
        icon="🚨",
    )

st.divider()

# ----------------------------------------------------------------------------
# 4. VISUALIZATIONS
# ----------------------------------------------------------------------------
viz_col1, viz_col2 = st.columns(2)

# --- Time-series chart: incident trend over time ---
with viz_col1:
    st.subheader("Incident Trend Over Time")
    # Daily counts, plus a 7-day rolling average to smooth noise and make the
    # underlying trend easier to read than raw daily bars.
    daily = df.groupby(df["Date"].dt.date).size().reset_index(name="Incidents")
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily = daily.sort_values("Date")
    daily["7-day Avg"] = daily["Incidents"].rolling(7, min_periods=1).mean()

    fig_trend = px.line(
        daily, x="Date", y=["Incidents", "7-day Avg"],
        labels={"value": "Incidents", "variable": ""},
        title=None,
    )
    fig_trend.update_layout(legend=dict(orientation="h", y=1.1), margin=dict(t=10))
    st.plotly_chart(fig_trend, use_container_width=True)

# --- Categorical chart: breakdown by incident type ---
with viz_col2:
    st.subheader("Breakdown by Incident Type")
    type_counts = df["Incident_Type"].value_counts().reset_index()
    type_counts.columns = ["Incident_Type", "Count"]
    fig_bar = px.bar(
        type_counts, x="Incident_Type", y="Count", color="Incident_Type",
        text="Count",
    )
    fig_bar.update_layout(showlegend=False, margin=dict(t=10))
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

viz_col3, viz_col4 = st.columns(2)

# --- Map OR heatmap (requirement #4, option 3) ---
with viz_col3:
    if {"lat", "lon"}.issubset(df.columns):
        st.subheader("Incident Locations")
        # A map is more intuitive than a table for spatial data when lat/lon exists.
        site_summary = (
            df.groupby("Site")
            .agg(lat=("lat", "mean"), lon=("lon", "mean"), Incidents=("Site", "count"))
            .reset_index()
        )
        fig_map = px.scatter_mapbox(
            site_summary, lat="lat", lon="lon", size="Incidents", color="Incidents",
            hover_name="Site", zoom=2.5, mapbox_style="carto-positron",
            color_continuous_scale="Reds",
        )
        fig_map.update_layout(margin=dict(t=10, l=0, r=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.subheader("Incidents by Shift & Day of Week")
        st.caption("No location data found -- showing a shift/day heatmap instead.")
        heat_df = df.copy()
        heat_df["Day_of_Week"] = heat_df["Date"].dt.day_name()
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot = (
            heat_df.groupby(["Shift", "Day_of_Week"]).size()
            .reset_index(name="Incidents")
            .pivot(index="Shift", columns="Day_of_Week", values="Incidents")
            .reindex(columns=day_order)
            .fillna(0)
        )
        fig_heat = px.imshow(
            pivot, text_auto=True, aspect="auto", color_continuous_scale="Reds",
            labels=dict(color="Incidents"),
        )
        fig_heat.update_layout(margin=dict(t=10))
        st.plotly_chart(fig_heat, use_container_width=True)

# --- Bonus: shift/day heatmap always shown alongside the map for extra context ---
with viz_col4:
    st.subheader("Incidents by Site")
    site_counts = df["Site"].value_counts().reset_index()
    site_counts.columns = ["Site", "Count"]
    fig_pie = px.pie(site_counts, names="Site", values="Count", hole=0.45)
    fig_pie.update_layout(margin=dict(t=10))
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# 7. EXPORT
# ----------------------------------------------------------------------------
st.subheader("Export Filtered Data")
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download filtered data as CSV",
    data=csv_bytes,
    file_name="filtered_hse_incidents.csv",
    mime="text/csv",
)

with st.expander("View filtered data table"):
    st.dataframe(df, use_container_width=True)
