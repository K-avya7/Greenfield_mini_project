from app.db_manager import DatabaseConnection
from app.entities import Employee, Project, Review
from mysql.connector import Error

class BaseDAL:
    """Base Data Access Layer handling safe SQL transactions and error handling."""
    def __init__(self):
        self.db = DatabaseConnection()

    def execute_write(self, db_name: str, query: str, params: tuple = None) -> bool:
        conn = self.db.get_connection(db_name)
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or ())
            conn.commit()
            return True
        except Error as e:
            conn.rollback()
            print(f"[DAL WRITE ERROR]: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def execute_read(self, db_name: str, query: str, params: tuple = None) -> list:
        conn = self.db.get_connection(db_name)
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            print(f"[DAL READ ERROR]: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


class EmployeeManager(BaseDAL):
    """Handles CRUD operations for Employees and triggers DW updates."""

    def create_employee(self, emp: Employee) -> bool:
        query = """
            INSERT INTO hr_oltp.employees (employee_number, first_name, last_name, email, department_id, job_title)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (emp.employee_number, emp.first_name, emp.last_name, emp.email, emp.department_id, emp.job_title)
        success = self.execute_write("hr_oltp", query, params)
        
        if success:
            # Trigger SCD Type 2 synchronization in DW
            self.execute_write("hr_dw", "CALL sp_etl_dim_employee_scd2();")
        return success

    def update_employee_role(self, employee_number: int, new_title: str) -> bool:
        query = "UPDATE hr_oltp.employees SET job_title = %s WHERE employee_number = %s"
        success = self.execute_write("hr_oltp", query, (new_title, employee_number))
        if success:
            self.execute_write("hr_dw", "CALL sp_etl_dim_employee_scd2();")
        return success


class AnalyticsManager(BaseDAL):
    """Fetches executive analytics from the Data Warehouse Star Schema."""

    def get_department_performance(self) -> list:
        query = """
            SELECT 
                d.department_name,
                COUNT(f.fact_id) AS total_reviews,
                ROUND(AVG(f.performance_rating), 2) AS avg_rating,
                ROUND(AVG(f.monthly_income), 2) AS avg_salary
            FROM hr_dw.Fact_PerformanceReviews f
            JOIN hr_dw.Dim_Department d ON f.department_sk = d.department_sk
            GROUP BY d.department_name
        """
        return self.execute_read("hr_dw", query)