# HSE Safety Command Center & Week 7 Deliverables

**Student Name:** Yvonne Wochuna  
**Course:** PLP Data Science / HSE Analytics  
**Submission Repository:** [https://github.com/wochuna/week7](https://github.com/wochuna/week7)  

This repository contains all technical code, data assets, communication deliverables, and capstone documentation required for the Week 7 HSE Safety Command Center assignment.

---

## Deliverables Summary

| Part | Rubric Item | Deliverable File | Description |
| :--- | :--- | :--- | :--- |
| **Part A** | Streamlit Dashboard | [`app_safety_dashboard.py`](./app_safety_dashboard.py) | Interactive command center with caching, KPI cards (inverse delta coloring), 4 visualizations, alert warning banner, and CSV export. |
| **Part A** | Primary HSE Dataset | [`safety_incidents.csv`](./safety_incidents.csv) | Real HSE incident logs (304 events across 5 facilities) with incident types, shift times, severity levels, and GPS coordinates. |
| **Part B.1** | Written Safety Alert (PDF) | [`Week7_Safety_Alert_YvonneWochuna.pdf`](./Week7_Safety_Alert_YvonneWochuna.pdf) | 1-page professional safety alert addressing night-shift slips at Depot B. Urgent, empathetic, and jargon-free. |
| **Part B.1** | Safety Alert (Markdown) | [`Week7_Safety_Alert_YvonneWochuna.md`](./Week7_Safety_Alert_YvonneWochuna.md) | Accessible markdown mirror of the safety alert document. |
| **Part B.1** | Alert PDF Generator | [`generate_safety_alert_pdf.py`](./generate_safety_alert_pdf.py) | Python script using ReportLab to build the 1-page safety alert PDF. |
| **Part B.2** | Role-Play Video (MP4) | [`Week7_Roleplay_YvonneWochuna.mp4`](./Week7_Roleplay_YvonneWochuna.mp4) | 2-3 minute video role-play presenting the safety alert to a skeptical technician using empathy and dashboard data. |
| **Part B.2** | Role-Play Script | [`ROLEPLAY_SCRIPT.md`](./ROLEPLAY_SCRIPT.md) | Complete dialogue script with timestamps, objection-handling techniques, and empathy coaching points. |
| **Part C** | Capstone Progress Update | [`capstone_week7_update.md`](./capstone_week7_update.md) | Answers all three required prompts: dashboard startup, Streamlit vs. Plotly Dash rationale, and visualization challenges (severity skew). |

---

## Part A: Streamlit Safety Dashboard Features

1. **Cached Data Loading (`@st.cache_data`):**  
   Auto-loads `safety_incidents.csv` with standard column normalization. Includes an automatic synthetic data generator fallback if no external file is present.
2. **Sidebar Controls & Filters:**  
   Multi-select for Site/Location, Date Range picker, Incident Type multi-select, and an Alert Threshold slider.
3. **KPI Metrics with Inverse Delta Coloring:**  
   Top-level metric cards (`Total Incidents`, `Average Severity`, and `Critical Incidents (Severity 5)`) use `delta_color="inverse"` so upward trends in risk or injury severity are visually flagged in red.
4. **Visualizations:**  
   - **Time-Series Trend Line:** Daily incident volume overlaid with a 7-day rolling average.
   - **Categorical Bar Chart:** Horizontal bar distribution by incident classification.
   - **Geospatial Map:** Mapbox facility scatter plot displaying incident clusters across locations.
   - **Shift x Day Heatmap:** Cross-tabulation identifying operational risk windows (e.g. night-shift hazards).
5. **Dynamic Interactivity:**  
   All downstream charts, metrics, and alerts update reactively on sidebar filter interactions.
6. **Proactive Alerting Logic:**  
   Displays an `st.warning` banner whenever critical incidents exceed the configured threshold.
7. **CSV Export Functionality:**  
   One-click CSV download of the filtered dataset via `st.download_button` and an expandable data table viewer.

### How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app_safety_dashboard.py
```

---

## Part B: Safety Alert & Role-Play Scenario

- **The Problem:** Depot B recorded **33 slip and trip incidents** (nearly double any other site), with **82% occurring during the Night Shift** around the transfer walkway. Ten were high-potential serious injury events (Potential SIFs).
- **The Approach:** Rather than blaming workers, the HSE alert and role-play dialogue acknowledge environmental root causes (poor drainage, flickering lighting) and implement physical fixes (LED upgrades, traction mats) alongside peer safety habits.

---

## Part C: Capstone Project Progress

The complete Week 7 progress report is detailed in [`capstone_week7_update.md`](./capstone_week7_update.md).
- **Framework Choice:** Streamlit + Plotly Express was chosen over Plotly Dash for rapid iterative development, built-in caching, and native executive UI components.
- **Key Visualization Challenge:** Addressing severity skew where high-frequency minor events dwarf critical low-frequency events (addressed via dual-layer rolling averages, isolated Severity-5 KPI cards, and multi-dimensional shift heatmaps).
