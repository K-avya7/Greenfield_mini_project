"""
Employee Analytics Data Synthesizer
----------------------------------
Preserves all 35 IBM HR columns, scales to 100,000 current employees,
and creates one SCD Type 2 historical version for 30% of employees.

Output: employee_scd2_130k.csv
Expected:
    100,000 current records
     30,000 historical records
    130,000 total records
     44 columns
"""

from pathlib import Path
import random

import numpy as np
import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("C:\\Users\\KavyaAgrawal\\Desktop\\greenfield mini porject\\data\\WA_Fn-UseC_-HR-Employee-Attrition.csv")
OUTPUT_FILE = Path("employee_scd2_130k.csv")

TARGET_CURRENT_EMPLOYEES = 100_000
HISTORY_PERCENTAGE = 0.30
RANDOM_SEED = 42

CURRENT_START_DATE = pd.Timestamp("2026-01-01")
OPEN_END_DATE = pd.Timestamp("9999-12-31")

MIN_HISTORY_MONTHS = 12
MAX_HISTORY_MONTHS = 36

HISTORY_EMPLOYEE_COUNT = int(
    TARGET_CURRENT_EMPLOYEES * HISTORY_PERCENTAGE
)


# ============================================================
# ORIGINAL IBM COLUMNS
# ============================================================

ORIGINAL_COLUMNS = [
    "Age",
    "Attrition",
    "BusinessTravel",
    "DailyRate",
    "Department",
    "DistanceFromHome",
    "Education",
    "EducationField",
    "EmployeeCount",
    "EmployeeNumber",
    "EnvironmentSatisfaction",
    "Gender",
    "HourlyRate",
    "JobInvolvement",
    "JobLevel",
    "JobRole",
    "JobSatisfaction",
    "MaritalStatus",
    "MonthlyIncome",
    "MonthlyRate",
    "NumCompaniesWorked",
    "Over18",
    "OverTime",
    "PercentSalaryHike",
    "PerformanceRating",
    "RelationshipSatisfaction",
    "StandardHours",
    "StockOptionLevel",
    "TotalWorkingYears",
    "TrainingTimesLastYear",
    "WorkLifeBalance",
    "YearsAtCompany",
    "YearsInCurrentRole",
    "YearsSinceLastPromotion",
    "YearsWithCurrManager",
]

ADDED_COLUMNS = [
    "EmployeeName",
    "Email",
    "employee_id",
    "employee_sk",
    "effective_start_date",
    "effective_end_date",
    "is_current",
    "change_reason",
]

FINAL_COLUMNS = ORIGINAL_COLUMNS + ADDED_COLUMNS


# ============================================================
# HELPERS
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fix the common IBM dataset typo without changing the schema."""
    if "YearsWithCurrManaer" in df.columns:
        df = df.rename(
            columns={
                "YearsWithCurrManaer": "YearsWithCurrManager"
            }
        )
    return df


def validate_source(df: pd.DataFrame) -> None:
    missing = [
        c for c in ORIGINAL_COLUMNS
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required IBM columns:\n"
            + "\n".join(missing)
        )


def clean_source(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].astype(str).str.strip()

    return df


def scale_to_target(
    base: pd.DataFrame,
    target: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Preserve the original rows and sample complete employee profiles
    to create additional employees. Complete-row sampling keeps
    correlations between IBM attributes.
    """
    base = base.reset_index(drop=True).copy()

    if len(base) >= target:
        return base.iloc[:target].copy()

    additional_count = target - len(base)

    sample_indices = rng.integers(
        0,
        len(base),
        size=additional_count,
    )

    additional = base.iloc[sample_indices].copy()
    additional.reset_index(drop=True, inplace=True)

    max_employee_number = int(
        pd.to_numeric(
            base["EmployeeNumber"],
            errors="raise",
        ).max()
    )

    additional["EmployeeNumber"] = np.arange(
        max_employee_number + 1,
        max_employee_number + additional_count + 1,
        dtype=np.int64,
    )

    return pd.concat(
        [base, additional],
        ignore_index=True,
    )


def add_small_variation(
    df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Prevent exact profile duplication while retaining realistic
    distributions from the IBM source.
    """
    df = df.copy()
    n = len(df)

    df["Age"] = (
        pd.to_numeric(df["Age"], errors="coerce")
        .fillna(35)
        .astype(int)
        + rng.choice([-2, -1, 0, 0, 0, 1, 2], n)
    ).clip(18, 65)

    df["DailyRate"] = (
        pd.to_numeric(df["DailyRate"], errors="coerce")
        .fillna(800)
        * rng.uniform(0.90, 1.10, n)
    ).round().astype(int)

    df["HourlyRate"] = (
        pd.to_numeric(df["HourlyRate"], errors="coerce")
        .fillna(60)
        * rng.uniform(0.92, 1.08, n)
    ).round().clip(30, 100).astype(int)

    df["MonthlyRate"] = (
        pd.to_numeric(df["MonthlyRate"], errors="coerce")
        .fillna(15000)
        * rng.uniform(0.92, 1.08, n)
    ).round().astype(int)

    df["MonthlyIncome"] = (
        pd.to_numeric(df["MonthlyIncome"], errors="coerce")
        .fillna(5000)
        * rng.uniform(0.92, 1.08, n)
    ).round().astype(int)

    df["DistanceFromHome"] = (
        pd.to_numeric(df["DistanceFromHome"], errors="coerce")
        .fillna(5)
        .astype(int)
        + rng.choice([-2, -1, 0, 0, 1, 2], n)
    ).clip(1, 50)

    df["TrainingTimesLastYear"] = (
        pd.to_numeric(df["TrainingTimesLastYear"], errors="coerce")
        .fillna(3)
        .astype(int)
        + rng.choice([-1, 0, 0, 0, 1], n)
    ).clip(0, 10)

    return df


def add_identity_fields(
    df: pd.DataFrame,
    fake: Faker,
) -> pd.DataFrame:
    df = df.copy()

    # Stable employee/business identifier.
    df["employee_id"] = (
        pd.to_numeric(
            df["EmployeeNumber"],
            errors="raise",
        ).astype(int)
    )

    names = []
    emails = []
    used_emails = set()

    for employee_id in df["employee_id"]:
        first = fake.first_name()
        last = fake.last_name()

        name = f"{first} {last}"
        email = (
            f"{first}.{last}.{employee_id}@example.com"
        ).lower()

        suffix = 1
        original_email = email

        while email in used_emails:
            email = (
                original_email.replace(
                    "@example.com",
                    f".{suffix}@example.com",
                )
            )
            suffix += 1

        used_emails.add(email)

        names.append(name)
        emails.append(email)

    df["EmployeeName"] = names
    df["Email"] = emails

    return df


# ============================================================
# SCD2 CHANGE FUNCTIONS
# ============================================================

def salary_revision(
    row: pd.Series,
    rng: np.random.Generator,
) -> pd.Series:
    row = row.copy()

    income = int(row["MonthlyIncome"])

    row["MonthlyIncome"] = income + max(
        int(round(income * rng.uniform(0.05, 0.15))),
        100,
    )

    row["PercentSalaryHike"] = int(
        rng.integers(5, 16)
    )

    row["change_reason"] = "Salary Revision"

    return row


def department_transfer(
    row: pd.Series,
    departments: list[str],
    rng: np.random.Generator,
) -> pd.Series:
    row = row.copy()

    alternatives = [
        d for d in departments
        if d != row["Department"]
    ]

    if alternatives:
        row["Department"] = rng.choice(alternatives)

    row["change_reason"] = "Department Transfer"

    return row


def promotion(
    row: pd.Series,
    rng: np.random.Generator,
) -> pd.Series:
    row = row.copy()

    current_level = int(row["JobLevel"])
    new_level = min(current_level + 1, 5)

    row["JobLevel"] = new_level

    income = int(row["MonthlyIncome"])

    row["MonthlyIncome"] = income + max(
        int(round(income * rng.uniform(0.08, 0.20))),
        500,
    )

    row["PercentSalaryHike"] = int(
        rng.integers(8, 21)
    )

    row["YearsInCurrentRole"] = 0
    row["YearsSinceLastPromotion"] = 0
    row["change_reason"] = "Promotion"

    return row


def role_change(
    row: pd.Series,
    job_roles: list[str],
    rng: np.random.Generator,
) -> pd.Series:
    row = row.copy()

    alternatives = [
        r for r in job_roles
        if r != row["JobRole"]
    ]

    if alternatives:
        row["JobRole"] = rng.choice(alternatives)

    row["JobLevel"] = min(
        int(row["JobLevel"])
        + int(rng.choice([0, 1])),
        5,
    )

    row["MonthlyIncome"] = int(
        round(
            float(row["MonthlyIncome"])
            * rng.uniform(1.05, 1.18)
        )
    )

    row["YearsInCurrentRole"] = 0
    row["change_reason"] = "Role Change"

    return row


def apply_history_change(
    row: pd.Series,
    departments: list[str],
    job_roles: list[str],
    rng: np.random.Generator,
) -> pd.Series:
    """
    Change distribution:
        Promotion             40%
        Salary Revision       25%
        Department Transfer   20%
        Role Change           15%
    """
    change = rng.choice(
        [
            "Promotion",
            "Salary Revision",
            "Department Transfer",
            "Role Change",
        ],
        p=[0.40, 0.25, 0.20, 0.15],
    )

    if change == "Promotion":
        return promotion(row, rng)

    if change == "Salary Revision":
        return salary_revision(row, rng)

    if change == "Department Transfer":
        return department_transfer(
            row,
            departments,
            rng,
        )

    return role_change(
        row,
        job_roles,
        rng,
    )


def create_scd2(
    current_df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Creates exactly one historical version for 30% of employees.
    """
    current_df = current_df.copy()

    employee_ids = (
        current_df["employee_id"]
        .astype(int)
        .to_numpy()
    )

    history_count = int(
        round(
            len(current_df) * HISTORY_PERCENTAGE
        )
    )

    selected_ids = rng.choice(
        employee_ids,
        size=history_count,
        replace=False,
    )

    departments = sorted(
        current_df["Department"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    job_roles = sorted(
        current_df["JobRole"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    # Current records.
    current = current_df.copy()
    current["effective_start_date"] = CURRENT_START_DATE
    current["effective_end_date"] = OPEN_END_DATE
    current["is_current"] = 1
    current["change_reason"] = "Current Record"

    # Historical records.
    indexed = current_df.set_index(
        "employee_id",
        drop=False,
    )

    history_rows = []

    for employee_id in selected_ids:
        historical = indexed.loc[employee_id].copy()

        historical = apply_history_change(
            historical,
            departments,
            job_roles,
            rng,
        )

        months_back = int(
            rng.integers(
                MIN_HISTORY_MONTHS,
                MAX_HISTORY_MONTHS + 1,
            )
        )

        start_date = (
            CURRENT_START_DATE
            - pd.DateOffset(months=months_back)
        )

        historical["effective_start_date"] = start_date

        historical["effective_end_date"] = (
            CURRENT_START_DATE
            - pd.Timedelta(days=1)
        )

        historical["is_current"] = 0

        history_rows.append(historical)

    history = pd.DataFrame(history_rows)

    return pd.concat(
        [history, current],
        ignore_index=True,
    )


def assign_employee_sk(
    df: pd.DataFrame,
) -> pd.DataFrame:
    df = df.copy()

    # Unique version/record identifier.
    df["employee_sk"] = np.arange(
        1,
        len(df) + 1,
        dtype=np.int64,
    )

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_final(
    df: pd.DataFrame,
) -> None:
    if list(df.columns) != FINAL_COLUMNS:
        raise ValueError(
            "Final columns do not match expected schema."
        )

    expected_total = (
        TARGET_CURRENT_EMPLOYEES
        + HISTORY_EMPLOYEE_COUNT
    )

    if len(df) != expected_total:
        raise ValueError(
            f"Expected {expected_total:,} rows; "
            f"got {len(df):,}."
        )

    if df["employee_id"].nunique() != TARGET_CURRENT_EMPLOYEES:
        raise ValueError(
            "Unexpected number of unique employee_id values."
        )

    if df["employee_sk"].nunique() != len(df):
        raise ValueError(
            "employee_sk is not unique."
        )

    current = (
        df["is_current"] == 1
    ).sum()

    historical = (
        df["is_current"] == 0
    ).sum()

    if current != TARGET_CURRENT_EMPLOYEES:
        raise ValueError(
            "Incorrect number of current records."
        )

    if historical != HISTORY_EMPLOYEE_COUNT:
        raise ValueError(
            "Incorrect number of historical records."
        )

    versions = (
        df.groupby("employee_id")["is_current"]
        .sum()
    )

    if not (versions == 1).all():
        raise ValueError(
            "Every employee must have exactly one current version."
        )

    dates_start = pd.to_datetime(
        df["effective_start_date"]
    )

    dates_end = pd.to_datetime(
        df["effective_end_date"]
    )

    if (dates_start > dates_end).any():
        raise ValueError(
            "Invalid SCD2 date range detected."
        )

    current_end = df.loc[
        df["is_current"] == 1,
        "effective_end_date",
    ]

    if not (
        current_end == "9999-12-31"
    ).all():
        raise ValueError(
            "Current records must end on 9999-12-31."
        )

    historical_reason = df.loc[
        df["is_current"] == 0,
        "change_reason",
    ]

    if historical_reason.isna().any():
        raise ValueError(
            "Historical records must have a change_reason."
        )

    # Ensure unique email per active employee record
    if df.loc[df["is_current"] == 1, "Email"].duplicated().any():
        raise ValueError(
            "Email values must be unique among current employees."
        )
# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 70)
    print("IBM HR DATA SYNTHESIZER + SCD TYPE 2")
    print("=" * 70)

    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    fake = Faker()
    fake.seed_instance(RANDOM_SEED)

    # --------------------------------------------------------
    # 1. Read source
    # --------------------------------------------------------

    print("\n[1/7] Reading source CSV...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE.resolve()}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    print(
        f"Original rows: {len(df):,}"
    )

    # --------------------------------------------------------
    # 2. Validate source
    # --------------------------------------------------------

    print("[2/7] Validating source columns...")

    df = normalize_columns(df)

    validate_source(df)

    df = df[ORIGINAL_COLUMNS].copy()
    df = clean_source(df)

    # --------------------------------------------------------
    # 3. Scale
    # --------------------------------------------------------

    print(
        f"[3/7] Scaling to "
        f"{TARGET_CURRENT_EMPLOYEES:,} current employees..."
    )

    current = scale_to_target(
        df,
        TARGET_CURRENT_EMPLOYEES,
        rng,
    )

    current = add_small_variation(
        current,
        rng,
    )

    # --------------------------------------------------------
    # 4. Identity
    # --------------------------------------------------------

    print("[4/7] Generating identity fields...")

    current = add_identity_fields(
        current,
        fake,
    )

    # --------------------------------------------------------
    # 5. SCD2
    # --------------------------------------------------------

    print(
        f"[5/7] Creating SCD2 history for "
        f"{HISTORY_EMPLOYEE_COUNT:,} employees..."
    )

    final = create_scd2(
        current,
        rng,
    )

    # --------------------------------------------------------
    # 6. Surrogate keys + final schema
    # --------------------------------------------------------

    print("[6/7] Assigning employee_sk and finalizing schema...")

    final = assign_employee_sk(final)

    final = final[FINAL_COLUMNS]

    final = final.sort_values(
        [
            "employee_id",
            "effective_start_date",
        ],
        kind="stable",
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # 7. Validate + write
    # --------------------------------------------------------

    print("[7/7] Validating and writing output...")

    validate_final(final)

    final.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n" + "=" * 70)
    print("SYNTHESIS COMPLETE")
    print("=" * 70)

    print(
        f"Current employees : {TARGET_CURRENT_EMPLOYEES:,}"
    )
    print(
        f"Historical records: {HISTORY_EMPLOYEE_COUNT:,}"
    )
    print(
        f"Total rows        : {len(final):,}"
    )
    print(
        f"Unique employees  : {final['employee_id'].nunique():,}"
    )
    print(
        f"Unique employee_sk: {final['employee_sk'].nunique():,}"
    )
    print(
        f"Columns           : {len(final.columns)}"
    )
    print(
        f"Output file       : {OUTPUT_FILE.resolve()}"
    )

    print("\nSCD2 change distribution:")
    print(
        final.loc[
            final["is_current"] == 0,
            "change_reason",
        ].value_counts().to_string()
    )

    print("\nFinal columns:")
    for i, column in enumerate(final.columns, start=1):
        print(f"{i:02d}. {column}")


if __name__ == "__main__":
    main()
