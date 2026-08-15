"""
managers.py
───────────
DAL Manager classes inheriting from DatabaseConnection.

BaseDAL         - raw execute helpers
EmployeeManager - CRUD + SCD2 trigger on BOTH employees & employee_job_history
ProjectManager  - project CRUD
ReviewManager   - review CRUD
AnalyticsManager- OLAP read-only analytics (window functions)

─────────────────────────────────────────────
HOW "ONBOARD NEW EMPLOYEE" TOUCHES THE DB:
─────────────────────────────────────────────
 Step 1 → INSERT into employees          (current state row)
 Step 2 → INSERT into employee_job_history (Day-1 SCD2 record,
           effective_start_date = today,
           effective_end_date   = 2099-12-31,
           is_current = 1,
           change_reason = 'New Hire')

 NO rows are inserted into:
   departments  — must exist already (looked up by ID)
   job_roles    — must exist already (looked up by name)
   reviews      — added separately via "Submit Review" form
   projects     — added separately via "Create Project" form
   assignments  — NOT handled via UI (populated by ETL)

─────────────────────────────────────────────
HOW "CHANGE DEPARTMENT (SCD2)" TOUCHES THE DB:
─────────────────────────────────────────────
 Step 1 → UPDATE employee_job_history   (expire old row: is_current=0,
           effective_end_date = yesterday)
 Step 2 → INSERT employee_job_history   (new row with new dept/role,
           effective_start_date = today,
           is_current = 1)
 Step 3 → UPDATE employees              (update department_id / job_role_id)
"""

from datetime import date, timedelta
from app.db_manager import DatabaseConnection
from app.entities import Employee, Project, Review


# ═══════════════════════════════════════════════════════════════
# BASE DAL
# ═══════════════════════════════════════════════════════════════
class BaseDAL(DatabaseConnection):
    """Base Data Access Layer. Inherits DB connection singleton."""
    pass


# ═══════════════════════════════════════════════════════════════
# EMPLOYEE MANAGER
# ═══════════════════════════════════════════════════════════════
class EmployeeManager(BaseDAL):
    """
    CRUD operations for employees.
    Onboarding → inserts into employees + employee_job_history.
    Department/Role change → SCD2 expire + new record in employee_job_history.
    """

    # ── helpers ─────────────────────────────────────────────────
    def _get_job_role_id(self, job_role_name: str, job_level: int) -> int | None:
        rows = self.execute_read(
            "SELECT job_role_id FROM job_roles WHERE job_role_name=%s AND job_level=%s LIMIT 1",
            (job_role_name, job_level)
        )
        return rows[0]["job_role_id"] if rows else None

    def _next_employee_sk(self) -> int:
        row = self.execute_read("SELECT COALESCE(MAX(employee_sk),0)+1 AS nxt FROM employee_job_history")
        return row[0]["nxt"]

    def get_departments(self) -> list[dict]:
        """Return all departments for dropdowns."""
        try:
            return self.execute_read("SELECT department_id, department_name FROM departments ORDER BY department_name")
        except Exception:
            return []

    def get_job_roles(self) -> list[dict]:
        """Return all job roles for dropdowns."""
        try:
            return self.execute_read("SELECT job_role_id, job_role_name, job_level FROM job_roles ORDER BY job_role_name, job_level")
        except Exception:
            return []

    # ── CREATE ──────────────────────────────────────────────────
    def create_employee(self, emp: Employee) -> tuple[bool, str]:
        """
        Onboard a new employee.
        Inserts into:
          1. employees              (current-state row)
          2. employee_job_history   (Day-1 SCD2 record)

        Returns (success: bool, message: str)
        """
        today = date.today().isoformat()
        far_future = "2099-12-31"

        try:
            # ── Look up job_role_id ──────────────────────────────
            job_role_id = self._get_job_role_id(emp.job_role, emp.job_level)
            if job_role_id is None:
                return False, (
                    f"Job role '{emp.job_role}' at level {emp.job_level} "
                    f"not found in job_roles table. "
                    f"Please pick a role that exists in the database."
                )

            # ── STEP 1: INSERT into employees ────────────────────
            emp_sql = """
                INSERT INTO employees
                    (employee_id, employee_number, first_name, last_name,
                     email, age, gender, marital_status, education_field,
                     distance_from_home, years_at_company, attrition,
                     department_id, job_role_id, manager_id)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.execute_write(emp_sql, (
                emp.employee_number, emp.employee_number,
                emp.first_name, emp.last_name, emp.email,
                emp.age, emp.gender, emp.marital_status,
                emp.education_field, emp.distance_from_home,
                emp.years_at_company, emp.attrition,
                emp.department_id, job_role_id,
                emp.manager_id
            ))

            # ── STEP 2: INSERT Day-1 row into employee_job_history
            next_sk = self._next_employee_sk()
            hist_sql = """
                INSERT INTO employee_job_history (
                    employee_sk, employee_id, department_id, job_role_id,
                    job_level, monthly_income, daily_rate, hourly_rate,
                    business_travel, years_since_last_promotion,
                    years_with_curr_manager, effective_start_date,
                    effective_end_date, is_current, change_reason
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            self.execute_write(hist_sql, (
                next_sk, emp.employee_number, emp.department_id, job_role_id,
                emp.job_level, emp.monthly_income, 0, 0,
                "Non-Travel", 0, 0,
                today, far_future, 1, "New Hire"
            ))

            return True, (
                f"✅ '{emp.full_name}' onboarded successfully!\n\n"
                f"• **employees** → 1 row inserted (current state)\n"
                f"• **employee_job_history** → 1 Day-1 SCD2 row inserted "
                f"(start={today}, end=2099-12-31, is_current=1)"
            )

        except RuntimeError as e:
            return False, f"❌ DB error: {e}"

    # ── READ ────────────────────────────────────────────────────
    def get_employee(self, employee_id: int) -> dict | None:
        try:
            rows = self.execute_read(
                """SELECT e.*, d.department_name, j.job_role_name
                   FROM employees e
                   JOIN departments d ON d.department_id = e.department_id
                   JOIN job_roles   j ON j.job_role_id   = e.job_role_id
                   WHERE e.employee_id = %s""",
                (employee_id,)
            )
            return rows[0] if rows else None
        except RuntimeError:
            return None

    def get_all_employees(self, limit: int = 50) -> list[dict]:
        try:
            return self.execute_read(
                """SELECT e.employee_id, e.first_name, e.last_name, e.email,
                          e.age, e.attrition, e.years_at_company,
                          d.department_name, j.job_role_name
                   FROM employees e
                   JOIN departments d ON d.department_id = e.department_id
                   JOIN job_roles   j ON j.job_role_id   = e.job_role_id
                   ORDER BY e.employee_id DESC
                   LIMIT %s""",
                (limit,)
            )
        except RuntimeError:
            return []

    # ── SCD2 UPDATE: Change Department or Role ───────────────────
    def change_department(self, employee_id: int,
                           new_dept_id: int,
                           new_role: str,
                           new_level: int,
                           new_income: float,
                           change_reason: str = "Department Transfer") -> tuple[bool, str]:
        """
        SCD Type 2 update: changing an employee's department/role.

        Touches employee_job_history TWICE:
          Step 1 → UPDATE old row  (set is_current=0, effective_end_date=yesterday)
          Step 2 → INSERT new row  (new dept/role, is_current=1, start=today)

        Also updates the employees table (step 3) with the new IDs.
        """
        today     = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        far_future = "2099-12-31"

        try:
            job_role_id = self._get_job_role_id(new_role, new_level)
            if job_role_id is None:
                return False, f"Job role '{new_role}' level {new_level} not found in job_roles."

            # ── STEP 1: Expire the current history row ───────────
            expired = self.execute_write("""
                UPDATE employee_job_history
                SET    is_current = 0,
                       effective_end_date = %s
                WHERE  employee_id = %s
                  AND  is_current  = 1
            """, (yesterday, employee_id))

            if expired == 0:
                return False, (
                    f"No active history row found for employee {employee_id}. "
                    f"Cannot apply SCD2."
                )

            # ── STEP 2: Insert new active history row ───────────
            next_sk = self._next_employee_sk()
            self.execute_write("""
                INSERT INTO employee_job_history (
                    employee_sk, employee_id, department_id, job_role_id,
                    job_level, monthly_income, daily_rate, hourly_rate,
                    business_travel, years_since_last_promotion,
                    years_with_curr_manager, effective_start_date,
                    effective_end_date, is_current, change_reason
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                next_sk, employee_id, new_dept_id, job_role_id,
                new_level, new_income, 0, 0,
                "Non-Travel", 0, 0,
                today, far_future, 1, change_reason
            ))

            # ── STEP 3: Sync the employees table ────────────────
            self.execute_write("""
                UPDATE employees
                SET department_id = %s,
                    job_role_id   = %s
                WHERE employee_id = %s
            """, (new_dept_id, job_role_id, employee_id))

            return True, (
                f"✅ SCD2 update applied for employee {employee_id}\n\n"
                f"• **employee_job_history** old row → expired (end={yesterday}, is_current=0)\n"
                f"• **employee_job_history** new row → inserted (start={today}, is_current=1)\n"
                f"• **employees** → department_id & job_role_id updated"
            )

        except RuntimeError as e:
            return False, f"❌ DB error: {e}"

    def mark_attrition(self, employee_id: int) -> bool:
        try:
            rows = self.execute_write(
                "UPDATE employees SET attrition='Yes' WHERE employee_id=%s",
                (employee_id,)
            )
            return rows > 0
        except RuntimeError:
            return False


# ═══════════════════════════════════════════════════════════════
# PROJECT MANAGER
# ═══════════════════════════════════════════════════════════════
class ProjectManager(BaseDAL):
    """CRUD for projects table."""

    def create_project(self, proj: Project) -> tuple[bool, str]:
        try:
            sql = """
                INSERT INTO projects (project_name, department_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            rows = self.execute_write(sql, (
                proj.project_name, proj.department_id,
                proj.start_date, proj.end_date, proj.status
            ))
            if rows > 0:
                return True, (
                    f"✅ Project '{proj.project_name}' created!\n\n"
                    f"• **projects** → 1 row inserted"
                )
            return False, "❌ Insert returned 0 rows."
        except RuntimeError as e:
            return False, f"❌ DB error: {e}"

    def get_all_projects(self) -> list[dict]:
        try:
            return self.execute_read(
                """SELECT p.project_id, p.project_name, d.department_name,
                          p.status, p.start_date, p.end_date
                   FROM projects p
                   JOIN departments d ON d.department_id = p.department_id
                   ORDER BY p.project_id DESC"""
            )
        except RuntimeError:
            return []


# ═══════════════════════════════════════════════════════════════
# REVIEW MANAGER
# ═══════════════════════════════════════════════════════════════
class ReviewManager(BaseDAL):
    """CRUD for reviews table."""

    def submit_review(self, review: Review) -> tuple[bool, str]:
        try:
            sql = """
                INSERT INTO reviews (employee_id, review_date, performance_rating, reviewer_id)
                VALUES (%s, %s, %s, %s)
            """
            rows = self.execute_write(sql, (
                review.employee_id, review.review_date,
                review.performance_rating, review.reviewer_id
            ))
            if rows > 0:
                return True, (
                    f"✅ Review submitted!\n\n"
                    f"• **reviews** → 1 row inserted "
                    f"(employee={review.employee_id}, "
                    f"rating={review.performance_rating}/5, "
                    f"date={review.review_date})"
                )
            return False, "❌ Insert returned 0 rows."
        except RuntimeError as e:
            return False, f"❌ DB error: {e}"

    def get_reviews_for_employee(self, employee_id: int) -> list[dict]:
        try:
            return self.execute_read(
                "SELECT * FROM reviews WHERE employee_id=%s ORDER BY review_date DESC",
                (employee_id,)
            )
        except RuntimeError:
            return []


# ═══════════════════════════════════════════════════════════════
# ANALYTICS MANAGER  (OLAP — Star Schema reads only)
# ═══════════════════════════════════════════════════════════════
class AnalyticsManager(BaseDAL):
    """
    Read-only analytics against the Star Schema (dim_* / fact_*).
    All queries use CTEs and Window Functions.
    """

    def get_kpis(self) -> dict:
        try:
            rows = self.execute_read("""
                SELECT
                    (SELECT COUNT(DISTINCT employee_id)
                       FROM dim_employee WHERE is_current=1)       AS total_employees,
                    (SELECT COUNT(*) FROM fact_performance_reviews) AS total_reviews,
                    (SELECT COUNT(*) FROM dim_department)           AS departments,
                    (SELECT COUNT(*) FROM dim_project)              AS projects,
                    (SELECT COUNT(*) FROM dim_employee)             AS scd2_versions,
                    (SELECT ROUND(AVG(performance_rating),2)
                       FROM fact_performance_reviews)              AS avg_rating
            """)
            return rows[0] if rows else {}
        except RuntimeError:
            return {}

    def get_top_performers(self, top_n: int = 3) -> list[dict]:
        """Top-N per dept using DENSE_RANK() window function."""
        try:
            return self.execute_read(f"""
                WITH ranked AS (
                    SELECT
                        CONCAT(de.first_name,' ',de.last_name) AS employee_name,
                        dd.department_name,
                        de.job_role,
                        de.job_level,
                        de.monthly_income,
                        ROUND(AVG(f.performance_rating),2)     AS avg_rating,
                        DENSE_RANK() OVER (
                            PARTITION BY dd.department_name
                            ORDER BY AVG(f.performance_rating) DESC,
                                     de.monthly_income DESC
                        ) AS dept_rank
                    FROM fact_performance_reviews f
                    JOIN dim_employee   de ON de.employee_sk   = f.employee_sk
                    JOIN dim_department dd ON dd.department_sk = f.department_sk
                    WHERE de.is_current = 1
                    GROUP BY de.employee_sk, de.first_name, de.last_name,
                             dd.department_name, de.job_role, de.job_level, de.monthly_income
                )
                SELECT * FROM ranked
                WHERE  dept_rank <= {top_n}
                ORDER  BY department_name, dept_rank
            """)
        except RuntimeError:
            return []

    def get_yoy_trend(self) -> list[dict]:
        try:
            return self.execute_read("""
                SELECT d.year, dept.department_name,
                       ROUND(AVG(f.performance_rating),3) AS avg_rating,
                       COUNT(*) AS reviews
                FROM fact_performance_reviews f
                JOIN dim_date       d    ON d.date_sk       = f.date_sk
                JOIN dim_department dept ON dept.department_sk = f.department_sk
                GROUP BY d.year, dept.department_name
                ORDER BY d.year
            """)
        except RuntimeError:
            return []

    def get_department_summary(self) -> list[dict]:
        try:
            return self.execute_read("""
                SELECT dept.department_name,
                       COUNT(DISTINCT de.employee_id)      AS headcount,
                       ROUND(AVG(de.monthly_income),0)     AS avg_income,
                       ROUND(AVG(f.performance_rating),2)  AS avg_rating
                FROM dim_employee de
                JOIN dim_department dept ON dept.department_sk = de.department_sk
                LEFT JOIN fact_performance_reviews f ON f.employee_sk = de.employee_sk
                WHERE de.is_current = 1
                GROUP BY dept.department_name
                ORDER BY avg_rating DESC
            """)
        except RuntimeError:
            return []

    def get_attrition_risk(self) -> list[dict]:
        try:
            return self.execute_read("""
                SELECT d.department_name, e.attrition, COUNT(*) AS employee_count
                FROM employees e
                JOIN departments d ON d.department_id = e.department_id
                GROUP BY d.department_name, e.attrition
                ORDER BY d.department_name
            """)
        except RuntimeError:
            return []

    def get_income_distribution(self) -> list[dict]:
        try:
            return self.execute_read("""
                SELECT dd.department_name, de.job_role, de.monthly_income
                FROM dim_employee de
                JOIN dim_department dd ON dd.department_sk = de.department_sk
                WHERE de.is_current = 1
            """)
        except RuntimeError:
            return []

    def get_scd2_history(self, employee_id: int) -> list[dict]:
        try:
            return self.execute_read("""
                SELECT
                    de.employee_sk,
                    CONCAT(de.first_name,' ',de.last_name) AS name,
                    dd.department_name,
                    de.job_role, de.job_level,
                    de.monthly_income,
                    de.change_reason,
                    de.effective_start_date,
                    de.effective_end_date,
                    IF(de.is_current=1,'✅ Current','📜 History') AS status
                FROM dim_employee de
                JOIN dim_department dd ON dd.department_sk = de.department_sk
                WHERE de.employee_id = %s
                ORDER BY de.effective_start_date
            """, (employee_id,))
        except RuntimeError:
            return []

    def get_quarterly_trend(self) -> list[dict]:
        try:
            return self.execute_read("""
                SELECT d.quarter,
                       ROUND(AVG(f.performance_rating),3) AS avg_rating,
                       COUNT(*) AS reviews
                FROM fact_performance_reviews f
                JOIN dim_date d ON d.date_sk = f.date_sk
                GROUP BY d.quarter
                ORDER BY d.quarter
            """)
        except RuntimeError:
            return []