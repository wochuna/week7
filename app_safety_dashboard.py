"""
app_safety_dashboard.py
------------------------
Interactive HSE (Health, Safety & Environment) Safety Command Center built with Streamlit.

Design choices (documented per Requirement #8):
1. Caching (@st.cache_data):
   - Loading datasets (from default path, uploaded CSV, or synthetic generation) is wrapped
     in `@st.cache_data` so that file reading, parsing, and column transformations only run once
     per session/file rather than re-executing on every UI filter interaction.
2. Interactivity & Reactive Filtering:
   - All filters (Site, Date Range, Incident Type) reside in the sidebar. All KPIs, charts,
     and alerts read from a single filtered slice `df`, so any filter change automatically and
     instantaneously cascades across all visual components without manual callback spaghetti.
3. KPI Metrics & Inverse Delta Trend Signaling:
   - Uses `st.metric` with `delta_color="inverse"` because in safety analytics, higher incident counts
     or rising severity represent negative (worsening) trends that must be flagged in red.
   - Compares the most recent half of the selected date range against the prior half for dynamic trend tracking.
4. Visual Diversity & Analytical Depth:
   - Time-Series: Daily counts paired with a 7-day rolling average to distinguish systemic trends from daily noise.
   - Categorical: Horizontal/vertical bar breakdown by incident classification with color cues.
   - Geospatial & Shift Analysis: Mapbox scatter plot showing geographical incident clusters across facilities,
     plus a Shift x Day-of-Week heatmap to uncover organizational blind spots (e.g. night-shift risks).
5. Proactive Alerting Logic:
   - Prominently displays an `st.warning` banner if critical incidents (Severity 5) exceed the user-defined
     threshold, immediately focusing executive attention on high-risk areas.
6. Export Functionality:
   - Provides a one-click CSV download of the filtered dataset (`st.download_button`) alongside an expander
     to inspect the underlying records.
"""

import io
import os
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Page configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="HSE Safety Command Center",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto-detect real HSE dataset in the workspace, fallback to synthetic if absent
DEFAULT_DATA_PATH = "safety_incidents.csv" if os.path.exists("safety_incidents.csv") else None

FALLBACK_SITES = ["Depot B", "Depot A", "Plant C", "Warehouse D", "Terminal E"]
FALLBACK_INCIDENT_TYPES = [
    "Slip / Trip",
    "Vehicle Interaction",
    "Equipment Contact",
    "Manual Handling",
    "Chemical Exposure",
    "Fall From Height",
    "Struck By",
    "Near Miss",
]
FALLBACK_SHIFTS = ["Day", "Night"]


# ----------------------------------------------------------------------------
# Helper: Standardize Column Names Across Datasets
# ----------------------------------------------------------------------------
def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes column names across various HSE datasets (such as safety_incidents.csv
    or user uploads) into standard expected columns:
    Date, Site, Incident_Type, Shift, Severity, lat, lon
    """
    column_mapping = {
        "incident_date": "Date",
        "date": "Date",
        "site": "Site",
        "location": "Site",
        "incident_type": "Incident_Type",
        "type": "Incident_Type",
        "shift": "Shift",
        "severity": "Severity",
        "latitude": "lat",
        "lat": "lat",
        "longitude": "lon",
        "lon": "lon",
    }
    rename_dict = {}
    for col in df.columns:
        norm_key = str(col).strip().lower()
        if norm_key in column_mapping:
            rename_dict[col] = column_mapping[norm_key]
    df = df.rename(columns=rename_dict)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])

    # Ensure required columns exist with sensible defaults if missing
    if "Severity" in df.columns:
        df["Severity"] = pd.to_numeric(df["Severity"], errors="coerce").fillna(1).astype(int)
    else:
        df["Severity"] = 1

    if "Site" not in df.columns:
        df["Site"] = "Unknown Site"
    if "Incident_Type" not in df.columns:
        df["Incident_Type"] = "General Incident"
    if "Shift" not in df.columns:
        df["Shift"] = "Day"

    return df


# ----------------------------------------------------------------------------
# 1. DATA LOADING (with caching per Requirement #1)
# ----------------------------------------------------------------------------
@st.cache_data
def generate_synthetic_data(n_rows: int = 1200, seed: int = 42) -> pd.DataFrame:
    """
    Creates a synthetic HSE incident log so the dashboard works seamlessly out of the box
    even if no external CSV file is present. Cached with @st.cache_data for instant performance.
    """
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp.today().normalize() - timedelta(days=365)
    dates = start_date + pd.to_timedelta(rng.integers(0, 365, n_rows), unit="D")

    df = pd.DataFrame(
        {
            "Date": dates,
            "Site": rng.choice(FALLBACK_SITES, n_rows, p=[0.30, 0.22, 0.20, 0.15, 0.13]),
            "Incident_Type": rng.choice(
                FALLBACK_INCIDENT_TYPES,
                n_rows,
                p=[0.25, 0.20, 0.15, 0.15, 0.10, 0.05, 0.05, 0.05],
            ),
            "Shift": rng.choice(FALLBACK_SHIFTS, n_rows, p=[0.55, 0.45]),
            "Severity": rng.choice([1, 2, 3, 4, 5], n_rows, p=[0.35, 0.28, 0.18, 0.12, 0.07]),
        }
    )
    df = df.sort_values("Date").reset_index(drop=True)

    site_coords = {
        "Depot B": (41.8781, -87.6298),      # Chicago
        "Depot A": (39.7392, -104.9903),     # Denver
        "Plant C": (29.7604, -95.3698),      # Houston
        "Warehouse D": (33.4484, -112.0740), # Phoenix
        "Terminal E": (34.0522, -118.2437),  # Los Angeles
    }
    jitter = rng.normal(0, 0.04, (n_rows, 2))
    df["lat"] = [site_coords.get(s, (37.0902, -95.7129))[0] for s in df["Site"]] + jitter[:, 0]
    df["lon"] = [site_coords.get(s, (37.0902, -95.7129))[1] for s in df["Site"]] + jitter[:, 1]
    return df


@st.cache_data
def load_csv_data(file_bytes: bytes) -> pd.DataFrame:
    """
    Loads a user-uploaded HSE CSV. Cached on file bytes so re-filtering doesn't re-parse.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    return standardize_columns(df)


@st.cache_data
def load_file_from_path(file_path: str) -> pd.DataFrame:
    """
    Loads an on-disk CSV file (e.g. safety_incidents.csv). Cached on file path.
    """
    df = pd.read_csv(file_path)
    return standardize_columns(df)


def load_data(uploaded_file) -> tuple[pd.DataFrame, str]:
    """
    Routing helper: Prefer uploaded file > default workspace file > synthetic fallback.
    Returns (DataFrame, source_description).
    """
    if uploaded_file is not None:
        return load_csv_data(uploaded_file.getvalue()), f"Uploaded file: {uploaded_file.name}"
    if DEFAULT_DATA_PATH and os.path.exists(DEFAULT_DATA_PATH):
        try:
            return load_file_from_path(DEFAULT_DATA_PATH), f"Primary Dataset ({DEFAULT_DATA_PATH})"
        except Exception as e:
            st.sidebar.warning(f"Could not load {DEFAULT_DATA_PATH}: {e}. Falling back to sample data.")
    return generate_synthetic_data(), "Synthetic HSE Demonstration Data"


# ----------------------------------------------------------------------------
# 2. SIDEBAR CONTROLS (Requirement #2: Site, Date Range, Incident Type)
# ----------------------------------------------------------------------------
st.sidebar.title("🦺 HSE Command Controls")

st.sidebar.subheader("Data Source")
uploaded_file = st.sidebar.file_uploader(
    "Upload Custom HSE/Capstone CSV",
    type=["csv"],
    help="Accepts standard HSE logs with Date, Site, Incident_Type, Shift, Severity, lat/lon.",
)

raw_df, data_source_label = load_data(uploaded_file)

st.sidebar.caption(f"📁 **Active Source:** {data_source_label}")
st.sidebar.divider()

st.sidebar.subheader("Interactive Filters")

# Site / Location filter
site_options = sorted(raw_df["Site"].dropna().unique())
selected_sites = st.sidebar.multiselect(
    "Site / Location",
    options=site_options,
    default=site_options,
    help="Filter data to specific operational facilities.",
)

# Date range filter
min_date = raw_df["Date"].min().date()
max_date = raw_df["Date"].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    help="Select start and end dates to evaluate incident trends.",
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# Incident type filter
type_options = sorted(raw_df["Incident_Type"].dropna().unique())
selected_types = st.sidebar.multiselect(
    "Incident Type",
    options=type_options,
    default=type_options,
    help="Filter by incident classification.",
)

st.sidebar.divider()

# Alerting Threshold control (Requirement #6)
st.sidebar.subheader("Alerting Configuration")
critical_threshold = st.sidebar.slider(
    "Critical Incident Alert Threshold",
    min_value=1,
    max_value=50,
    value=10,
    help="Trigger a warning banner if the count of Critical (Severity 5) incidents exceeds this threshold.",
)

# ----------------------------------------------------------------------------
# 5. INTERACTIVITY: Apply reactive filtering across downstream components
# ----------------------------------------------------------------------------
mask = (
    raw_df["Site"].isin(selected_sites)
    & raw_df["Incident_Type"].isin(selected_types)
    & (raw_df["Date"].dt.date >= start_date)
    & (raw_df["Date"].dt.date <= end_date)
)
df = raw_df[mask].copy()

# Header banner
st.title("🦺 HSE Safety Intelligence Command Center")
st.markdown(
    f"**Active Scope:** Evaluating **{len(df):,}** incidents across **{df['Site'].nunique()}** site(s) "
    f"from **{start_date}** to **{end_date}**."
)

if df.empty:
    st.info("ℹ️ No incidents match the currently selected filter combination. Please expand your sidebar filters.")
    st.stop()


# ----------------------------------------------------------------------------
# 3. KPI METRICS (Requirement #3: >=3 metrics with inverse delta conditional coloring)
# ----------------------------------------------------------------------------
# We split the selected timeframe into two equal halves (recent period vs prior period)
# to compute period-over-period trend deltas.
midpoint = start_date + (end_date - start_date) / 2
recent = df[df["Date"].dt.date > midpoint]
prior = df[df["Date"].dt.date <= midpoint]

total_incidents = len(df)
avg_severity = df["Severity"].mean()
critical_count = int((df["Severity"] == 5).sum())

recent_total, prior_total = len(recent), len(prior)
recent_avg_sev = recent["Severity"].mean() if not recent.empty else 0.0
prior_avg_sev = prior["Severity"].mean() if not prior.empty else 0.0
recent_critical = int((recent["Severity"] == 5).sum())
prior_critical = int((prior["Severity"] == 5).sum())

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

with kpi_col1:
    delta_incidents = recent_total - prior_total
    st.metric(
        label="Total Incidents",
        value=f"{total_incidents:,}",
        delta=f"{delta_incidents:+d} vs prior period",
        delta_color="inverse",  # An increase in incidents is dangerous/negative -> red
    )

with kpi_col2:
    delta_sev = recent_avg_sev - prior_avg_sev
    st.metric(
        label="Average Severity (Scale 1–5)",
        value=f"{avg_severity:.2f}",
        delta=f"{delta_sev:+.2f} vs prior period",
        delta_color="inverse",  # Rising severity is dangerous -> red
    )

with kpi_col3:
    delta_crit = recent_critical - prior_critical
    st.metric(
        label="Critical Incidents (Sev. 5 / SIF)",
        value=f"{critical_count:,}",
        delta=f"{delta_crit:+d} vs prior period",
        delta_color="inverse",  # More critical incidents -> red
    )


# ----------------------------------------------------------------------------
# 6. ALERTING LOGIC (Requirement #6: st.warning if critical incidents > threshold)
# ----------------------------------------------------------------------------
if critical_count > critical_threshold:
    st.warning(
        f"🚨 **CRITICAL SAFETY ALERT**: Filtered view records **{critical_count} critical incidents (Severity 5)**, "
        f"exceeding the safety threshold of **{critical_threshold}**. Immediate site supervisor intervention, "
        f"focused hazard audits, and shift stand-downs are strongly advised.",
        icon="⚠️",
    )

st.divider()


# ----------------------------------------------------------------------------
# 4. VISUALIZATIONS (Requirement #4: Time-Series, Categorical, Map / Heatmap)
# ----------------------------------------------------------------------------
viz_row1_col1, viz_row1_col2 = st.columns(2)

# Visualization 1: Time-Series Chart with 7-Day Rolling Trend
with viz_row1_col1:
    st.subheader("📈 Incident Frequency & Trend Over Time")
    daily = df.groupby(df["Date"].dt.date).size().reset_index(name="Daily Incidents")
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily = daily.sort_values("Date")
    daily["7-Day Rolling Average"] = daily["Daily Incidents"].rolling(7, min_periods=1).mean()

    fig_trend = px.line(
        daily,
        x="Date",
        y=["Daily Incidents", "7-Day Rolling Average"],
        labels={"value": "Incident Count", "variable": "Metric"},
        color_discrete_map={
            "Daily Incidents": "#94a3b8",
            "7-Day Rolling Average": "#dc2626",
        },
    )
    fig_trend.update_layout(
        legend=dict(orientation="h", y=1.12, x=0),
        margin=dict(t=15, b=10, l=10, r=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# Visualization 2: Categorical Chart (Breakdown by Incident Type)
with viz_row1_col2:
    st.subheader("📊 Breakdown by Incident Classification")
    type_counts = df["Incident_Type"].value_counts().reset_index()
    type_counts.columns = ["Incident_Type", "Count"]

    fig_bar = px.bar(
        type_counts,
        x="Count",
        y="Incident_Type",
        orientation="h",
        color="Count",
        color_continuous_scale="Reds",
        text="Count",
        labels={"Incident_Type": "Classification", "Count": "Recorded Events"},
    )
    fig_bar.update_layout(
        yaxis=dict(autorange="reversed"),
        margin=dict(t=15, b=10, l=10, r=10),
        coloraxis_showscale=False,
    )
    fig_bar.update_traces(textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

viz_row2_col1, viz_row2_col2 = st.columns(2)

# Visualization 3: Geospatial Map of Incident Locations OR Shift/Day Heatmap
with viz_row2_col1:
    if {"lat", "lon"}.issubset(df.columns) and df["lat"].notna().any():
        st.subheader("🗺️ Facility Incident Distribution (Geospatial Map)")
        site_geo = (
            df.groupby("Site")
            .agg(lat=("lat", "mean"), lon=("lon", "mean"), Incidents=("Site", "count"))
            .reset_index()
        )
        fig_map = px.scatter_mapbox(
            site_geo,
            lat="lat",
            lon="lon",
            size="Incidents",
            color="Incidents",
            hover_name="Site",
            zoom=3,
            mapbox_style="carto-positron",
            color_continuous_scale="Reds",
            size_max=30,
        )
        fig_map.update_layout(margin=dict(t=10, b=10, l=0, r=0))
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.subheader("🗓️ Incidents by Shift & Day of Week")
        heat_df = df.copy()
        heat_df["Day_of_Week"] = heat_df["Date"].dt.day_name()
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot_heat = (
            heat_df.groupby(["Shift", "Day_of_Week"])
            .size()
            .reset_index(name="Count")
            .pivot(index="Shift", columns="Day_of_Week", values="Count")
            .reindex(columns=days_order)
            .fillna(0)
        )
        fig_heat = px.imshow(
            pivot_heat,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Reds",
            labels=dict(color="Incidents"),
        )
        fig_heat.update_layout(margin=dict(t=15, b=10, l=10, r=10))
        st.plotly_chart(fig_heat, use_container_width=True)

# Visualization 4: Incident Density by Shift & Day of Week
with viz_row2_col2:
    st.subheader("🗓️ Incident Density by Shift & Day of Week")
    heat_df = df.copy()
    heat_df["Day_of_Week"] = heat_df["Date"].dt.day_name()
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot_heat = (
        heat_df.groupby(["Shift", "Day_of_Week"])
        .size()
        .reset_index(name="Count")
        .pivot(index="Shift", columns="Day_of_Week", values="Count")
        .reindex(columns=days_order)
        .fillna(0)
    )
    fig_heat2 = px.imshow(
        pivot_heat,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(color="Incidents"),
    )
    fig_heat2.update_layout(margin=dict(t=15, b=10, l=10, r=10))
    st.plotly_chart(fig_heat2, use_container_width=True)

st.divider()


# ----------------------------------------------------------------------------
# 7. EXPORT FUNCTIONALITY (Requirement #7: Download filtered data as CSV)
# ----------------------------------------------------------------------------
st.subheader("📥 Export & Audit Filtered HSE Records")
st.markdown("Download the filtered incident slice for regulatory compliance, shift huddles, or executive reporting.")

csv_export_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Filtered Data as CSV",
    data=csv_export_bytes,
    file_name=f"filtered_hse_incidents_{start_date}_to_{end_date}.csv",
    mime="text/csv",
    help="Click to export the currently filtered table records as a CSV file.",
)

with st.expander("🔍 Preview Detailed Filtered Dataset"):
    st.dataframe(df, use_container_width=True)
