import streamlit as st
import pandas as pd
import plotly.express as px
from app.db_manager import DatabaseConnection
from app.entities import Employee, Project
from app.managers import EmployeeManager, AnalyticsManager, BaseDAL

# Page Configuration
st.set_page_config(
    page_title="Enterprise HR Analytics & Data Warehouse",
    page_icon="📊",
    layout="wide"
)

# Initialize Managers
emp_manager = EmployeeManager()
analytics_manager = AnalyticsManager()
dal = BaseDAL()

st.title("🏢 Enterprise HR Analytics & Warehouse Portal")
st.markdown("---")

# Navigation Tabs
tab1, tab2 = st.tabs(["📝 OLTP Data Entry & Operations", "📈 OLAP Executive Analytics Dashboard"])

# =============================================================================
# TAB 1: OLTP DATA ENTRY & OPERATIONS
# =============================================================================
with tab1:
    st.header("Operational Management & Onboarding")
    
    col1, col2 = st.columns(2)
    
    # Form 1: Onboard New Employee
    with col1:
        st.subheader("➕ Onboard New Employee")
        with st.form("onboard_employee_form"):
            emp_num = st.number_input("Employee ID", min_value=100000, max_value=999999, step=1)
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            email = st.text_input("Company Email")
            dept_id = st.number_input("Department ID", min_value=1, max_value=10, value=1)
            job_title = st.text_input("Job Title", value="Software Engineer")
            
            submit_onboard = st.form_submit_button("Onboard Employee")
            
            if submit_onboard:
                if first_name and last_name and email:
                    new_emp = Employee(emp_num, first_name, last_name, email, dept_id, job_title)
                    if emp_manager.create_employee(new_emp):
                        st.success(f"Employee {first_name} {last_name} onboarded! SCD Type 2 record initialized in DW.")
                    else:
                        st.error("Failed to onboard employee. ID or Email might already exist.")
                else:
                    st.warning("Please fill out all required fields.")

    # Form 2: Update Role (Triggers SCD Type 2 Update)
    with col2:
        st.subheader("🔄 Update Role / Department (SCD Type 2)")
        with st.form("update_role_form"):
            target_emp_num = st.number_input("Target Employee ID", min_value=100000, max_value=999999, step=1)
            new_title = st.text_input("New Job Title")
            
            submit_update = st.form_submit_button("Promote / Change Role")
            
            if submit_update:
                if new_title:
                    if emp_manager.update_employee_role(target_emp_num, new_title):
                        st.success(f"Role updated to '{new_title}'. Previous SCD2 record expired and new record activated in DW!")
                    else:
                        st.error("Employee update failed.")
                else:
                    st.warning("Please enter a new job title.")

    st.markdown("---")
    
    # Recent Employees Table View
    st.subheader("📋 Recent Operational Employees (OLTP)")
    recent_emps = dal.execute_read("hr_oltp", "SELECT * FROM employees ORDER BY created_at DESC LIMIT 10")
    if recent_emps:
        st.dataframe(pd.DataFrame(recent_emps), use_container_width=True)
    else:
        st.info("No employee records found in OLTP database.")


# =============================================================================
# TAB 2: OLAP EXECUTIVE ANALYTICS DASHBOARD
# =============================================================================
with tab2:
    st.header("Executive Data Warehouse Analytics (Star Schema)")
    
    # 1. High-Level Metrics Row
    metric_query = """
        SELECT 
            COUNT(DISTINCT employee_sk) as total_emp,
            ROUND(AVG(monthly_income), 2) as avg_sal,
            ROUND(AVG(performance_rating), 2) as avg_perf
        FROM hr_dw.Fact_PerformanceReviews
    """
    metrics = dal.execute_read("hr_dw", metric_query)
    
    if metrics:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Warehouse Records", f"{metrics[0]['total_emp']:,}")
        m2.metric("Average Monthly Income", f"${metrics[0]['avg_sal']:,.2f}")
        m3.metric("Avg Performance Score", f"{metrics[0]['avg_perf']} / 5.0")

    st.markdown("---")
    
    # 2. Top-Performing Employees per Department (SQL Window Function: DENSE_RANK)
    st.subheader("🏆 Top Performers by Department (Window Function Analysis)")
    top_performers_query = """
        WITH RankedEmployees AS (
            SELECT 
                e.employee_name,
                d.department_name,
                e.job_role,
                f.performance_rating,
                f.monthly_income,
                DENSE_RANK() OVER (
                    PARTITION BY d.department_name 
                    ORDER BY f.performance_rating DESC, f.monthly_income DESC
                ) as rank_num
            FROM hr_dw.Fact_PerformanceReviews f
            JOIN hr_dw.Dim_Employee e ON f.employee_sk = e.employee_sk
            JOIN hr_dw.Dim_Department d ON f.department_sk = d.department_sk
            WHERE e.is_current = 1
        )
        SELECT department_name, rank_num, employee_name, job_role, performance_rating, monthly_income
        FROM RankedEmployees 
        WHERE rank_num <= 3
        ORDER BY department_name, rank_num;
    """
    top_df = pd.DataFrame(dal.execute_read("hr_dw", top_performers_query))
    if not top_df.empty:
        st.dataframe(top_df, use_container_width=True)

    st.markdown("---")
    
    # 3. Interactive Visualizations
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("📊 Average Salary by Department")
        dept_perf_df = pd.DataFrame(analytics_manager.get_department_performance())
        if not dept_perf_df.empty:
            fig_sal = px.bar(
                dept_perf_df, 
                x='department_name', 
                y='avg_salary',
                color='department_name',
                text_auto='.2s',
                title="Department Compensation Metrics"
            )
            st.plotly_chart(fig_sal, use_container_width=True)

    with chart_col2:
        st.subheader("🚨 Employee Attrition Risk Distribution")
        attrition_query = """
            SELECT 
                d.department_name,
                f.attrition,
                COUNT(*) as employee_count
            FROM hr_dw.Fact_PerformanceReviews f
            JOIN hr_dw.Dim_Department d ON f.department_sk = d.department_sk
            GROUP BY d.department_name, f.attrition
        """
        attrition_df = pd.DataFrame(dal.execute_read("hr_dw", attrition_query))
        if not attrition_df.empty:
            fig_attr = px.pie(
                attrition_df, 
                names='attrition', 
                values='employee_count',
                hole=0.4,
                title="Overall Attrition Proportion"
            )
            st.plotly_chart(fig_attr, use_container_width=True)