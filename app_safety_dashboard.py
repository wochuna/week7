"""
app_safety_dashboard.py
------------------------
HSE Safety Command Center - Interactive Streamlit Dashboard

Design Choices & Rubric Compliance (Requirement #8):
1. Data Loading & Caching (@st.cache_data):
   - Loading from safety_incidents.csv, file upload, or synthetic generator is cached using
     @st.cache_data so file parsing only runs once, maintaining sub-second responsiveness.
2. Sidebar Controls:
   - Interactive filters for Site/Location, Date Range, Incident Type, and Alert Threshold.
3. KPI Metrics with Inverse Delta Coloring:
   - Evaluates recent vs. prior period trends. Uses delta_color="inverse" because higher
     incident counts or rising severity represent worsening safety performance (red flag).
4. Visualizations:
   - Time-series trend line with 7-day rolling average.
   - Categorical bar chart showing breakdown by incident type.
   - Geospatial facility map (or Shift x Day-of-Week heatmap fallback).
   - Bonus Shift x Day density heatmap.
5. Interactivity:
   - All charts, metrics, and alert banners update reactively when sidebar filters change.
6. Alerting Logic:
   - Triggers st.warning when Critical (Severity 5) incidents exceed the alert threshold.
7. Data Export:
   - Download filtered records as CSV via st.download_button, plus expandable data table.
"""

import io
import os
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Page Configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="HSE Safety Command Center",
    page_icon="[HSE]",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# 1. DATA LOADING & CACHING (Requirement #1)
# ----------------------------------------------------------------------------
DEFAULT_DATA_PATH = "safety_incidents.csv" if os.path.exists("safety_incidents.csv") else None

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonizes various HSE column conventions into a standard schema."""
    mapping = {
        "incident_date": "Date", "date": "Date",
        "site": "Site", "location": "Site",
        "incident_type": "Incident_Type", "type": "Incident_Type",
        "shift": "Shift",
        "severity": "Severity",
        "latitude": "lat", "lat": "lat",
        "longitude": "lon", "lon": "lon",
    }
    renames = {}
    for c in df.columns:
        clean_key = str(c).strip().lower()
        if clean_key in mapping:
            renames[c] = mapping[clean_key]
    df = df.rename(columns=renames)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    if "Severity" in df.columns:
        df["Severity"] = pd.to_numeric(df["Severity"], errors="coerce").fillna(1).astype(int)
    else:
        df["Severity"] = 1
    if "Site" not in df.columns:
        df["Site"] = "Site A"
    if "Incident_Type" not in df.columns:
        df["Incident_Type"] = "General"
    if "Shift" not in df.columns:
        df["Shift"] = "Day"
    return df

@st.cache_data
def generate_synthetic_data(n_rows: int = 600, seed: int = 42) -> pd.DataFrame:
    """Generates realistic synthetic HSE data as fallback if no CSV is available."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp.today().normalize() - timedelta(days=180)
    dates = start + pd.to_timedelta(rng.integers(0, 180, n_rows), unit="D")
    sites = ["Depot B", "Depot A", "Plant C", "Warehouse D", "Terminal E"]
    types = ["Slip / Trip", "Vehicle Interaction", "Equipment Contact", "Manual Handling", "Chemical Exposure", "Fall From Height", "Near Miss"]
    shifts = ["Day", "Night"]
    df = pd.DataFrame({
        "Date": dates,
        "Site": rng.choice(sites, n_rows, p=[0.30, 0.22, 0.20, 0.15, 0.13]),
        "Incident_Type": rng.choice(types, n_rows, p=[0.25, 0.20, 0.15, 0.15, 0.10, 0.08, 0.07]),
        "Shift": rng.choice(shifts, n_rows, p=[0.55, 0.45]),
        "Severity": rng.choice([1, 2, 3, 4, 5], n_rows, p=[0.35, 0.28, 0.18, 0.12, 0.07]),
    }).sort_values("Date").reset_index(drop=True)
    coords = {
        "Depot B": (41.8781, -87.6298), "Depot A": (39.7392, -104.9903),
        "Plant C": (29.7604, -95.3698), "Warehouse D": (33.4484, -112.0740),
        "Terminal E": (34.0522, -118.2437),
    }
    jitter = rng.normal(0, 0.03, (n_rows, 2))
    df["lat"] = [coords[s][0] for s in df["Site"]] + jitter[:, 0]
    df["lon"] = [coords[s][1] for s in df["Site"]] + jitter[:, 1]
    return df

@st.cache_data
def load_csv_data(file_bytes: bytes) -> pd.DataFrame:
    """Loads and standardizes an uploaded CSV file."""
    return standardize_columns(pd.read_csv(io.BytesIO(file_bytes)))

@st.cache_data
def load_file_from_path(file_path: str) -> pd.DataFrame:
    """Loads and standardizes an on-disk CSV file."""
    return standardize_columns(pd.read_csv(file_path))

def load_data(uploaded_file) -> tuple[pd.DataFrame, str]:
    """Loads dataset: uploaded file > workspace CSV > synthetic fallback."""
    if uploaded_file is not None:
        return load_csv_data(uploaded_file.getvalue()), f"Uploaded: {uploaded_file.name}"
    if DEFAULT_DATA_PATH and os.path.exists(DEFAULT_DATA_PATH):
        try:
            return load_file_from_path(DEFAULT_DATA_PATH), f"Primary: {DEFAULT_DATA_PATH}"
        except Exception:
            pass
    return generate_synthetic_data(), "Synthetic Demo Data"

# ----------------------------------------------------------------------------
# 2. SIDEBAR CONTROLS (Requirement #2: Site, Date Range, Incident Type)
# ----------------------------------------------------------------------------
st.sidebar.title("HSE Command Controls")
st.sidebar.subheader("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Incident CSV", type=["csv"])
raw_df, source_name = load_data(uploaded_file)
st.sidebar.caption(f"Active Source: {source_name}")
st.sidebar.divider()

st.sidebar.subheader("Filters")
all_sites = sorted(raw_df["Site"].dropna().unique())
selected_sites = st.sidebar.multiselect("Site / Location", options=all_sites, default=all_sites)

min_date, max_date = raw_df["Date"].min().date(), raw_df["Date"].max().date()
date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

all_types = sorted(raw_df["Incident_Type"].dropna().unique())
selected_types = st.sidebar.multiselect("Incident Type", options=all_types, default=all_types)

st.sidebar.divider()
st.sidebar.subheader("Alert Settings")
critical_threshold = st.sidebar.slider("Critical Incident Alert Threshold", min_value=1, max_value=50, value=10)

# ----------------------------------------------------------------------------
# 5. INTERACTIVITY: Apply reactive filtering across dashboard (Requirement #5)
# ----------------------------------------------------------------------------
mask = (
    raw_df["Site"].isin(selected_sites)
    & raw_df["Incident_Type"].isin(selected_types)
    & (raw_df["Date"].dt.date >= start_date)
    & (raw_df["Date"].dt.date <= end_date)
)
df = raw_df[mask].copy()

# Header title
st.title("HSE Safety Intelligence Command Center")
st.markdown(f"**Scope:** Analyzing **{len(df):,}** incidents across **{df['Site'].nunique()}** site(s) from **{start_date}** to **{end_date}**.")

if df.empty:
    st.info("No records match the current filter selection. Please broaden your filters.")
    st.stop()

# ----------------------------------------------------------------------------
# 3. KPI METRICS (Requirement #3: >=3 metrics with inverse delta coloring)
# ----------------------------------------------------------------------------
midpoint = start_date + (end_date - start_date) / 2
recent = df[df["Date"].dt.date > midpoint]
prior = df[df["Date"].dt.date <= midpoint]

total_incidents = len(df)
avg_severity = df["Severity"].mean()
critical_count = int((df["Severity"] == 5).sum())

recent_total, prior_total = len(recent), len(prior)
recent_avg_sev = recent["Severity"].mean() if not recent.empty else 0.0
prior_avg_sev = prior["Severity"].mean() if not prior.empty else 0.0
recent_crit = int((recent["Severity"] == 5).sum())
prior_crit = int((prior["Severity"] == 5).sum())

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(
        label="Total Incidents",
        value=f"{total_incidents:,}",
        delta=f"{recent_total - prior_total:+d} vs prior period",
        delta_color="inverse",  # Increase in incidents is bad -> red
    )
with kpi2:
    st.metric(
        label="Average Severity (1-5)",
        value=f"{avg_severity:.2f}",
        delta=f"{recent_avg_sev - prior_avg_sev:+.2f} vs prior period",
        delta_color="inverse",  # Higher severity is bad -> red
    )
with kpi3:
    st.metric(
        label="Critical Incidents (Severity 5)",
        value=f"{critical_count:,}",
        delta=f"{recent_crit - prior_crit:+d} vs prior period",
        delta_color="inverse",  # Rising critical count is bad -> red
    )

# ----------------------------------------------------------------------------
# 6. ALERTING LOGIC (Requirement #6: st.warning if critical incidents > threshold)
# ----------------------------------------------------------------------------
if critical_count > critical_threshold:
    st.warning(
        f"CRITICAL ALERT: Current selection records {critical_count} critical incidents (Severity 5), "
        f"exceeding the safety threshold of {critical_threshold}. Immediate supervisor intervention required!"
    )

st.divider()

# ----------------------------------------------------------------------------
# 4. VISUALIZATIONS (Requirement #4: Time-Series, Categorical, Map / Heatmap)
# ----------------------------------------------------------------------------
col_viz1, col_viz2 = st.columns(2)

# Visualization 1: Time-Series Trend Line with 7-Day Rolling Average
with col_viz1:
    st.subheader("Incident Frequency & Trend Over Time")
    daily = df.groupby(df["Date"].dt.date).size().reset_index(name="Daily Incidents")
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily = daily.sort_values("Date")
    daily["7-Day Rolling Avg"] = daily["Daily Incidents"].rolling(7, min_periods=1).mean()

    fig_trend = px.line(
        daily,
        x="Date",
        y=["Daily Incidents", "7-Day Rolling Avg"],
        labels={"value": "Incidents", "variable": "Metric"},
        color_discrete_map={"Daily Incidents": "#94a3b8", "7-Day Rolling Avg": "#dc2626"},
    )
    fig_trend.update_layout(legend=dict(orientation="h", y=1.1, x=0), margin=dict(t=15, b=10, l=10, r=10))
    st.plotly_chart(fig_trend, use_container_width=True)

# Visualization 2: Categorical Chart (Breakdown by Incident Type)
with col_viz2:
    st.subheader("Breakdown by Incident Classification")
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
        labels={"Incident_Type": "Classification", "Count": "Events"},
    )
    fig_bar.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=15, b=10, l=10, r=10), coloraxis_showscale=False)
    fig_bar.update_traces(textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

col_viz3, col_viz4 = st.columns(2)

# Visualization 3: Geospatial Map OR Shift/Day Heatmap
with col_viz3:
    if {"lat", "lon"}.issubset(df.columns) and df["lat"].notna().any():
        st.subheader("Facility Incident Map (Geospatial)")
        site_geo = df.groupby("Site").agg(lat=("lat", "mean"), lon=("lon", "mean"), Incidents=("Site", "count")).reset_index()
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
        st.subheader("Incidents by Shift & Day of Week")
        heat_df = df.copy()
        heat_df["Day_of_Week"] = heat_df["Date"].dt.day_name()
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot_heat = heat_df.groupby(["Shift", "Day_of_Week"]).size().reset_index(name="Count").pivot(index="Shift", columns="Day_of_Week", values="Count").reindex(columns=days_order).fillna(0)
        fig_heat = px.imshow(pivot_heat, text_auto=True, aspect="auto", color_continuous_scale="Reds", labels=dict(color="Incidents"))
        fig_heat.update_layout(margin=dict(t=15, b=10, l=10, r=10))
        st.plotly_chart(fig_heat, use_container_width=True)

# Visualization 4: Heatmap of Incidents by Shift & Day
with col_viz4:
    st.subheader("Incident Density by Shift & Day of Week")
    heat_df2 = df.copy()
    heat_df2["Day_of_Week"] = heat_df2["Date"].dt.day_name()
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot_heat2 = heat_df2.groupby(["Shift", "Day_of_Week"]).size().reset_index(name="Count").pivot(index="Shift", columns="Day_of_Week", values="Count").reindex(columns=days_order).fillna(0)
    fig_heat2 = px.imshow(pivot_heat2, text_auto=True, aspect="auto", color_continuous_scale="YlOrRd", labels=dict(color="Incidents"))
    fig_heat2.update_layout(margin=dict(t=15, b=10, l=10, r=10))
    st.plotly_chart(fig_heat2, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# 7. EXPORT FUNCTIONALITY (Requirement #7: Download filtered data as CSV)
# ----------------------------------------------------------------------------
st.subheader("Export Filtered HSE Incident Data")
st.markdown("Download the filtered records for executive reporting, compliance audits, or shift briefings.")

csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Filtered Data as CSV",
    data=csv_bytes,
    file_name=f"filtered_hse_incidents_{start_date}_to_{end_date}.csv",
    mime="text/csv",
)

with st.expander("Preview Filtered Data Table"):
    st.dataframe(df, use_container_width=True)
