import pandas as pd
import numpy as np
from datetime import datetime

class DataValidator:
    """Automated Data Quality & Verification Suite for Synthesized HR Data."""

    VALID_DEPT_ROLES = {
        "Sales": ["Sales Executive", "Sales Representative", "Manager"],
        "Research & Development": [
            "Research Scientist", "Laboratory Technician", 
            "Manufacturing Director", "Healthcare Representative", 
            "Research Director", "Manager"
        ],
        "Human Resources": ["Human Resources", "Manager"]
    }

    def __init__(self, filepath="data/synthesized_employees_staging.csv"):
        print(f"Loading dataset from '{filepath}'...")
        self.df = pd.read_csv(filepath)
        self.df['effective_start_date'] = pd.to_datetime(self.df['effective_start_date'])
        # Replace warehouse infinity date for datetime comparisons
        self.df['effective_end_date_clean'] = pd.to_datetime(
            self.df['effective_end_date'].replace('9999-12-31', '2099-12-31')
        )
        self.passed_tests = 0
        self.failed_tests = 0

    def _log_result(self, test_name, passed, message=""):
        if passed:
            self.passed_tests += 1
            print(f"✅ PASS: [{test_name}] {message}")
        else:
            self.failed_tests += 1
            print(f"❌ FAIL: [{test_name}] {message}")

    def test_volume_and_nulls(self):
        """1. Verify row volume exceeds 100,000 and zero critical NULL values exist."""
        total_rows = len(self.df)
        has_min_volume = total_rows >= 100000
        null_count = self.df[['employee_id', 'monthly_income', 'department', 'is_current']].isnull().sum().sum()
        
        passed = has_min_volume and (null_count == 0)
        self._log_result(
            "Volume & Mandatory Null Check", 
            passed, 
            f"Total Rows: {total_rows:,} | Null Critical Values: {null_count}"
        )

    def test_single_active_record_per_employee(self):
        """2. SCD Type 2 Constraint: Every employee MUST have EXACTLY ONE active record (is_current=1)."""
        active_counts = self.df[self.df['is_current'] == 1].groupby('employee_id').size()
        invalid_employees = active_counts[active_counts != 1]
        
        passed = len(invalid_employees) == 0
        self._log_result(
            "SCD2 Single Active Record Check", 
            passed, 
            f"Employees violating single active state: {len(invalid_employees)}"
        )

    def test_timeline_integrity(self):
        """3. Ensure effective_start_date is strictly earlier than effective_end_date."""
        invalid_dates = self.df[self.df['effective_start_date'] >= self.df['effective_end_date_clean']]
        passed = len(invalid_dates) == 0
        self._log_result(
            "SCD2 Date Sequence Check", 
            passed, 
            f"Records with start_date >= end_date: {len(invalid_dates)}"
        )

    def test_timeline_overlaps(self):
        """4. SCD Type 2 Constraint: An employee's historical records must not overlap in time."""
        # Sort by employee and start date
        sorted_df = self.df.sort_values(['employee_id', 'effective_start_date'])
        # Shift the previous record's end date to compare with current record's start date
        sorted_df['prev_end_date'] = sorted_df.groupby('employee_id')['effective_end_date_clean'].shift(1)
        
        # Overlap occurs if start_date < prev_end_date
        overlaps = sorted_df[sorted_df['effective_start_date'] < sorted_df['prev_end_date']]
        passed = len(overlaps) == 0
        self._log_result(
            "SCD2 Timeline Overlap Check", 
            passed, 
            f"Overlapping historical records found: {len(overlaps)}"
        )

    def test_department_role_alignment(self):
        """5. Ensure job roles logically align with their assigned department."""
        mismatches = 0
        for dept, roles in self.VALID_DEPT_ROLES.items():
            dept_mask = self.df['department'] == dept
            invalid_roles = ~self.df[dept_mask]['job_role'].isin(roles)
            mismatches += invalid_roles.sum()
            
        passed = mismatches == 0
        self._log_result(
            "Domain Dept/Role Mapping Check", 
            passed, 
            f"Mismatched Job Role & Dept pairings: {mismatches}"
        )

    def test_salary_sanity_by_job_level(self):
        """6. Check for salary outliers relative to Job Levels."""
        # Define reasonable upper/lower limits per Job Level
        level_bounds = {
            1: (1500, 5000),
            2: (3500, 8500),
            3: (6000, 14000),
            4: (10000, 18000),
            5: (14000, 25000)
        }
        anomalies = 0
        for lvl, (low, high) in level_bounds.items():
            outliers = self.df[(self.df['job_level'] == lvl) & 
                               ((self.df['monthly_income'] < low) | (self.df['monthly_income'] > high))]
            anomalies += len(outliers)
            
        passed = anomalies == 0
        self._log_result(
            "Salary Range Sanity Check", 
            passed, 
            f"Out-of-bound salaries for job levels: {anomalies}"
        )

    def test_daily_rate_formula_consistency(self):
        """7. Verify DailyRate is mathematically consistent with MonthlyIncome (~21.66 workdays)."""
        expected_daily = self.df['monthly_income'] / 21.66
        # Allow a tolerance margin of ±$30 due to random variance added in generation
        diff = (self.df['daily_rate'] - expected_daily).abs()
        inconsistent = (diff > 30).sum()
        
        passed = inconsistent == 0
        self._log_result(
            "Financial Ratio Consistency Check", 
            passed, 
            f"Daily Rate vs Monthly Income mismatches: {inconsistent}"
        )

    def test_scd2_promotion_logic(self):
        """8. Ensure historical records (is_current=0) show lower/equal salary than current ones (is_current=1)."""
        grouped = self.df.groupby('employee_id')
        multi_record_emps = grouped.filter(lambda x: len(x) > 1)
        
        # Sort chronologically
        sorted_multi = multi_record_emps.sort_values(['employee_id', 'effective_start_date'])
        
        # Check if income decreases over time without a change reason justifying it
        sorted_multi['income_diff'] = sorted_multi.groupby('employee_id')['monthly_income'].diff()
        unexplained_drops = sorted_multi[sorted_multi['income_diff'] < -5000] # Unexpected huge salary drops
        
        passed = len(unexplained_drops) == 0
        self._log_result(
            "SCD2 Salary Progression Check", 
            passed, 
            f"Unexplained drastic salary drops in history: {len(unexplained_drops)}"
        )

    def test_attrition_ratio(self):
        """9. Verify Attrition rate stays within expected bounds (14% to 18%)."""
        current_employees = self.df[self.df['is_current'] == 1]
        attrition_rate = (current_employees['attrition'] == 'Yes').mean() * 100
        
        passed = 14.0 <= attrition_rate <= 18.0
        self._log_result(
            "Statistical Distribution Check", 
            passed, 
            f"Calculated Attrition Rate: {attrition_rate:.2f}% (Expected: 14%-18%)"
        )

    def run_all_tests(self):
        print("\n=== STARTING DATA QUALITY & INTEGRITY VALIDATION ===")
        self.test_volume_and_nulls()
        self.test_single_active_record_per_employee()
        self.test_timeline_integrity()
        self.test_timeline_overlaps()
        self.test_department_role_alignment()
        self.test_salary_sanity_by_job_level()
        self.test_daily_rate_formula_consistency()
        self.test_scd2_promotion_logic()
        self.test_attrition_ratio()
        print("=====================================================")
        print(f"SUMMARY: {self.passed_tests} PASSED | {self.failed_tests} FAILED\n")

if __name__ == "__main__":
    validator = DataValidator("data/synthesized_employees_staging3.csv")
    validator.run_all_tests()