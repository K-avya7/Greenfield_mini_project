#!/usr/bin/env python3
"""
main.py — Connectivity Smoke Test
══════════════════════════════════
Quick sanity check that confirms:
  1. .env credentials are loaded correctly
  2. MySQL is reachable
  3. Core OLTP tables exist and are populated
  4. Core OLAP (Star Schema) tables exist and are populated

Run with:
    python main.py

To launch the Streamlit app instead run:
    streamlit run app/streamlit_app.py
"""

import sys
from app.db_manager import DatabaseConnection
from app.entities   import Employee, Project, Review
from app.managers   import EmployeeManager, ProjectManager, ReviewManager, AnalyticsManager


def section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def test_entities():
    """Confirm entity classes instantiate correctly."""
    section("ENTITY CLASSES")

    emp = Employee(
        employee_number  = 99999,
        first_name       = "Test",
        last_name        = "User",
        email            = "test.user@company.com",
        department_id    = 1,
        job_role         = "Data Analyst",
        job_level        = 2,
        monthly_income   = 6000.0,
        gender           = "Other",
        marital_status   = "Single",
        age              = 30,
    )
    print(f"  Employee  : {emp}")
    print(f"  Full name : {emp.full_name}")

    proj = Project(project_name="Test Project", department_id=1, status="Active")
    print(f"  Project   : {proj}  is_active={proj.is_active()}")

    rev = Review(employee_id=99999, performance_rating=4)
    print(f"  Review    : {rev}  high_performer={rev.is_high_performer()}")


def test_db_connection():
    """Confirm Singleton pattern and basic connectivity."""
    section("DATABASE CONNECTION (Singleton)")
    db1 = DatabaseConnection()
    db2 = DatabaseConnection()
    print(f"  Singleton check : db1 is db2 → {db1 is db2}")

    cfg = db1._config
    print(f"  Host     : {cfg['host']}")
    print(f"  User     : {cfg['user']}")
    print(f"  Database : {cfg['database']}")

    try:
        conn = db1.get_connection()
        conn.close()
        print("  Connection : ✅ OK")
    except Exception as e:
        print(f"  Connection : ❌ FAILED — {e}")
        return False

    return True


def test_oltp_tables():
    """Read row counts from OLTP tables."""
    section("OLTP TABLE ROW COUNTS")
    db = DatabaseConnection()
    oltp_tables = [
        "staging_employees",
        "departments",
        "job_roles",
        "employees",
        "employee_job_history",
        "reviews",
        "projects",
        "assignments",
    ]
    for tbl in oltp_tables:
        try:
            rows = db.execute_read(f"SELECT COUNT(*) AS cnt FROM {tbl}")
            count = rows[0]["cnt"]
            status = "✅" if count > 0 else "⚠️ empty"
            print(f"  {tbl:<30} {count:>10,} rows   {status}")
        except Exception as e:
            print(f"  {tbl:<30} ❌ {e}")


def test_olap_tables():
    """Read row counts from OLAP / Star Schema tables."""
    section("OLAP STAR SCHEMA ROW COUNTS")
    db = DatabaseConnection()
    olap_tables = [
        "dim_date",
        "dim_department",
        "dim_project",
        "dim_employee",
        "fact_performance_reviews",
    ]
    for tbl in olap_tables:
        try:
            rows = db.execute_read(f"SELECT COUNT(*) AS cnt FROM {tbl}")
            count = rows[0]["cnt"]
            status = "✅" if count > 0 else "⚠️ empty — run ETL"
            print(f"  {tbl:<30} {count:>10,} rows   {status}")
        except Exception as e:
            print(f"  {tbl:<30} ❌ {e}")


def main():
    print("\n" + "═" * 60)
    print("  ENTERPRISE HR ANALYTICS — SMOKE TEST")
    print(f"  Database : employee_analytics_dw2")
    print("═" * 60)

    try:
        test_entities()

        connected = test_db_connection()
        if not connected:
            print("\n❌ Cannot reach MySQL — fix credentials in .env and retry.")
            return 1

        test_oltp_tables()
        test_olap_tables()

        section("RESULT")
        print("  ✅ All checks completed.")
        print("\n  To launch the web application run:")
        print("    streamlit run app/streamlit_app.py\n")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
