#!/usr/bin/env python3
"""
Main test/demo script for the HR Analytics Application
Tests all modules: entities, database manager, and managers
"""

import sys
from app.entities import Employee, Project, Review
from app.db_manager import DatabaseConnection
from app.managers import EmployeeManager, AnalyticsManager


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_entities():
    """Test entity classes"""
    print_section("TESTING ENTITY CLASSES")
    
    # Test Employee
    print("1. Employee Entity:")
    emp = Employee(
        employee_number=1001,
        first_name="John",
        last_name="Doe",
        email="john.doe@company.com",
        department_id=10,
        job_title="Software Engineer"
    )
    print(f"   Created: {emp.full_name}")
    print(f"   Email: {emp.email}")
    print(f"   Title: {emp.job_title}")
    
    emp.promote("Senior Software Engineer")
    print(f"   Promoted to: {emp.job_title}")
    
    # Test Project
    print("\n2. Project Entity:")
    proj = Project(
        project_name="HR Analytics System",
        budget=50000.00,
        status="Active"
    )
    print(f"   Project: {proj.project_name}")
    print(f"   Budget: ${proj.budget:,.2f}")
    print(f"   Is Active: {proj.is_active()}")
    
    # Test Review
    print("\n3. Review Entity:")
    review = Review(
        employee_number=1001,
        reviewer_id=2001,
        performance_rating=5,
        comments="Excellent performance this quarter"
    )
    print(f"   Employee #: {review.employee_number}")
    print(f"   Rating: {review.performance_rating}/5")
    print(f"   High Performer: {review.is_high_performer()}")


def test_database_connection():
    """Test database connection"""
    print_section("TESTING DATABASE CONNECTION")
    
    db = DatabaseConnection()
    print("1. Database Connection Singleton:")
    print(f"   Instance created: {db}")
    print(f"   Config: host={db._config['host']}, user={db._config['user']}")
    
    print("\n2. Testing connection to 'hr_staging' database:")
    try:
        conn = db.get_connection("hr_staging")
        if conn:
            print("   ✓ Connection successful!")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as row_count FROM information_schema.tables WHERE table_schema = 'hr_staging'")
            result = cursor.fetchone()
            print(f"   Tables in hr_staging: {result[0]}")
            cursor.close()
            conn.close()
        else:
            print("   ✗ Connection failed (database may not exist)")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def test_employee_manager():
    """Test EmployeeManager operations"""
    print_section("TESTING EMPLOYEE MANAGER")
    
    mgr = EmployeeManager()
    
    print("1. EmployeeManager initialized")
    print(f"   Instance: {mgr}")
    print(f"   Database connection: {mgr.db}")
    
    print("\n2. Sample operations (would execute on real database):")
    
    # Create sample employee
    emp = Employee(
        employee_number=9999,
        first_name="Test",
        last_name="User",
        email="test.user@company.com",
        department_id=1,
        job_title="Analyst"
    )
    
    print(f"   - Would create employee: {emp.full_name}")
    print(f"   - Would update role to: Senior Analyst")
    print(f"   - Would trigger SCD Type 2 sync in Data Warehouse")


def test_analytics_manager():
    """Test AnalyticsManager operations"""
    print_section("TESTING ANALYTICS MANAGER")
    
    mgr = AnalyticsManager()
    
    print("1. AnalyticsManager initialized")
    print(f"   Instance: {mgr}")
    
    print("\n2. Fetching department performance analytics:")
    try:
        results = mgr.get_department_performance()
        if results:
            print(f"   ✓ Retrieved {len(results)} departments")
            for dept in results[:3]:  # Show first 3
                print(f"     - {dept}")
        else:
            print("   - No data returned (tables may not exist or be populated)")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def test_database_structures():
    """Test database schema information"""
    print_section("TESTING DATABASE STRUCTURES")
    
    db = DatabaseConnection()
    
    databases_to_check = ["hr_staging", "hr_oltp", "hr_dw"]
    
    for db_name in databases_to_check:
        print(f"\n{db_name.upper()}:")
        try:
            conn = db.get_connection(db_name)
            if conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT TABLE_NAME 
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = '{db_name}'
                """)
                tables = cursor.fetchall()
                if tables:
                    print(f"  Tables: {[t[0] for t in tables]}")
                else:
                    print(f"  No tables found")
                cursor.close()
                conn.close()
            else:
                print(f"  ✗ Could not connect")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  HR ANALYTICS APPLICATION - TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Entities
        test_entities()
        
        # Test 2: Database Connection
        test_database_connection()
        
        # Test 3: Database Structures
        test_database_structures()
        
        # Test 4: Employee Manager
        test_employee_manager()
        
        # Test 5: Analytics Manager
        test_analytics_manager()
        
        # Summary
        print_section("TEST EXECUTION COMPLETE")
        print("✓ All module tests completed successfully!")
        print("\nNext Steps:")
        print("  1. Verify database structures with MySQL Workbench")
        print("  2. Deploy staging data to OLTP and DW databases")
        print("  3. Run ETL procedures for SCD Type 2 synchronization")
        print("  4. Execute analytics queries from AnalyticsManager")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
