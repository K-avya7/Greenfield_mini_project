import os
import random
from datetime import datetime

import numpy as np
import pandas as pd
from faker import Faker


class HRDataSynthesizer:
    """High-performance HR data synthesizer.

    Purpose:
        1. Scale the IBM HR dataset to 100K+ employees.
        2. Generate unique employee identities using Faker.
        3. Generate SCD Type 2 historical records.
        4. Export the result as a staging CSV.

    Designed for data-engineering / data-warehouse projects.
    """

    def __init__(
        self,
        source_file,
        output_file="data/synthesized_employees_staging.csv",
        target_employees=100_000,
        history_pct=0.30,
        seed=42,
    ):
        self.source_file = source_file
        self.output_file = output_file
        self.target_employees = target_employees
        self.history_pct = history_pct
        self.seed = seed

        # Pandas nanosecond resolution limit is 2262-04-11, so 2099-12-31 is safe.
        self.CURRENT_END_DATE = pd.Timestamp("2099-12-31")

        # Reproducibility
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

        self.fake = Faker()

    # =========================================================
    # 1. LOAD SOURCE DATA
    # =========================================================

    def load_source_data(self):
        """Load the original IBM HR dataset."""
        print("Loading source dataset...")
        df = pd.read_csv(self.source_file)
        print(f"Source rows: {len(df):,}")
        return df

    # =========================================================
    # 2. SCALE DATASET
    # =========================================================

    def scale_dataset(self, source_df):
        """Scale the original dataset to the requested size.

        Uses numpy sampling instead of repeatedly appending DataFrames.
        """
        print(f"Scaling dataset to {self.target_employees:,} employees...")
        source_size = len(source_df)

        # Randomly sample source rows with replacement.
        indices = np.random.randint(
            0,
            source_size,
            size=self.target_employees,
        )

        df = source_df.iloc[indices].reset_index(drop=True).copy()

        # Generate unique employee IDs.
        df["employee_id"] = np.arange(
            10001,
            10001 + self.target_employees,
            dtype=np.int64,
        )
        return df

    # =========================================================
    # 3. GENERATE IDENTITIES
    # =========================================================

    def generate_identities(self, df):
        """Generate realistic names and unique email addresses.

        Faker is only used for attributes that actually benefit from synthetic
        generation.
        """
        print("Generating employee identities...")
        genders = df["Gender"].to_numpy()

        first_names = [
            (
                self.fake.first_name_male()
                if gender == "Male"
                else (
                    self.fake.first_name_female()
                    if gender == "Female"
                    else self.fake.first_name()
                )
            )
            for gender in genders
        ]

        last_names = [self.fake.last_name() for _ in range(len(df))]

        df["first_name"] = first_names
        df["last_name"] = last_names

        df["email"] = (
            df["first_name"].str.lower()
            + "."
            + df["last_name"].str.lower()
            + df["employee_id"].astype(str)
            + "@company.com"
        )
        return df

    # =========================================================
    # 4. STANDARDIZE HR ATTRIBUTES
    # =========================================================

    def prepare_attributes(self, df):
        """Create/standardize attributes required for the warehouse dataset."""
        print("Preparing HR attributes...")

        # -----------------------------------------------------
        # Rename IBM columns (Added Manager & Years columns)
        # -----------------------------------------------------
        rename_map = {
            "Age": "age",
            "Gender": "gender",
            "MaritalStatus": "marital_status",
            "Department": "department",
            "JobRole": "job_role",
            "JobLevel": "job_level",
            "EducationField": "education_field",
            "MonthlyIncome": "monthly_income",
            "DailyRate": "daily_rate",
            "HourlyRate": "hourly_rate",
            "BusinessTravel": "business_travel",
            "DistanceFromHome": "distance_from_home",
            "PerformanceRating": "performance_rating",
            "Attrition": "attrition",
            "YearsWithCurrManager": "years_with_curr_manager",
            "YearsSinceLastPromotion": "years_since_last_promotion",
            "YearsAtCompany": "years_at_company"
        }

        df = df.rename(columns=rename_map)

        # Drop useless static columns to clean the warehouse data
        cols_to_drop = ["EmployeeCount", "StandardHours", "Over18"]
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")

        # Recalculate daily_rate & hourly_rate
        df["daily_rate"] = (df["monthly_income"] / 21.66).astype(int)
        df["hourly_rate"] = (df["daily_rate"] / 8).astype(int)

        # -----------------------------------------------------
        # Assign Initial Manager IDs
        # -----------------------------------------------------
        valid_ids = df["employee_id"].to_numpy()
        df["manager_id"] = np.random.choice(valid_ids, size=len(df))
        
        # Prevent employees from being their own manager
        self_managed = df["manager_id"] == df["employee_id"]
        df.loc[self_managed, "manager_id"] = np.random.choice(valid_ids)

        # -----------------------------------------------------
        # Generate hire dates
        # -----------------------------------------------------
        start_timestamp = np.datetime64("2015-01-01")
        end_timestamp = np.datetime64("2024-01-01")

        total_days = ((end_timestamp - start_timestamp).astype("timedelta64[D]").astype(int))
        random_days = np.random.randint(0, total_days + 1, size=len(df))

        df["effective_start_date"] = pd.Timestamp("2015-01-01") + pd.to_timedelta(random_days, unit="D")

        # -----------------------------------------------------
        # SCD current record
        # -----------------------------------------------------
        df["effective_end_date"] = self.CURRENT_END_DATE
        df["is_current"] = 1
        df["change_reason"] = "Initial Onboarding"

        return df

    # =========================================================
    # 5. GENERATE SCD TYPE 2 HISTORY
    # =========================================================

# =========================================================
    # 5. GENERATE SCD TYPE 2 HISTORY
    # =========================================================

    def generate_scd2(self, df):
        """Generate one historical version for a subset of employees."""
        print("Generating SCD Type 2 history...")

        employee_count = len(df)
        history_count = int(employee_count * self.history_pct)

        # -----------------------------------------------------
        # Select employees for historical changes
        # -----------------------------------------------------
        historical_indices = np.random.choice(
            employee_count, size=history_count, replace=False
        )
        historical_indices.sort()

        original = df.iloc[historical_indices].copy()
        historical = original.copy()

        # -----------------------------------------------------
        # Generate change dates
        # -----------------------------------------------------
        hire_dates = historical["effective_start_date"]

        min_change_dates = hire_dates + pd.Timedelta(days=180)
        max_change_date = pd.Timestamp("2024-01-01")

        available_days = (max_change_date - min_change_dates).dt.days
        available_days = np.maximum(available_days.to_numpy(), 1)

        random_offsets = (
            np.random.random(history_count) * available_days
        ).astype(int)
        change_dates = min_change_dates + pd.to_timedelta(
            random_offsets, unit="D"
        )

        # -----------------------------------------------------
        # HISTORICAL VERSION (represents the PAST state)
        # -----------------------------------------------------
        historical["effective_end_date"] = change_dates.values
        historical["is_current"] = 0
        historical["change_reason"] = np.random.choice(
            [
                "Promotion",
                "Department Transfer",
                "Annual Compensation Review",
            ],
            size=history_count,
        )

        # -----------------------------------------------------
        # Apply actual historical changes
        # -----------------------------------------------------

        # 1. PROMOTION
        promotion_mask = historical["change_reason"] == "Promotion"
        historical.loc[promotion_mask, "job_level"] = np.maximum(
            1, historical.loc[promotion_mask, "job_level"].to_numpy() - 1
        )
        # Salary drops by 30% on historical demotion to keep income valid for lower level
        historical.loc[promotion_mask, "monthly_income"] = (
            historical.loc[promotion_mask, "monthly_income"] * 0.70
        ).astype(int)

        # 2. ANNUAL COMPENSATION REVIEW
        comp_mask = historical["change_reason"] == "Annual Compensation Review"
        historical.loc[comp_mask, "monthly_income"] = (
            historical.loc[comp_mask, "monthly_income"] * 0.92
        ).astype(int)

        # 3. DEPARTMENT TRANSFER
        transfer_mask = historical["change_reason"] == "Department Transfer"

        dept_role_mapping = {
            "Sales": [
                "Sales Executive",
                "Sales Representative",
                "Manager",
            ],
            "Research & Development": [
                "Research Scientist",
                "Laboratory Technician",
                "Manufacturing Director",
                "Healthcare Representative",
                "Research Director",
                "Manager",
            ],
            "Human Resources": ["Human Resources", "Manager"],
        }

        dept_rotation = {
            "Sales": "Research & Development",
            "Research & Development": "Human Resources",
            "Human Resources": "Sales",
        }

        # Rotate department
        new_depts = (
            historical.loc[transfer_mask, "department"]
            .map(dept_rotation)
            .fillna("Sales")
        )
        historical.loc[transfer_mask, "department"] = new_depts

        # Assign a valid role for the new department
        new_roles = [
            random.choice(dept_role_mapping[dept]) for dept in new_depts
        ]
        historical.loc[transfer_mask, "job_role"] = new_roles

        historical.loc[transfer_mask, "monthly_income"] = (
            historical.loc[transfer_mask, "monthly_income"] * 0.95
        ).astype(int)

        # Recalculate daily/hourly rates for all historical rows
        historical["daily_rate"] = (
            historical["monthly_income"] / 21.66
        ).astype(int)
        historical["hourly_rate"] = (historical["daily_rate"] / 8).astype(int)

        # -----------------------------------------------------
        # 4. MANAGER CHANGES (Ensuring realistic hierarchy history)
        # -----------------------------------------------------
        current_year = 2024
        years_since_change = current_year - historical["effective_end_date"].dt.year
        
        # A manager change must have happened if they transferred departments OR 
        # if the years with their current manager is shorter than the time elapsed since this record ended.
        manager_changed_mask = transfer_mask | (historical["years_with_curr_manager"] < years_since_change)
        
        # Assign a different historical manager from the valid employee pool
        valid_ids = df["employee_id"].to_numpy()
        historical.loc[manager_changed_mask, "manager_id"] = np.random.choice(
            valid_ids, size=manager_changed_mask.sum()
        )

        # -----------------------------------------------------
        # CURRENT VERSION
        # -----------------------------------------------------
        current_updates = original.copy()
        current_updates["effective_start_date"] = change_dates.values
        current_updates["effective_end_date"] = self.CURRENT_END_DATE
        current_updates["is_current"] = 1
        current_updates["change_reason"] = "Role & Compensation Update"

        # -----------------------------------------------------
        # Combine & Sort
        # -----------------------------------------------------
        base_remaining = df.drop(index=df.index[historical_indices])

        final_df = pd.concat(
            [base_remaining, historical, current_updates],
            ignore_index=True,
        )

        final_df = final_df.sort_values(
            ["employee_id", "effective_start_date"], kind="mergesort"
        ).reset_index(drop=True)

        return final_df
    # =========================================================
    # 6. ADD SURROGATE KEY
    # =========================================================

    def add_surrogate_key(self, df):
        """Generate a warehouse surrogate key for every employee-version record."""
        df.insert(
            0,
            "employee_sk",
            np.arange(1, len(df) + 1, dtype=np.int64),
        )
        return df

    # =========================================================
    # 7. VALIDATE
    # =========================================================

    def validate(self, df):
        """Run basic SCD Type 2 data-quality checks."""
        print("\nRunning validation...")

        unique_employees = df["employee_id"].nunique()
        current_employees = df.loc[
            df["is_current"] == 1, "employee_id"
        ].nunique()

        assert (
            unique_employees == self.target_employees
        ), "Employee count mismatch"
        assert (
            current_employees == self.target_employees
        ), "Every employee must have exactly one current record"

        assert df["employee_sk"].is_unique, "Duplicate surrogate keys"

        current = df[df["is_current"] == 1]
        assert (current["effective_end_date"] == self.CURRENT_END_DATE).all()

        historical = df[df["is_current"] == 0]
        assert (
            historical["effective_start_date"] < historical["effective_end_date"]
        ).all()

        print("✓ Employee count valid")
        print("✓ Exactly one current record per employee")
        print("✓ Surrogate keys unique")
        print("✓ Current records valid")
        print("✓ Historical date ranges valid")

# =========================================================
    # 8. EXPORT
    # =========================================================

    def save(self, df):
        """Write final dataset to CSV, strictly ordering and filtering columns."""
        output_dir = os.path.dirname(self.output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # Define the exact columns matching the MySQL staging_employees table
        final_cols = [
            "employee_sk", "employee_id", "first_name", "last_name", "email", 
            "age", "gender", "marital_status", "department", "job_role", 
            "job_level", "education_field", "monthly_income", "daily_rate", 
            "hourly_rate", "business_travel", "distance_from_home", 
            "performance_rating", "attrition", "effective_start_date", 
            "effective_end_date", "is_current", "change_reason", 
            "years_with_curr_manager", "years_since_last_promotion", 
            "years_at_company", "manager_id"
        ]
        
        # Filter the DataFrame to ONLY include these columns in this exact order
        df_export = df[final_cols]
        
        df_export.to_csv(self.output_file, index=False)
        print(f"\nSaved clean dataset to: {self.output_file}")
    
    def run(self):
        """Execute complete synthesis pipeline."""
        start_time = datetime.now()

        print("=" * 60)
        print("HR DATA SYNTHESIS PIPELINE")
        print("=" * 60)

        source_df = self.load_source_data()
        df = self.scale_dataset(source_df)
        df = self.generate_identities(df)
        df = self.prepare_attributes(df)
        print(f"Base employees: {len(df):,}")

        df = self.generate_scd2(df)
        df = self.add_surrogate_key(df)
        self.validate(df)
        self.save(df)

        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("GENERATION COMPLETE")
        print("=" * 60)
        print(f"Unique employees: {df['employee_id'].nunique():,}")
        print(f"Total SCD records: {len(df):,}")
        print(f"Historical records: {(df['is_current'] == 0).sum():,}")
        print(f"Current records: {(df['is_current'] == 1).sum():,}")
        print(f"Runtime: {elapsed:.2f} seconds")

        return df


if __name__ == "__main__":
    synthesizer = HRDataSynthesizer(
        source_file="data/WA_Fn-UseC_-HR-Employee-Attrition.csv",
        output_file="data/synthesized_employees_staging3.csv",
        target_employees=100_000,
        history_pct=0.30,
        seed=42,
    )
    synthesizer.run()