"""
streamlit_app.py — HR Analytics & Data Warehouse
═════════════════════════════════════════════════
TAB 1 — OLTP Data Entry & Operations
  Form 1: Onboard New Employee      → employees + employee_job_history
  Form 2: Change Department (SCD2)  → employee_job_history (expire+insert) + employees
  Form 3: Create Project            → projects
  Form 4: Submit Performance Review → reviews

TAB 2 — OLAP Executive Analytics Dashboard
  KPIs, YoY trend, Top performers (DENSE_RANK), Attrition, Income, SCD2 History
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from app.db_manager import DatabaseConnection
from app.entities   import Employee, Project, Review
from app.managers   import (EmployeeManager, ProjectManager,
                             ReviewManager, AnalyticsManager)

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="HR Analytics & Data Warehouse",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#0f1117; }
[data-testid="stHeader"]           { background:transparent; }
h1,h2,h3 { color:#e2e8f0; }
.hdr {
  font-size:.9rem; font-weight:700; color:#7c83fd;
  text-transform:uppercase; letter-spacing:.1em;
  border-bottom:1px solid #1e2a3a; padding-bottom:6px; margin-bottom:12px;
}
.db-info {
  background:#0d1f0d; border:1px solid #1a3a1a; border-radius:8px;
  padding:12px 16px; font-size:.85rem; color:#86efac;
  font-family:monospace; white-space:pre-wrap;
}
div[data-testid="stMetricValue"]>div { color:#7c83fd!important; font-size:1.8rem!important; }
div[data-testid="stMetricLabel"]     { color:#94a3b8!important; }
</style>
""", unsafe_allow_html=True)

# ── Manager singletons ─────────────────────────────────────────
@st.cache_resource
def get_managers():
    return {
        "emp":       EmployeeManager(),
        "proj":      ProjectManager(),
        "rev":       ReviewManager(),
        "analytics": AnalyticsManager(),
    }

try:
    mgr        = get_managers()
    emp_mgr    : EmployeeManager  = mgr["emp"]
    proj_mgr   : ProjectManager   = mgr["proj"]
    rev_mgr    : ReviewManager    = mgr["rev"]
    analytics  : AnalyticsManager = mgr["analytics"]
except Exception as e:
    st.error(f"❌ Database connection failed: {e}")
    st.info("Check that MySQL is running and `.env` credentials are correct.")
    st.stop()

# ── Cached dropdowns (refresh every 5 min) ────────────────────
@st.cache_data(ttl=300)
def load_departments():
    return emp_mgr.get_departments()

@st.cache_data(ttl=300)
def load_job_roles():
    return emp_mgr.get_job_roles()

# ── Title ─────────────────────────────────────────────────────
st.title("🏢 Enterprise HR Analytics & Warehouse Portal")
st.caption("Database: `hr_analytics_dw`  ·  Star Schema  ·  SCD Type 2")
st.markdown("---")

tab1, tab2 = st.tabs([
    "📝  OLTP — Data Entry & Operations",
    "📈  OLAP — Executive Analytics Dashboard"
])


# ═════════════════════════════════════════════════════════════
# TAB 1 — OLTP DATA ENTRY
# ═════════════════════════════════════════════════════════════
with tab1:

    depts    = load_departments()
    roles    = load_job_roles()
    dept_map = {d["department_name"]: d["department_id"] for d in depts}
    role_map = {f"{r['job_role_name']} (Lvl {r['job_level']})": r
                for r in roles}

    # ── ROW 1: Onboard + SCD2 Change ─────────────────────────
    col1, col2 = st.columns(2)

    # ── FORM 1: Onboard New Employee ─────────────────────────
    with col1:
        st.markdown('<div class="hdr">➕ Form 1 — Onboard New Employee</div>', unsafe_allow_html=True)
        st.caption("Inserts into → `employees` + `employee_job_history` (Day-1 SCD2 record)")

        with st.form("form_onboard", clear_on_submit=True):
            f1c1, f1c2 = st.columns(2)
            emp_id    = f1c1.number_input("Employee ID", min_value=100000, max_value=999999, value=200001, step=1)
            age       = f1c2.number_input("Age", 18, 70, 28)
            fname     = f1c1.text_input("First Name")
            lname     = f1c2.text_input("Last Name")
            email     = st.text_input("Company Email")

            dept_name = st.selectbox("Department", list(dept_map.keys()) if dept_map else ["—"])
            role_key  = st.selectbox("Job Role & Level", list(role_map.keys()) if role_map else ["—"])

            f1c3, f1c4 = st.columns(2)
            income    = f1c3.number_input("Monthly Income ($)", 1000, 50000, 5000, step=500)
            gender    = f1c4.selectbox("Gender", ["Male","Female","Other","Prefer not to say"])
            marital   = f1c3.selectbox("Marital Status", ["Single","Married","Divorced"])
            yrs_co    = f1c4.number_input("Years at Company", 0, 40, 0)

            submitted = st.form_submit_button("🚀 Onboard Employee", use_container_width=True)

        if submitted:
            if fname and lname and email and dept_name in dept_map and role_key in role_map:
                role_info = role_map[role_key]
                new_emp = Employee(
                    employee_number  = emp_id,
                    first_name       = fname,
                    last_name        = lname,
                    email            = email,
                    department_id    = dept_map[dept_name],
                    job_role         = role_info["job_role_name"],
                    job_level        = role_info["job_level"],
                    monthly_income   = income,
                    gender           = gender,
                    marital_status   = marital,
                    years_at_company = yrs_co,
                    age              = age,
                )
                ok, msg = emp_mgr.create_employee(new_emp)
                if ok:
                    st.success(msg)
                    st.markdown('<div class="db-info">'
                        'Tables written:\n'
                        '  employees             → 1 row  (current employee state)\n'
                        '  employee_job_history  → 1 row  (Day-1 SCD2, is_current=1)\n\n'
                        'Tables NOT touched:\n'
                        '  departments, job_roles → looked up only\n'
                        '  reviews, projects, assignments → untouched'
                        '</div>', unsafe_allow_html=True)
                    load_departments.clear()
                else:
                    st.error(msg)
            else:
                st.warning("Please fill in all required fields.")

    # ── FORM 2: SCD2 — Change Department / Role ──────────────
    with col2:
        st.markdown('<div class="hdr">🔄 Form 2 — Change Department (SCD Type 2)</div>', unsafe_allow_html=True)
        st.caption("Touches `employee_job_history` (expire old → insert new) + `employees`")

        with st.expander("ℹ️ How SCD2 works here", expanded=False):
            st.markdown("""
| Step | Table | Action |
|------|-------|--------|
| 1 | `employee_job_history` | Old row: `is_current=0`, `end_date=yesterday` |
| 2 | `employee_job_history` | New row: new dept/role, `is_current=1`, `start=today` |
| 3 | `employees` | Update `department_id`, `job_role_id` |
""")

        with st.form("form_scd2"):
            target_id   = st.number_input("Employee ID to Transfer", min_value=1, value=10001, step=1)
            new_dept    = st.selectbox("New Department", list(dept_map.keys()) if dept_map else ["—"], key="scd2_dept")
            new_role_k  = st.selectbox("New Job Role & Level", list(role_map.keys()) if role_map else ["—"], key="scd2_role")
            new_income  = st.number_input("New Monthly Income ($)", 1000, 50000, 6000, step=500)
            reason      = st.selectbox("Change Reason", [
                "Department Transfer", "Promotion", "Role Change",
                "Restructuring", "Performance Upgrade"
            ])

            scd2_sub = st.form_submit_button("🔁 Apply SCD2 Transfer", use_container_width=True)

        if scd2_sub:
            if new_dept in dept_map and new_role_k in role_map:
                role_info = role_map[new_role_k]
                ok, msg = emp_mgr.change_department(
                    employee_id = target_id,
                    new_dept_id = dept_map[new_dept],
                    new_role    = role_info["job_role_name"],
                    new_level   = role_info["job_level"],
                    new_income  = new_income,
                    change_reason = reason
                )
                if ok:
                    st.success(msg)
                    st.markdown('<div class="db-info">'
                        'Tables written:\n'
                        '  employee_job_history  → OLD row: is_current=0, end_date=yesterday\n'
                        '  employee_job_history  → NEW row: is_current=1, start=today\n'
                        '  employees             → department_id + job_role_id updated\n\n'
                        'Tables NOT touched:\n'
                        '  reviews, projects, assignments, departments, job_roles'
                        '</div>', unsafe_allow_html=True)
                else:
                    st.error(msg)

    st.markdown("---")

    # ── ROW 2: Create Project + Submit Review ─────────────────
    col3, col4 = st.columns(2)

    # ── FORM 3: Create Project ────────────────────────────────
    with col3:
        st.markdown('<div class="hdr">📁 Form 3 — Create Project</div>', unsafe_allow_html=True)
        st.caption("Inserts into → `projects` only")

        with st.form("form_project", clear_on_submit=True):
            proj_name  = st.text_input("Project Name")
            proj_dept  = st.selectbox("Department", list(dept_map.keys()) if dept_map else ["—"], key="proj_dept")
            proj_status= st.selectbox("Status", ["Active","In Progress","Completed"])
            p1, p2     = st.columns(2)
            start_date = p1.date_input("Start Date", value=date.today())
            end_date   = p2.date_input("End Date",   value=date.today())

            proj_sub   = st.form_submit_button("💼 Create Project", use_container_width=True)

        if proj_sub:
            if proj_name and proj_dept in dept_map:
                new_proj = Project(
                    project_name  = proj_name,
                    department_id = dept_map[proj_dept],
                    status        = proj_status,
                    start_date    = start_date,
                    end_date      = end_date if proj_status != "Active" else None
                )
                ok, msg = proj_mgr.create_project(new_proj)
                if ok:
                    st.success(msg)
                    st.markdown('<div class="db-info">'
                        'Tables written:\n'
                        '  projects → 1 row inserted\n\n'
                        'Tables NOT touched:\n'
                        '  assignments → must be populated via ETL\n'
                        '  employees, reviews, departments, job_roles'
                        '</div>', unsafe_allow_html=True)
                else:
                    st.error(msg)
            else:
                st.warning("Fill project name and select a department.")

    # ── FORM 4: Submit Performance Review ────────────────────
    with col4:
        st.markdown('<div class="hdr">⭐ Form 4 — Submit Performance Review</div>', unsafe_allow_html=True)
        st.caption("Inserts into → `reviews` only")

        with st.form("form_review", clear_on_submit=True):
            rev_emp_id  = st.number_input("Employee ID", min_value=1, value=10001, step=1)
            rev_rating  = st.select_slider("Performance Rating", options=[1,2,3,4,5], value=3,
                                           format_func=lambda x: f"{x} ({'⭐'*x})")
            rev_date    = st.date_input("Review Date", value=date.today())
            rev_reviewer= st.number_input("Reviewer Employee ID (0 = skip)", min_value=0, step=1, value=0)

            rev_sub = st.form_submit_button("📋 Submit Review", use_container_width=True)

        if rev_sub:
            review = Review(
                employee_id        = rev_emp_id,
                performance_rating = rev_rating,
                review_date        = rev_date,
                reviewer_id        = rev_reviewer if rev_reviewer > 0 else None
            )
            ok, msg = rev_mgr.submit_review(review)
            if ok:
                badge = "🏆 High Performer!" if review.is_high_performer() else ""
                st.success(f"{msg}  {badge}")
                st.markdown('<div class="db-info">'
                    'Tables written:\n'
                    '  reviews → 1 row inserted\n\n'
                    'Tables NOT touched:\n'
                    '  employees, employee_job_history,\n'
                    '  projects, assignments, departments, job_roles'
                    '</div>', unsafe_allow_html=True)
            else:
                st.error(msg)

    st.markdown("---")

    # ── Live Table Views ──────────────────────────────────────
    st.markdown('<div class="hdr">📊 Live OLTP Table Preview</div>', unsafe_allow_html=True)
    tv1, tv2 = st.columns(2)

    with tv1:
        st.caption("**employees** (latest 20)")
        try:
            emps = emp_mgr.get_all_employees(limit=20)
            if emps:
                st.dataframe(pd.DataFrame(emps), use_container_width=True, hide_index=True)
            else:
                st.info("No employees found.")
        except Exception as e:
            st.error(f"⚠️ {e}")

    with tv2:
        st.caption("**projects** (latest 20)")
        try:
            projs = proj_mgr.get_all_projects()
            if projs:
                st.dataframe(pd.DataFrame(projs), use_container_width=True, hide_index=True)
            else:
                st.info("No projects found.")
        except Exception as e:
            st.error(f"⚠️ {e}")


# ═════════════════════════════════════════════════════════════
# TAB 2 — OLAP ANALYTICS DASHBOARD
# ═════════════════════════════════════════════════════════════
with tab2:
    st.header("Executive Data Warehouse Analytics — Star Schema")

    # ── KPIs ─────────────────────────────────────────────────
    try:
        kpis = analytics.get_kpis()
    except Exception as e:
        st.error(f"⚠️ Cannot reach database: {e}")
        kpis = {}

    if kpis:
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("👥 Employees",     f"{kpis.get('total_employees',0):,}")
        k2.metric("📋 Reviews",        f"{kpis.get('total_reviews',0):,}")
        k3.metric("🏛️ Departments",    str(kpis.get('departments',0)))
        k4.metric("📁 Projects",       str(kpis.get('projects',0)))
        k5.metric("📜 SCD2 Versions",  f"{kpis.get('scd2_versions',0):,}")
        k6.metric("⭐ Avg Rating",      f"{kpis.get('avg_rating',0)}/5")
    else:
        st.info("Run `CALL sp_run_full_etl_olap();` in MySQL to populate the Star Schema.")

    st.markdown("---")

    # ── YoY Trend + Quarterly ─────────────────────────────────
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="hdr">📈 Year-over-Year Performance Trend (by Department)</div>', unsafe_allow_html=True)
        try:
            yoy = pd.DataFrame(analytics.get_yoy_trend())
            if not yoy.empty:
                fig = px.line(yoy, x="year", y="avg_rating", color="department_name",
                              markers=True, template="plotly_dark",
                              labels={"avg_rating":"Avg Rating","year":"Year","department_name":"Dept"})
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No trend data yet.")
        except Exception as e:
            st.error(f"⚠️ {e}")

    with c2:
        st.markdown('<div class="hdr">📊 Avg Rating by Quarter</div>', unsafe_allow_html=True)
        try:
            qtly = pd.DataFrame(analytics.get_quarterly_trend())
            if not qtly.empty:
                fig2 = px.bar(qtly, x="quarter", y="avg_rating", text="avg_rating",
                              template="plotly_dark", color_discrete_sequence=["#7c83fd"])
                fig2.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10))
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"⚠️ {e}")

    # ── Top Performers — DENSE_RANK() ─────────────────────────
    st.markdown('<div class="hdr">🏆 Top Performers by Department — DENSE_RANK() Window Function</div>', unsafe_allow_html=True)
    top_n = st.slider("Show top N per department", 1, 10, 3)
    try:
        top_df = pd.DataFrame(analytics.get_top_performers(top_n))
        if not top_df.empty:
            st.dataframe(top_df, use_container_width=True, hide_index=True)
        else:
            st.info("No performer data — run the OLAP ETL stored procedure first.")
    except Exception as e:
        st.error(f"⚠️ {e}")

    st.markdown("---")

    # ── Dept Summary + Attrition ──────────────────────────────
    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="hdr">🏛️ Dept Compensation & Performance</div>', unsafe_allow_html=True)
        try:
            dept = pd.DataFrame(analytics.get_department_summary())
            if not dept.empty:
                fig3 = px.bar(dept, x="department_name", y=["avg_income","avg_rating"],
                              barmode="group", template="plotly_dark",
                              color_discrete_sequence=["#7c83fd","#4facfe"])
                fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10))
                st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.error(f"⚠️ {e}")

    with c4:
        st.markdown('<div class="hdr">🚨 Attrition Risk by Department</div>', unsafe_allow_html=True)
        try:
            attr = pd.DataFrame(analytics.get_attrition_risk())
            if not attr.empty:
                fig4 = px.sunburst(attr, path=["department_name","attrition"],
                                   values="employee_count", template="plotly_dark",
                                   color="attrition",
                                   color_discrete_map={"Yes":"#ef4444","No":"#22c55e"})
                fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10))
                st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.error(f"⚠️ {e}")

    # ── Income Box Plot ───────────────────────────────────────
    st.markdown('<div class="hdr">💰 Income Distribution by Department</div>', unsafe_allow_html=True)
    try:
        inc = pd.DataFrame(analytics.get_income_distribution())
        if not inc.empty:
            fig5 = px.box(inc, x="department_name", y="monthly_income",
                          color="department_name", template="plotly_dark",
                          labels={"monthly_income":"Monthly Income ($)","department_name":"Department"})
            fig5.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10,b=10))
            st.plotly_chart(fig5, use_container_width=True)
    except Exception as e:
        st.error(f"⚠️ {e}")

    st.markdown("---")

    # ── SCD2 History Explorer ─────────────────────────────────
    st.markdown('<div class="hdr">🕐 SCD Type 2 — Employee History Explorer</div>', unsafe_allow_html=True)
    st.caption("Shows all versions of an employee across employee_job_history / dim_employee")
    search_id = st.number_input("Enter Employee ID", min_value=1, value=10001, step=1)
    try:
        scd_df = pd.DataFrame(analytics.get_scd2_history(search_id))
        if not scd_df.empty:
            st.success(f"**{scd_df['name'].iloc[0]}** — {len(scd_df)} SCD2 version(s) found")
            st.dataframe(scd_df, use_container_width=True, hide_index=True)
            if len(scd_df) > 1:
                fig6 = px.line(scd_df, x="effective_start_date", y="monthly_income",
                               markers=True, template="plotly_dark",
                               color_discrete_sequence=["#7c83fd"],
                               title=f"Income History — {scd_df['name'].iloc[0]}")
                fig6.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info(f"No SCD2 records found for employee {search_id}. Check the dim_employee table.")
    except Exception as e:
        st.error(f"⚠️ {e}")