# Capstone Project Progress Update - Week 7

**Student Name:** Yvonne Wochuna  
**Course:** PLP Data Science / HSE Analytics Specialization  
**Project Title:** HSE Safety Command Center: Predictive Incident Analytics & Risk Mitigation Platform  
**Submission Date:** September 2026  

---

## 1. Did you start building your Capstone dashboard?

**Yes.** I have officially started building the core architecture and user interface for my Capstone safety intelligence dashboard. 

During this week, I focused on establishing the structural foundation:
- **Data Ingestion and Caching Layer:** Implemented high-performance data intake using Streamlit's `@st.cache_data`. This ensures that raw operational logs (such as incident frequencies, shift allocations, severity indices, and GPS coordinates) are parsed once and held in memory, eliminating redundant disk I/O when users interact with visual controls.
- **Hierarchical Layout and Sidebar Controls:** Designed a centralized command sidebar featuring multi-select filters for operating facilities (`Site`), temporal scope (`Date Range`), incident classifications (`Incident Type`), and customizable threshold triggers for high-severity events.
- **Proactive Risk Metric Cards (KPIs):** Built top-level executive metrics (Total Incidents, Average Severity, and Critical Severity-5 / Potential SIF counts) utilizing inverse delta coloring (`delta_color="inverse"`). This ensures that upward trends in incident counts or injury severity immediately signal danger in red, directing supervisory attention to emerging hotspots.
- **Analytical Visualizations:** Created an initial suite of reactive charts, including a 7-day rolling average time-series trend line, a categorical incident distribution chart, a geographic Mapbox facility map, and a shift-by-day heatmap.

---

## 2. What library are you using (Streamlit vs. Plotly Dash)?

I selected **Streamlit paired with Plotly Express (`plotly.express`)** as my primary visualization and application stack.

### Key Technical Reasons for Choosing Streamlit + Plotly:
1. **Rapid Iteration and Declarative Model:** Streamlit's top-to-bottom reactive execution model enables fast prototyping without the overhead of maintaining complex callback graphs (which can become difficult to debug and maintain in Plotly Dash as the dashboard scales).
2. **Built-in Performance Optimization (`@st.cache_data`):** Safety analytics requires slicing thousands of incident records across multiple dimensions (sites, shifts, severity levels). Streamlit's caching mechanism keeps the dashboard snappy and responsive during live site inspections.
3. **Interactive Visual Quality with Plotly:** While Streamlit provides the interface controls and layout grid, Plotly delivers rich, interactive charts with customizable hover cards, zoom/pan capabilities, dynamic color scales, and smooth Mapbox integration for geographic site mapping.
4. **Intuitive Executive Usability:** Features like `st.metric` with `delta_color="inverse"` and conditional alerting banners (`st.warning`) allow the command center to communicate urgency directly to field supervisors and leadership without unnecessary technical clutter.

---

## 3. What is one challenge you faced in visualizing your specific Capstone data?

### The Challenge: Visualizing Disproportionate Severity Skew (High-Frequency Minor Events vs. Low-Frequency Catastrophic SIFs)
A major challenge in HSE data visualization is the inherent skew between incident frequency and incident severity:
- **The Problem:** The vast majority of logged events are low-severity incidents (Severity 1-2, such as minor cuts or near misses), whereas critical events (Severity 5, potential Fatalities or Life-Altering Injuries) occur infrequently. When plotted on standard time-series or bar charts, the high volume of minor incidents completely dwarfs and obscures the critical events. A facility might appear "safe" due to a low overall incident count, while silently harboring multiple critical near-misses that could lead to a fatality.
- **Specific Example in the Data:** At **Depot B**, minor slips and trips accounted for 33 events, with 82% concentrated during night shifts near the transfer walkway. Ten of these incidents were classified as Potential SIFs (Significant Injury or Fatality). On a standard aggregate bar chart, these dangerous precursors were easily masked by overall plant operations.
- **How I Solved / Am Addressing It:**
  1. **Dual-Layered Analytical Views:** Implemented a 7-day rolling trend line to smooth daily reporting noise, paired with explicit categorical filtering so safety officers can isolate high-potential risks.
  2. **Dedicated Critical Incident KPIs and Threshold Alerting:** Placed Severity-5 incidents in an isolated KPI card with inverse delta highlighting and built an alert banner (`st.warning`) that automatically triggers when critical incidents exceed a defined safety threshold.
  3. **Multi-Dimensional Heatmaps:** Added a Shift x Day-of-Week heatmap matrix that highlights systemic organizational risk windows (e.g., night-shift fatigue patterns) independent of raw volume counts.

---

## 4. Next Steps for Week 8

1. **Predictive Risk Scoring:** Integrate a machine learning classification model to assign a dynamic predictive risk score to active work permits based on weather, shift fatigue, and historical incident frequency.
2. **Corrective Action Tracking:** Add an interactive module allowing safety managers to log and track closed-loop corrective actions directly from the dashboard view.
3. **Automated Executive PDF Export:** Extend the reporting module to allow one-click PDF safety alert generation based on filtered dashboard findings.
