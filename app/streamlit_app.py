"""
streamlit_app.py — Enterprise HR Analytics & Data Warehouse Portal
══════════════════════════════════════════════════════════════════
4-page sidebar navigation:

  🏠 Dashboard          → OLAP Executive Analytics (Star Schema)
  👥 Employees          → OLTP: Onboard, SCD2 Transfer, Search
  📁 Projects           → OLTP: Create Projects, Assign Employees
  ⭐ Reviews & Analytics→ OLTP: Submit Reviews  |  OLAP: Deep Insights
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from app.db_manager import DatabaseConnection
from app.entities   import Employee, Project, Review
from app.managers   import (EmployeeManager, ProjectManager,
                             ReviewManager, AnalyticsManager)

# ──────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Analytics — Enterprise Data Warehouse",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# DESIGN SYSTEM — CSS
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Core palette ──────────────────────────────────────── */
:root {
  --bg:          #0d1117;
  --bg-card:     #161b27;
  --bg-card2:    #1c2333;
  --border:      #21293b;
  --border-hover:#2d3a52;
  --accent:      #6366f1;
  --accent-glow: rgba(99,102,241,0.18);
  --accent2:     #22d3ee;
  --success:     #22c55e;
  --danger:      #ef4444;
  --warning:     #f59e0b;
  --txt1:        #e2e8f0;
  --txt2:        #94a3b8;
  --txt3:        #64748b;
}

/* ── Background ─────────────────────────────────────────── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"]            { background: var(--bg) !important; }
[data-testid="stHeader"]          { background: transparent !important; border-bottom: 1px solid var(--border); }
section[data-testid="stSidebar"]  { background: #0a0e1a !important; border-right: 1px solid var(--border); }

/* ── Typography ─────────────────────────────────────────── */
h1 { color: var(--txt1) !important; font-size: 1.7rem !important; font-weight: 800 !important; letter-spacing: -0.02em !important; }
h2 { color: var(--txt1) !important; font-size: 1.25rem !important; font-weight: 700 !important; }
h3 { color: var(--txt1) !important; font-size: 1.05rem !important; font-weight: 600 !important; }
p, li, div { color: var(--txt2); }

/* ── Metric cards ───────────────────────────────────────── */
div[data-testid="metric-container"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  padding: 18px 20px !important;
  transition: border-color .2s, box-shadow .2s;
}
div[data-testid="metric-container"]:hover {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-glow) !important;
}
div[data-testid="stMetricValue"] > div {
  color: var(--accent) !important;
  font-size: 1.9rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em !important;
}
div[data-testid="stMetricLabel"] {
  color: var(--txt3) !important;
  font-size: 0.73rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.09em !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
  color: #fff !important; border: none !important;
  border-radius: 10px !important; font-weight: 700 !important;
  font-size: 0.9rem !important; letter-spacing: 0.02em !important;
  padding: 10px 20px !important;
  transition: transform .15s, box-shadow .15s !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 20px rgba(99,102,241,0.45) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Form containers ─────────────────────────────────────── */
[data-testid="stForm"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  padding: 4px 8px !important;
}

/* ── Inputs ──────────────────────────────────────────────── */
input[type="text"], input[type="number"],
input[type="email"], textarea,
div[data-baseweb="select"] > div {
  background: var(--bg) !important;
  border-color: var(--border) !important;
  color: var(--txt1) !important;
  border-radius: 8px !important;
}

/* ── Sidebar radio nav ───────────────────────────────────── */
div[data-testid="stSidebar"] .stRadio label {
  color: var(--txt2) !important;
  font-size: 0.93rem !important;
  padding: 6px 0 !important;
  transition: color .15s !important;
}
div[data-testid="stSidebar"] .stRadio label:hover { color: var(--txt1) !important; }

/* ── Section headers ─────────────────────────────────────── */
.sec-hdr {
  font-size: 0.72rem; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: 0.12em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px; margin: 20px 0 14px 0;
}

/* ── Info / DB status ────────────────────────────────────── */
.db-ok  { background:#052e16; border:1px solid #14532d; border-radius:8px;
          padding:10px 14px; color:#86efac; font-size:.78rem; font-family:monospace; }
.db-err { background:#2d0b0b; border:1px solid #7f1d1d; border-radius:8px;
          padding:10px 14px; color:#fca5a5; font-size:.78rem; font-family:monospace; }

/* ── Status badges ───────────────────────────────────────── */
.badge-active   { display:inline-block; background:#052e16; color:#6ee7b7;
                  padding:2px 10px; border-radius:20px; font-size:.72rem; font-weight:700; }
.badge-inactive { display:inline-block; background:#1e1b4b; color:#a5b4fc;
                  padding:2px 10px; border-radius:20px; font-size:.72rem; font-weight:700; }
.badge-warn     { display:inline-block; background:#451a03; color:#fcd34d;
                  padding:2px 10px; border-radius:20px; font-size:.72rem; font-weight:700; }

/* ── Dividers ────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 24px 0 !important; }

/* ── Expander ────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}

/* ── Dataframe ───────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# CHART HELPERS
# ──────────────────────────────────────────────────────────────
PALETTE = ["#6366f1","#22d3ee","#34d399","#f59e0b","#f472b6","#818cf8","#4ade80","#fb923c"]

def _chart_layout(**kwargs):
    base = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,17,23,0.6)",
        font=dict(color="#94a3b8", family="Inter, system-ui, sans-serif", size=12),
        margin=dict(t=30, b=20, l=10, r=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.08)",
                    borderwidth=1, font=dict(size=11)),
    )
    base.update(kwargs)
    return base


def _no_data(label: str):
    st.info(f"📭 No data yet for **{label}**. Populate the warehouse and run the ETL to see charts here.")


# ──────────────────────────────────────────────────────────────
# SINGLETON MANAGERS  (cached for session lifetime)
# ──────────────────────────────────────────────────────────────
@st.cache_resource
def _get_managers():
    return {
        "emp":       EmployeeManager(),
        "proj":      ProjectManager(),
        "rev":       ReviewManager(),
        "analytics": AnalyticsManager(),
    }

try:
    _mgr        = _get_managers()
    emp_mgr     : EmployeeManager  = _mgr["emp"]
    proj_mgr    : ProjectManager   = _mgr["proj"]
    rev_mgr     : ReviewManager    = _mgr["rev"]
    analytics   : AnalyticsManager = _mgr["analytics"]
    DatabaseConnection().execute_read("SELECT 1 AS ok")
    _db_ok = True
except Exception as _db_err:
    _db_ok = False
    _db_err_msg = str(_db_err)

# ──────────────────────────────────────────────────────────────
# CACHED DROPDOWN LOADERS  (refresh every 5 min)
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _depts():
    return emp_mgr.get_departments() if _db_ok else []

@st.cache_data(ttl=300)
def _roles():
    return emp_mgr.get_job_roles() if _db_ok else []

@st.cache_data(ttl=300)
def _projects_dd():
    return proj_mgr.get_projects_for_dropdown() if _db_ok else []


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏢 HR Analytics")
    st.markdown("<p style='color:#64748b;font-size:.78rem;margin-top:-10px;'>Enterprise Data Warehouse</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "👥 Employees", "📁 Projects & Assignments", "⭐ Reviews & Analytics"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── DB connection status ───────────────────────────────────
    st.markdown("<p class='sec-hdr'>Database</p>", unsafe_allow_html=True)
    if _db_ok:
        db_cfg = DatabaseConnection()._config
        st.markdown(
            f"<div class='db-ok'>✅ Connected<br>"
            f"<b>host:</b> {db_cfg['host']}<br>"
            f"<b>db:</b>   {db_cfg['database']}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='db-err'>❌ Connection failed<br>{_db_err_msg[:120]}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("<p style='color:#334155;font-size:.72rem;text-align:center;'>IBM HR Dataset · SCD Type 2<br>Star Schema · 130k rows</p>",
                unsafe_allow_html=True)

# Early-exit if DB is down
if not _db_ok:
    st.error(f"❌ Cannot reach MySQL: `{_db_err_msg}`")
    st.info("Verify MySQL is running and `.env` credentials are correct, then refresh.")
    st.stop()


# ══════════════════════════════════════════════════════════════
# PAGE 1 — 🏠 DASHBOARD  (OLAP Executive Analytics)
# ══════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":

    st.markdown("# 🏠 Executive Analytics Dashboard")
    st.markdown("<p style='color:#64748b;margin-top:-12px;'>Live from the Star Schema · OLAP Data Warehouse</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    # ── KPI METRICS ───────────────────────────────────────────
    kpis = analytics.get_kpis()
    if kpis:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("👥 Employees",    f"{kpis.get('total_employees', 0):,}")
        k2.metric("📋 Reviews",       f"{kpis.get('total_reviews', 0):,}")
        k3.metric("⭐ Avg Rating",     f"{kpis.get('avg_rating', 0)}/5")
        k4.metric("🏛 Departments",   str(kpis.get('departments', 0)))
        k5.metric("📁 Projects",      str(kpis.get('projects', 0)))
        k6.metric("📜 SCD2 Versions", f"{kpis.get('scd2_versions', 0):,}")
    else:
        st.warning("⚠️ OLAP tables appear empty. Run the ETL script (`oltp_to_olap.txt`) in MySQL Workbench first.")

    st.markdown("---")

    # ── ROW 1: YoY Trend + Quarterly ──────────────────────────
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("<div class='sec-hdr'>📈 Year-over-Year Performance Trend (by Department)</div>",
                    unsafe_allow_html=True)
        yoy = pd.DataFrame(analytics.get_yoy_trend())
        if not yoy.empty:
            fig = px.line(yoy, x="year", y="avg_rating", color="department_name",
                          markers=True, color_discrete_sequence=PALETTE,
                          labels={"avg_rating": "Avg Rating", "year": "Year",
                                  "department_name": "Department"})
            fig.update_traces(line_width=2.5, marker_size=7)
            fig.update_layout(**_chart_layout())
            st.plotly_chart(fig, use_container_width=True)
        else:
            _no_data("YoY Trend")

    with c2:
        st.markdown("<div class='sec-hdr'>📊 Avg Rating by Quarter</div>",
                    unsafe_allow_html=True)
        qtly = pd.DataFrame(analytics.get_quarterly_trend())
        if not qtly.empty:
            fig2 = px.bar(qtly, x="quarter", y="avg_rating", text="avg_rating",
                          color_discrete_sequence=["#6366f1"])
            fig2.update_traces(texttemplate='%{text:.2f}', textposition='outside',
                               marker_line_width=0, opacity=0.9)
            fig2.update_layout(**_chart_layout(
                xaxis=dict(tickvals=[1,2,3,4], ticktext=["Q1","Q2","Q3","Q4"])
            ))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            _no_data("Quarterly Trend")

    st.markdown("---")

    # ── ROW 2: Department Compensation & Performance ───────────
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("<div class='sec-hdr'>🏛 Department: Compensation vs. Performance</div>",
                    unsafe_allow_html=True)
        dept = pd.DataFrame(analytics.get_department_summary())
        if not dept.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(name="Avg Income ($)", x=dept["department_name"],
                                   y=dept["avg_income"], marker_color="#6366f1", opacity=0.85))
            fig3.add_trace(go.Scatter(name="Avg Rating", x=dept["department_name"],
                                      y=dept["avg_rating"] * 2000,  # scale for dual-axis
                                      mode="markers+lines",
                                      marker=dict(color="#22d3ee", size=10, symbol="diamond"),
                                      line=dict(color="#22d3ee", width=2),
                                      yaxis="y2"))
            fig3.update_layout(
                **_chart_layout(),
                yaxis=dict(title=dict(text="Avg Monthly Income ($)", font=dict(color="#6366f1"))),
                yaxis2=dict(title=dict(text="Avg Rating × 2000", font=dict(color="#22d3ee")),
                            overlaying="y", side="right", showgrid=False),
                barmode="group",
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            _no_data("Department Summary")

    with c4:
        st.markdown("<div class='sec-hdr'>🚨 Attrition Risk by Department</div>",
                    unsafe_allow_html=True)
        attr = pd.DataFrame(analytics.get_attrition_risk())
        if not attr.empty:
            fig4 = px.sunburst(attr, path=["department_name", "attrition"],
                               values="employee_count",
                               color="attrition",
                               color_discrete_map={"Yes": "#ef4444", "No": "#22c55e"},
                               )
            fig4.update_layout(**_chart_layout(margin=dict(t=20, b=0, l=0, r=0)))
            fig4.update_traces(textfont_size=12)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            _no_data("Attrition Risk")

    st.markdown("---")

    # ── ROW 3: Attrition Rate % Bars ──────────────────────────
    st.markdown("<div class='sec-hdr'>📉 Attrition Rate % per Department</div>",
                unsafe_allow_html=True)
    attr_score = pd.DataFrame(analytics.get_attrition_score_by_dept())
    if not attr_score.empty:
        fig5 = px.bar(attr_score, x="attrition_rate_pct", y="department_name",
                      orientation="h", text="attrition_rate_pct",
                      color="attrition_rate_pct",
                      color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
                      labels={"attrition_rate_pct": "Attrition Rate (%)",
                              "department_name": "Department"})
        fig5.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig5.update_layout(**_chart_layout(coloraxis_showscale=False))
        st.plotly_chart(fig5, use_container_width=True)
    else:
        _no_data("Attrition Score")

    st.markdown("---")

    # ── ROW 4: Income Box Plot ──────────────────────────────────
    st.markdown("<div class='sec-hdr'>💰 Monthly Income Distribution by Department</div>",
                unsafe_allow_html=True)
    inc = pd.DataFrame(analytics.get_income_distribution())
    if not inc.empty:
        fig6 = px.box(inc, x="department_name", y="monthly_income",
                      color="department_name", color_discrete_sequence=PALETTE,
                      labels={"monthly_income": "Monthly Income ($)", "department_name": "Department"})
        fig6.update_layout(**_chart_layout(showlegend=False))
        st.plotly_chart(fig6, use_container_width=True)
    else:
        _no_data("Income Distribution")


# ══════════════════════════════════════════════════════════════
# PAGE 2 — 👥 EMPLOYEES  (OLTP)
# ══════════════════════════════════════════════════════════════
elif page == "👥 Employees":

    st.markdown("# 👥 Employee Management")
    st.markdown("<p style='color:#64748b;margin-top:-12px;'>OLTP — employees · employee_job_history · departments · job_roles</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    depts    = _depts()
    roles    = _roles()
    dept_map = {d["department_name"]: d["department_id"] for d in depts}
    role_map = {f"{r['job_role_name']} (Lvl {r['job_level']})": r for r in roles}

    # ── EMPLOYEE SEARCH ────────────────────────────────────────
    st.markdown("<div class='sec-hdr'>🔍 Employee Search</div>", unsafe_allow_html=True)
    search_col, id_col = st.columns([3, 1])
    with search_col:
        name_q = st.text_input("Search by name", placeholder="e.g. James, Sarah...", label_visibility="collapsed")
    with id_col:
        scd2_id = st.number_input("SCD2 History by ID", min_value=1, value=10001, step=1, label_visibility="visible")

    s1, s2 = st.columns(2)
    with s1:
        if name_q:
            results = emp_mgr.search_employees(name_q)
            if results:
                st.success(f"Found **{len(results)}** matching employee(s)")
                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            else:
                st.info(f"No employees found matching '{name_q}'")

    with s2:
        scd2_df = pd.DataFrame(analytics.get_scd2_history(scd2_id))
        if not scd2_df.empty:
            emp_name = scd2_df["name"].iloc[0]
            ver_count = len(scd2_df)
            st.success(f"**{emp_name}** — {ver_count} SCD2 version(s)")
            st.dataframe(scd2_df, use_container_width=True, hide_index=True)
            if ver_count > 1:
                fig_scd = px.line(scd2_df, x="effective_start_date", y="monthly_income",
                                  markers=True, color_discrete_sequence=["#6366f1"],
                                  title=f"Income Journey — {emp_name}")
                fig_scd.update_traces(line_width=2.5, marker_size=9)
                fig_scd.update_layout(**_chart_layout(margin=dict(t=40, b=20)))
                st.plotly_chart(fig_scd, use_container_width=True)
        else:
            st.info(f"No SCD2 records in **dim_employee** for ID {scd2_id}.")

    st.markdown("---")

    # ── FORMS: Onboard + SCD2 ─────────────────────────────────
    col1, col2 = st.columns(2)

    # ── FORM 1: Onboard New Employee ──────────────────────────
    with col1:
        st.markdown("<div class='sec-hdr'>➕ Onboard New Employee</div>", unsafe_allow_html=True)
        st.caption("Writes to → `employees` + `employee_job_history` (Day-1 SCD2, is_current=1)")

        with st.form("form_onboard", clear_on_submit=True):
            st.markdown("<p style='font-weight:600; color:#e2e8f0; margin-bottom:5px;'>Identity & Role</p>", unsafe_allow_html=True)
            f1a, f1b = st.columns(2)
            emp_id  = f1a.number_input("Employee ID", min_value=200001, max_value=999999, value=200001, step=1)
            email   = f1b.text_input("Company Email")
            fname   = f1a.text_input("First Name")
            lname   = f1b.text_input("Last Name")

            dept_sel  = f1a.selectbox("Department", list(dept_map.keys()) or ["—"])
            role_sel  = f1b.selectbox("Job Role & Level", list(role_map.keys()) or ["—"])

            st.markdown("<p style='font-weight:600; color:#e2e8f0; margin-top:15px; margin-bottom:5px;'>Demographics & Compensation</p>", unsafe_allow_html=True)
            f2a, f2b, f2c = st.columns(3)
            age     = f2a.number_input("Age", 18, 70, 28)
            gender  = f2b.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
            marital = f2c.selectbox("Marital Status", ["Single", "Married", "Divorced"])
            
            edu     = f2a.selectbox("Education Level", [1, 2, 3, 4, 5], index=2, format_func=lambda x: f"{x} - {['Below College', 'College', 'Bachelor', 'Master', 'Doctor'][x-1]}")
            edu_fld = f2b.text_input("Education Field", value="Life Sciences")
            dist    = f2c.number_input("Distance from Home (km)", 0, 100, 5)
            
            income  = f2a.number_input("Monthly Income ($)", 1000, 50000, 5000, step=500)
            hike    = f2b.number_input("Salary Hike (%)", 0, 100, 10)
            stock   = f2c.number_input("Stock Option Level", 0, 3, 0)

            st.markdown("<p style='font-weight:600; color:#e2e8f0; margin-top:15px; margin-bottom:5px;'>Work History</p>", unsafe_allow_html=True)
            f3a, f3b, f3c = st.columns(3)
            num_comp = f3a.number_input("Num Companies Worked", 0, 20, 1)
            tot_yrs  = f3b.number_input("Total Working Years", 0, 50, 5)
            yrs_co   = f3c.number_input("Years at Company", 0, 40, 2)
            yrs_role = f3a.number_input("Years in Current Role", 0, 40, 2)
            train_t  = f3b.number_input("Training Times Last Year", 0, 10, 2)
            
            travel   = f3c.selectbox("Business Travel", ["Non-Travel", "Travel_Rarely", "Travel_Frequently"])
            overtime = f3a.selectbox("Over Time", ["No", "Yes"])
            attrit   = f3b.selectbox("Attrition", ["No", "Yes"])

            st.markdown("<p style='font-weight:600; color:#e2e8f0; margin-top:15px; margin-bottom:5px;'>Satisfaction (1-4)</p>", unsafe_allow_html=True)
            f4a, f4b, f4c, f4d = st.columns(4)
            env_sat = f4a.number_input("Environment", 1, 4, 3)
            job_inv = f4b.number_input("Job Involvement", 1, 4, 3)
            job_sat = f4c.number_input("Job Satisfaction", 1, 4, 3)
            rel_sat = f4d.number_input("Relationship", 1, 4, 3)
            wl_bal  = f4a.number_input("Work Life Balance", 1, 4, 3)

            st.markdown("<br>", unsafe_allow_html=True)
            onboard_btn = st.form_submit_button("🚀 Onboard Employee", use_container_width=True)

        if onboard_btn:
            missing = [f for f, v in [("First Name", fname), ("Last Name", lname), ("Email", email), ("Education Field", edu_fld)] if not v.strip()]
            
            if missing:
                st.warning(f"Please fill in: {', '.join(missing)}")
            elif dept_sel not in dept_map:
                st.warning("Select a valid department.")
            elif role_sel not in role_map:
                st.warning("Select a valid job role.")
            elif "@" not in email or "." not in email:
                st.warning("Please enter a valid email address.")
            elif any(char.isdigit() for char in fname):
                st.warning("First name cannot contain numbers.")
            elif any(char.isdigit() for char in lname):
                st.warning("Last name cannot contain numbers.")
            elif yrs_co > tot_yrs:
                st.warning("Years at company cannot be greater than total working years.")
            elif yrs_role > yrs_co:
                st.warning("Years in current role cannot be greater than years at company.")
            elif (age - 16) < tot_yrs:
                st.warning(f"Total working years ({tot_yrs}) is logically too high for an employee of age {age}.")
            else:
                role_info = role_map[role_sel]
                new_emp = Employee(
                    employee_number  = emp_id,
                    first_name       = fname.strip(),
                    last_name        = lname.strip(),
                    email            = email.strip(),
                    department_id    = dept_map[dept_sel],
                    job_role         = role_info["job_role_name"],
                    job_level        = role_info["job_level"],
                    monthly_income   = income,
                    gender           = gender,
                    marital_status   = marital,
                    education        = edu,
                    education_field  = edu_fld,
                    age              = age,
                    distance_from_home = dist,
                    num_companies_worked = num_comp,
                    total_working_years = tot_yrs,
                    years_at_company = yrs_co,
                    years_in_current_role = yrs_role,
                    attrition        = attrit,
                    business_travel  = travel,
                    over_time        = overtime,
                    stock_option_level = stock,
                    percent_salary_hike = hike,
                    environment_satisfaction = env_sat,
                    job_involvement  = job_inv,
                    job_satisfaction = job_sat,
                    relationship_satisfaction = rel_sat,
                    work_life_balance = wl_bal,
                    training_times_last_year = train_t
                )
                with st.spinner("Onboarding employee..."):
                    ok, msg = emp_mgr.create_employee(new_emp)
                if ok:
                    st.success(msg)
                    st.markdown(
                        "<div class='db-ok'>"
                        "Tables written:\n"
                        "  employees            → 1 row (current state)\n"
                        "  employee_job_history → 1 row (Day-1 SCD2, is_current=1)\n\n"
                        "Tables NOT touched:\n"
                        "  departments, job_roles → looked up only\n"
                        "  reviews, projects, assignments → untouched"
                        "</div>", unsafe_allow_html=True
                    )
                    _depts.clear(); _roles.clear()
                else:
                    st.error(msg)

    # ── FORM 2: SCD2 Department Transfer ──────────────────────
    with col2:
        st.markdown("<div class='sec-hdr'>🔄 Department Transfer (SCD Type 2)</div>",
                    unsafe_allow_html=True)
        st.caption("Writes to → `employee_job_history` (expire + new row) + `employees`")

        with st.expander("ℹ️ How SCD2 works here", expanded=False):
            st.markdown("""
| Step | Table | Action |
|------|-------|--------|
| 1 | `employee_job_history` | Old row → `is_current=0`, `effective_end_date=yesterday` |
| 2 | `employee_job_history` | New row → new dept/role, `is_current=1`, `start=today` |
| 3 | `employees`            | Update `department_id`, `job_role_id` |
""")

        with st.form("form_scd2"):
            target_id  = st.number_input("Employee ID to Transfer", min_value=1, value=10001, step=1)
            new_dept   = st.selectbox("New Department", list(dept_map.keys()) or ["—"], key="scd2_dept")
            new_role_k = st.selectbox("New Job Role & Level", list(role_map.keys()) or ["—"], key="scd2_role")
            new_income = st.number_input("New Monthly Income ($)", 1000, 50000, 6000, step=500)
            reason     = st.selectbox("Change Reason", [
                "Department Transfer", "Promotion", "Role Change",
                "Restructuring", "Performance Upgrade", "Internal Move"
            ])
            scd2_btn = st.form_submit_button("🔁 Apply SCD2 Transfer", use_container_width=True)

        if scd2_btn:
            if new_dept not in dept_map or new_role_k not in role_map:
                st.warning("Select a valid department and role.")
            else:
                role_info = role_map[new_role_k]
                with st.spinner("Applying SCD2 update..."):
                    ok, msg = emp_mgr.change_department(
                        employee_id   = target_id,
                        new_dept_id   = dept_map[new_dept],
                        new_role      = role_info["job_role_name"],
                        new_level     = role_info["job_level"],
                        new_income    = new_income,
                        change_reason = reason,
                    )
                if ok:
                    st.success(msg)
                    st.markdown(
                        "<div class='db-ok'>"
                        "Tables written:\n"
                        "  employee_job_history → OLD row: is_current=0, end_date=yesterday\n"
                        "  employee_job_history → NEW row: is_current=1, start=today\n"
                        "  employees            → department_id + job_role_id updated\n\n"
                        "OLAP dim_employee will be updated on next ETL run."
                        "</div>", unsafe_allow_html=True
                    )
                else:
                    st.error(msg)

    st.markdown("---")

    # ── LIVE EMPLOYEE TABLE ───────────────────────────────────
    st.markdown("<div class='sec-hdr'>📋 Live Employee Records (Latest 50)</div>",
                unsafe_allow_html=True)
    emps = emp_mgr.get_all_employees(limit=50)
    if emps:
        st.dataframe(pd.DataFrame(emps), use_container_width=True, hide_index=True)
    else:
        st.info("No employee records found.")

    st.markdown("---")

    # ── INCOME HEATMAP ────────────────────────────────────────
    st.markdown("<div class='sec-hdr'>🌡 Income Heatmap — Department × Job Level</div>",
                unsafe_allow_html=True)
    hm_data = pd.DataFrame(analytics.get_income_heatmap_data())
    if not hm_data.empty:
        hm_pivot = hm_data.pivot(index="department_name", columns="job_level", values="avg_income")
        hm_pivot.columns = [f"Level {c}" for c in hm_pivot.columns]
        fig_hm = px.imshow(
            hm_pivot, text_auto=True,
            color_continuous_scale=["#0d1117","#1e2a4a","#3b4ea0","#6366f1","#a5b4fc"],
            aspect="auto",
            labels={"x": "Job Level", "y": "Department", "color": "Avg Income ($)"},
        )
        fig_hm.update_traces(texttemplate="$%{z:,.0f}")
        fig_hm.update_layout(**_chart_layout(margin=dict(t=20, b=30)))
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        _no_data("Income Heatmap")


# ══════════════════════════════════════════════════════════════
# PAGE 3 — 📁 PROJECTS & ASSIGNMENTS  (OLTP)
# ══════════════════════════════════════════════════════════════
elif page == "📁 Projects & Assignments":

    st.markdown("# 📁 Projects & Assignments")
    st.markdown("<p style='color:#64748b;margin-top:-12px;'>OLTP — projects · assignments</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    depts    = _depts()
    dept_map = {d["department_name"]: d["department_id"] for d in depts}

    col1, col2 = st.columns(2)

    # ── FORM 3: Create Project ─────────────────────────────────
    with col1:
        st.markdown("<div class='sec-hdr'>📁 Create New Project</div>", unsafe_allow_html=True)
        st.caption("Writes to → `projects`")

        with st.form("form_project", clear_on_submit=True):
            proj_name   = st.text_input("Project Name", placeholder="e.g. HR Digital Transformation")
            proj_dept   = st.selectbox("Department", list(dept_map.keys()) or ["—"])
            proj_status = st.selectbox("Status", ["Active", "In Progress", "Completed", "On Hold"])

            p1, p2 = st.columns(2)
            proj_start = p1.date_input("Start Date", value=date.today())
            proj_end   = p2.date_input("End Date",   value=date.today())

            proj_btn = st.form_submit_button("💼 Create Project", use_container_width=True)

        if proj_btn:
            if not proj_name.strip():
                st.warning("Enter a project name.")
            elif proj_dept not in dept_map:
                st.warning("Select a valid department.")
            else:
                new_proj = Project(
                    project_name  = proj_name.strip(),
                    department_id = dept_map[proj_dept],
                    status        = proj_status,
                    start_date    = proj_start,
                    end_date      = proj_end if proj_status in ["Completed", "On Hold"] else None,
                )
                with st.spinner("Creating project..."):
                    ok, msg = proj_mgr.create_project(new_proj)
                if ok:
                    st.success(msg)
                    st.markdown(
                        "<div class='db-ok'>"
                        "Tables written:\n"
                        "  projects → 1 row inserted\n\n"
                        "Tables NOT touched:\n"
                        "  assignments → use 'Assign Employee' form below"
                        "</div>", unsafe_allow_html=True
                    )
                    _projects_dd.clear()
                else:
                    st.error(msg)

    # ── FORM 4: Assign Employee to Project ─────────────────────
    with col2:
        st.markdown("<div class='sec-hdr'>🔗 Assign Employee to Project</div>",
                    unsafe_allow_html=True)
        st.caption("Writes to → `assignments`")

        projects_dd  = _projects_dd()
        proj_id_map  = {f"{p['project_name']} ({p['status']})": p["project_id"] for p in projects_dd}

        with st.form("form_assign", clear_on_submit=True):
            asgn_emp_id   = st.number_input("Employee ID", min_value=1, value=10001, step=1)
            asgn_proj_sel = st.selectbox("Project", list(proj_id_map.keys()) or ["— no projects yet —"])
            asgn_role     = st.text_input("Role on Project", value="Contributor",
                                          placeholder="e.g. Lead Analyst, Developer...")
            a1, a2 = st.columns(2)
            asgn_alloc    = a1.number_input("Allocation (%)", 0, 100, 50, step=5)
            asgn_start    = a2.date_input("Assigned Date", value=date.today())
            asgn_end_chk  = st.checkbox("Set an end date for this assignment")
            asgn_end      = st.date_input("Assignment End Date", value=date.today()) if asgn_end_chk else None

            asgn_btn = st.form_submit_button("🔗 Assign Employee", use_container_width=True)

        if asgn_btn:
            if asgn_proj_sel not in proj_id_map:
                st.warning("Select a valid project. Create one first if the list is empty.")
            elif not asgn_role.strip():
                st.warning("Enter a role on the project.")
            else:
                with st.spinner("Assigning employee..."):
                    ok, msg = proj_mgr.assign_employee(
                        employee_id     = asgn_emp_id,
                        project_id      = proj_id_map[asgn_proj_sel],
                        role_on_project = asgn_role.strip(),
                        allocation_ratio= asgn_alloc,
                        assigned_date   = asgn_start,
                        end_date        = asgn_end,
                    )
                if ok:
                    st.success(msg)
                    st.markdown(
                        "<div class='db-ok'>"
                        "Tables written:\n"
                        "  assignments → 1 row inserted\n\n"
                        "Tables NOT touched:\n"
                        "  employees, projects, reviews"
                        "</div>", unsafe_allow_html=True
                    )
                else:
                    st.error(msg)

    st.markdown("---")

    # ── LIVE TABLES ────────────────────────────────────────────
    t1, t2 = st.columns(2)

    with t1:
        st.markdown("<div class='sec-hdr'>📋 All Projects</div>", unsafe_allow_html=True)
        projs = proj_mgr.get_all_projects()
        if projs:
            st.dataframe(pd.DataFrame(projs), use_container_width=True, hide_index=True)
        else:
            st.info("No projects yet. Create one above.")

    with t2:
        st.markdown("<div class='sec-hdr'>🔗 All Assignments</div>", unsafe_allow_html=True)
        asgns = proj_mgr.get_all_assignments()
        if asgns:
            st.dataframe(pd.DataFrame(asgns), use_container_width=True, hide_index=True)
        else:
            st.info("No assignments yet. Assign an employee to a project above.")

    st.markdown("---")

    # ── PROJECT BOTTLENECK ANALYSIS ────────────────────────────
    st.markdown("<div class='sec-hdr'>🚧 Project Bottleneck Analysis</div>", unsafe_allow_html=True)
    st.caption("Projects with highest employee count and total allocation — identifies resource bottlenecks")
    bottleneck = pd.DataFrame(analytics.get_project_bottleneck())
    if not bottleneck.empty and bottleneck["assigned_employees"].sum() > 0:
        active_bn = bottleneck[bottleneck["assigned_employees"] > 0].copy()
        if not active_bn.empty:
            fig_bn = px.bar(active_bn, x="project_name", y="total_allocation_pct",
                            color="assigned_employees",
                            color_continuous_scale=["#1e2a4a","#6366f1","#ef4444"],
                            text="assigned_employees",
                            labels={"total_allocation_pct": "Total Allocation (%)",
                                    "project_name": "Project",
                                    "assigned_employees": "# Employees"})
            fig_bn.update_traces(texttemplate='%{text} staff', textposition='outside')
            fig_bn.update_layout(**_chart_layout(coloraxis_showscale=False))
            st.plotly_chart(fig_bn, use_container_width=True)
        else:
            _no_data("Bottleneck Chart (no assignments yet)")
        st.dataframe(bottleneck, use_container_width=True, hide_index=True)
    else:
        st.info("📭 No assignments exist yet — the bottleneck chart will appear once employees are assigned to projects.")


# ══════════════════════════════════════════════════════════════
# PAGE 4 — ⭐ REVIEWS & ANALYTICS
# ══════════════════════════════════════════════════════════════
elif page == "⭐ Reviews & Analytics":

    st.markdown("# ⭐ Reviews & Deep Analytics")
    st.markdown("<p style='color:#64748b;margin-top:-12px;'>OLTP reviews form + OLAP insights — Window Functions · CTEs · LAG · DENSE_RANK</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    # ── ROW 1: Submit Review + Top Performers ─────────────────
    c1, c2 = st.columns([1, 2])

    # ── FORM 5: Submit Performance Review ─────────────────────
    with c1:
        st.markdown("<div class='sec-hdr'>⭐ Submit Performance Review</div>",
                    unsafe_allow_html=True)
        st.caption("Writes to → `reviews`")

        with st.form("form_review", clear_on_submit=True):
            rev_emp     = st.number_input("Employee ID", min_value=1, value=10001, step=1)
            rev_rating  = st.select_slider(
                "Performance Rating",
                options=[1, 2, 3, 4, 5], value=3,
                format_func=lambda x: f"{'⭐'*x}  ({x}/5)"
            )
            rev_date    = st.date_input("Review Date", value=date.today())
            rev_env     = st.slider("Environment Satisfaction", 1, 4, 3)
            rev_jobi    = st.slider("Job Involvement",          1, 4, 3)
            rev_jobsat  = st.slider("Job Satisfaction",         1, 4, 3)
            rev_rel     = st.slider("Relationship Satisfaction",1, 4, 3)
            rev_wlb     = st.slider("Work Life Balance",        1, 4, 3)
            rev_reviewer = st.number_input("Reviewer Employee ID (0 = none)", min_value=0, step=1, value=0)

            rev_btn = st.form_submit_button("📋 Submit Review", use_container_width=True)

        if rev_btn:
            review = Review(
                employee_id        = rev_emp,
                performance_rating = rev_rating,
                review_date        = rev_date,
                reviewer_id        = rev_reviewer if rev_reviewer > 0 else None,
            )
            with st.spinner("Submitting review..."):
                ok, msg = rev_mgr.submit_review(review)
            if ok:
                badge = "🏆 High Performer!" if review.is_high_performer() else ""
                st.success(f"{msg}  {badge}")
                st.markdown(
                    "<div class='db-ok'>"
                    "Tables written:\n"
                    "  reviews → 1 row inserted\n\n"
                    "Tables NOT touched:\n"
                    "  employees, employee_job_history,\n"
                    "  projects, assignments, departments, job_roles"
                    "</div>", unsafe_allow_html=True
                )
            else:
                st.error(msg)

    # ── TOP PERFORMERS — DENSE_RANK ────────────────────────────
    with c2:
        st.markdown("<div class='sec-hdr'>🏆 Top Performers by Department — DENSE_RANK()</div>",
                    unsafe_allow_html=True)
        st.caption("Uses SQL: `DENSE_RANK() OVER (PARTITION BY department_name ORDER BY AVG(rating) DESC)`")
        top_n  = st.slider("Show top N per department", 1, 10, 3, key="top_n_slider")
        top_df = pd.DataFrame(analytics.get_top_performers(top_n))
        if not top_df.empty:
            # Color rank 1 entries
            def _style_rank(row):
                if row.get("dept_rank") == 1:
                    return ["background-color: rgba(99,102,241,0.12)"] * len(row)
                return [""] * len(row)
            styled = top_df.style.apply(_style_rank, axis=1)
            st.dataframe(styled, use_container_width=True, hide_index=True)

            fig_top = px.bar(top_df, x="avg_rating", y="employee_name",
                             orientation="h", color="department_name",
                             color_discrete_sequence=PALETTE,
                             text="avg_rating",
                             labels={"avg_rating":"Avg Rating","employee_name":"Employee"})
            fig_top.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_top.update_layout(**_chart_layout(height=max(300, len(top_df)*28 + 60)))
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            _no_data("Top Performers (run OLAP ETL first)")

    st.markdown("---")

    # ── YoY WITH LAG ──────────────────────────────────────────
    st.markdown("<div class='sec-hdr'>📊 Year-over-Year Trend with Performance Delta (LAG Window Function)</div>",
                unsafe_allow_html=True)
    st.caption("Uses SQL: `LAG(avg_performance) OVER (ORDER BY year)` inside a CTE")

    yoy_delta = pd.DataFrame(analytics.get_yoy_with_delta())
    if not yoy_delta.empty:
        yy1, yy2 = st.columns([3, 2])
        with yy1:
            fig_yoy = go.Figure()
            fig_yoy.add_trace(go.Scatter(
                x=yoy_delta["year"], y=yoy_delta["avg_performance"],
                mode="lines+markers", name="Avg Performance",
                line=dict(color="#6366f1", width=3),
                marker=dict(size=10, color="#6366f1"),
            ))
            fig_yoy.add_trace(go.Bar(
                x=yoy_delta["year"], y=yoy_delta["performance_change"].fillna(0),
                name="YoY Change", marker_color=[
                    "#22c55e" if v >= 0 else "#ef4444"
                    for v in yoy_delta["performance_change"].fillna(0)
                ],
                opacity=0.6, yaxis="y2",
            ))
            fig_yoy.update_layout(
                **_chart_layout(),
                yaxis=dict(title=dict(text="Avg Performance", font=dict(color="#6366f1"))),
                yaxis2=dict(title=dict(text="YoY Change", font=dict(color="#22c55e")),
                            overlaying="y", side="right", showgrid=False),
            )
            st.plotly_chart(fig_yoy, use_container_width=True)

        with yy2:
            st.dataframe(
                yoy_delta[["year", "total_reviews", "avg_performance",
                            "prev_year_avg", "performance_change"]],
                use_container_width=True, hide_index=True
            )
    else:
        _no_data("YoY Delta (run OLAP ETL first)")

    st.markdown("---")

    # ── HEADCOUNT GROWTH TREND ─────────────────────────────────
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("<div class='sec-hdr'>📈 Employee Headcount Growth Over Time</div>",
                    unsafe_allow_html=True)
        hc = pd.DataFrame(analytics.get_headcount_trend())
        if not hc.empty:
            fig_hc = px.area(hc, x="hire_year", y="new_employees",
                             color_discrete_sequence=["#6366f1"],
                             labels={"hire_year":"Year","new_employees":"New Employees"})
            fig_hc.update_traces(fill="tozeroy",
                                  line=dict(width=2.5, color="#6366f1"),
                                  fillcolor="rgba(99,102,241,0.15)")
            fig_hc.update_layout(**_chart_layout())
            fig_hc.update_xaxes(dtick=1)
            st.plotly_chart(fig_hc, use_container_width=True)
        else:
            _no_data("Headcount Trend (run OLAP ETL first)")

    # ── TOP EARNERS ────────────────────────────────────────────
    with c4:
        st.markdown("<div class='sec-hdr'>💎 Top Earners</div>", unsafe_allow_html=True)
        n_earners = st.slider("Show top N earners", 5, 50, 15, key="earners_slider")
        earners   = pd.DataFrame(analytics.get_top_earners(n_earners))
        if not earners.empty:
            fig_earn = px.bar(earners, x="monthly_income", y="employee_name",
                              orientation="h", color="department_name",
                              color_discrete_sequence=PALETTE,
                              text="monthly_income",
                              labels={"monthly_income":"Monthly Income ($)","employee_name":"Employee"})
            fig_earn.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_earn.update_layout(**_chart_layout(height=max(300, n_earners * 28 + 60)))
            st.plotly_chart(fig_earn, use_container_width=True)
        else:
            _no_data("Top Earners")
