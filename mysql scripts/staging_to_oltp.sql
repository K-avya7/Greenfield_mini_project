-- ============================================================
-- ENTERPRISE EMPLOYEE ANALYTICS & DATA WAREHOUSE
-- STAGING -> OLTP LOAD
--
-- Source:
--   employee_scd2_130k.csv
--
-- Expected source:
--   35 original IBM HR columns
--   + EmployeeName
--   + Email
--   + employee_id
--   + employee_sk
--   + effective_start_date
--   + effective_end_date
--   + is_current
--   + change_reason
--
-- Total: 44 columns
--
-- IMPORTANT:
--   1. This is a FRESH schema/load script.
--   2. No TRUNCATE statements are used.
--   3. No DROP TABLE statements are used.
--   4. Existing populated tables should NOT be reused with this script.
--   5. Run this in a new/empty employee_analytics_dw database.
--
-- SCD TYPE 2:
--   employee_id = stable employee/business identifier
--   employee_sk = unique source/version identifier
--   employee_job_history = all employee versions
--   employees = current employee state
--
-- Projects and assignments are NOT loaded from this CSV because
-- the IBM HR dataset contains no project information.
-- ============================================================


-- ============================================================
-- 1. DATABASE
-- ============================================================

CREATE DATABASE IF NOT EXISTS employee_analytics_dw2;

USE employee_analytics_dw2;


-- ============================================================
-- 2. STAGING TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS staging_employees (

    Age INT,
    Attrition VARCHAR(10),
    BusinessTravel VARCHAR(50),
    DailyRate INT,
    Department VARCHAR(100),
    DistanceFromHome INT,
    Education INT,
    EducationField VARCHAR(100),
    EmployeeCount INT,
    EmployeeNumber INT,
    EnvironmentSatisfaction INT,
    Gender VARCHAR(20),
    HourlyRate INT,
    JobInvolvement INT,
    JobLevel INT,
    JobRole VARCHAR(100),
    JobSatisfaction INT,
    MaritalStatus VARCHAR(30),
    MonthlyIncome INT,
    MonthlyRate INT,
    NumCompaniesWorked INT,
    Over18 VARCHAR(5),
    OverTime VARCHAR(5),
    PercentSalaryHike INT,
    PerformanceRating INT,
    RelationshipSatisfaction INT,
    StandardHours INT,
    StockOptionLevel INT,
    TotalWorkingYears INT,
    TrainingTimesLastYear INT,
    WorkLifeBalance INT,
    YearsAtCompany INT,
    YearsInCurrentRole INT,
    YearsSinceLastPromotion INT,
    YearsWithCurrManager INT,

    EmployeeName VARCHAR(100),
    Email VARCHAR(150),

    employee_id INT NOT NULL,
    employee_sk BIGINT NOT NULL,

    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL,

    is_current TINYINT(1) NOT NULL,

    change_reason VARCHAR(100),

    INDEX idx_staging_employee_id (employee_id),
    INDEX idx_staging_employee_sk (employee_sk),
    INDEX idx_staging_current (is_current),
    INDEX idx_staging_department (Department),
    INDEX idx_staging_job_role (JobRole)
);


-- ============================================================
-- 3. LOAD CSV INTO STAGING
--
-- Change the path below to the actual location of:
-- employee_scd2_130k.csv
--
-- If MySQL Workbench blocks LOCAL INFILE, enable it in the
-- Workbench connection/server settings.
-- ============================================================

LOAD DATA LOCAL INFILE
'C:\\Users\\KavyaAgrawal\\Desktop\\greenfield mini porject\\data\\employee_scd2_130k.csv'

INTO TABLE staging_employees

FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'

LINES TERMINATED BY '\n'

IGNORE 1 LINES

(
    Age,
    Attrition,
    BusinessTravel,
    DailyRate,
    Department,
    DistanceFromHome,
    Education,
    EducationField,
    EmployeeCount,
    EmployeeNumber,
    EnvironmentSatisfaction,
    Gender,
    HourlyRate,
    JobInvolvement,
    JobLevel,
    JobRole,
    JobSatisfaction,
    MaritalStatus,
    MonthlyIncome,
    MonthlyRate,
    NumCompaniesWorked,
    Over18,
    OverTime,
    PercentSalaryHike,
    PerformanceRating,
    RelationshipSatisfaction,
    StandardHours,
    StockOptionLevel,
    TotalWorkingYears,
    TrainingTimesLastYear,
    WorkLifeBalance,
    YearsAtCompany,
    YearsInCurrentRole,
    YearsSinceLastPromotion,
    YearsWithCurrManager,

    EmployeeName,
    Email,

    employee_id,
    employee_sk,

    effective_start_date,
    effective_end_date,

    is_current,

    change_reason
);


-- ============================================================
-- 4. STAGING VALIDATION
-- ============================================================

SELECT
    COUNT(*) AS staging_row_count
FROM staging_employees;


SELECT
    COUNT(DISTINCT employee_id) AS unique_employee_count
FROM staging_employees;


SELECT
    COUNT(DISTINCT employee_sk) AS unique_employee_sk_count
FROM staging_employees;


SELECT
    is_current,
    COUNT(*) AS record_count
FROM staging_employees
GROUP BY is_current;


-- Every employee must have exactly one current record.
SELECT
    employee_id,
    COUNT(*) AS total_versions,
    SUM(is_current) AS current_versions
FROM staging_employees
GROUP BY employee_id
HAVING SUM(is_current) <> 1;


-- Check SCD2 date validity.
SELECT
    employee_id,
    employee_sk,
    effective_start_date,
    effective_end_date
FROM staging_employees
WHERE effective_start_date > effective_end_date;


-- Current records must have open-ended date.
SELECT
    COUNT(*) AS invalid_current_dates
FROM staging_employees
WHERE is_current = 1
  AND effective_end_date <> '9999-12-31';


-- Historical records must have a change reason.
SELECT
    COUNT(*) AS historical_records_without_reason
FROM staging_employees
WHERE is_current = 0
  AND (
      change_reason IS NULL
      OR TRIM(change_reason) = ''
  );
desc staging_employees;
select * from staging_employees limit 10;
-- ============================================================
-- 5. DEPARTMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS departments (

    department_id INT NOT NULL AUTO_INCREMENT,

    department_name VARCHAR(100) NOT NULL,

    PRIMARY KEY (department_id),

    UNIQUE KEY uq_departments_name (
        department_name
    )
);


INSERT INTO departments (
    department_name
)
SELECT DISTINCT
    TRIM(Department)
FROM staging_employees
WHERE Department IS NOT NULL
  AND TRIM(Department) <> '';

select * from departments;
-- ============================================================
-- 6. JOB ROLES
--
-- As agreed:
--   Job Role + Job Level is treated as the lookup combination.
--
-- Therefore:
--   Sales Executive + Level 1
--   Sales Executive + Level 2
--
-- are separate job_roles records.
-- ============================================================

CREATE TABLE IF NOT EXISTS job_roles (

    job_role_id INT NOT NULL AUTO_INCREMENT,

    job_role_name VARCHAR(100) NOT NULL,

    job_level INT NOT NULL,

    PRIMARY KEY (job_role_id),

    UNIQUE KEY uq_job_role_level (
        job_role_name,
        job_level
    )
);


INSERT INTO job_roles (
    job_role_name,
    job_level
)
SELECT DISTINCT
    TRIM(JobRole),
    JobLevel
FROM staging_employees
WHERE JobRole IS NOT NULL
  AND TRIM(JobRole) <> ''
  AND JobLevel IS NOT NULL;

select * from job_roles;
-- ============================================================
-- 7. EMPLOYEES
--
-- Current employee state only.
--
-- Historical versions are stored in employee_job_history.
--
-- employee_id is stable across SCD2 versions.
-- ============================================================

CREATE TABLE IF NOT EXISTS employees (

    employee_id INT NOT NULL,

    employee_number INT NOT NULL,

    employee_name VARCHAR(100),

    first_name VARCHAR(50),
    last_name VARCHAR(50),

    email VARCHAR(150),

    age INT,
    gender VARCHAR(20),
    marital_status VARCHAR(30),

    education INT,
    education_field VARCHAR(100),

    distance_from_home INT,

    num_companies_worked INT,
    total_working_years INT,

    years_at_company INT,
    years_in_current_role INT,

    attrition VARCHAR(10),

    business_travel VARCHAR(50),
    over_time VARCHAR(5),

    stock_option_level INT,

    percent_salary_hike INT,

    environment_satisfaction INT,
    job_involvement INT,
    job_satisfaction INT,
    relationship_satisfaction INT,
    work_life_balance INT,

    training_times_last_year INT,

    monthly_income INT,
    daily_rate INT,
    hourly_rate INT,
    monthly_rate INT,

    employee_count INT,
    standard_hours INT,
    over_18 VARCHAR(5),

    department_id INT,
    job_role_id INT,

    manager_id INT,

    PRIMARY KEY (employee_id),

    UNIQUE KEY uq_employees_employee_number (
        employee_number
    ),

    UNIQUE KEY uq_employees_email (
        email
    ),

    INDEX idx_employees_department (
        department_id
    ),

    INDEX idx_employees_job_role (
        job_role_id
    ),

    INDEX idx_employees_manager (
        manager_id
    ),

    CONSTRAINT fk_employees_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id),

    CONSTRAINT fk_employees_job_role
        FOREIGN KEY (job_role_id)
        REFERENCES job_roles(job_role_id)
);


-- ============================================================
-- 8. INSERT CURRENT EMPLOYEES
-- ============================================================

INSERT INTO employees (

    employee_id,
    employee_number,

    employee_name,

    first_name,
    last_name,

    email,

    age,
    gender,
    marital_status,

    education,
    education_field,

    distance_from_home,

    num_companies_worked,
    total_working_years,

    years_at_company,
    years_in_current_role,

    attrition,

    business_travel,
    over_time,

    stock_option_level,

    percent_salary_hike,

    environment_satisfaction,
    job_involvement,
    job_satisfaction,
    relationship_satisfaction,
    work_life_balance,

    training_times_last_year,

    monthly_income,
    daily_rate,
    hourly_rate,
    monthly_rate,

    employee_count,
    standard_hours,
    over_18,

    department_id,
    job_role_id,

    manager_id
)

SELECT

    s.employee_id,
    s.EmployeeNumber,

    s.EmployeeName,

    -- The synthesizer creates EmployeeName rather than
    -- separate first_name/last_name columns.
    -- Split the name into first/last for OLTP convenience.
    SUBSTRING_INDEX(
        s.EmployeeName,
        ' ',
        1
    ) AS first_name,

    CASE
        WHEN LOCATE(
            ' ',
            s.EmployeeName
        ) > 0
        THEN SUBSTRING(
            s.EmployeeName,
            LOCATE(' ', s.EmployeeName) + 1
        )
        ELSE NULL
    END AS last_name,

    s.Email,

    s.Age,
    s.Gender,
    s.MaritalStatus,

    s.Education,
    s.EducationField,

    s.DistanceFromHome,

    s.NumCompaniesWorked,
    s.TotalWorkingYears,

    s.YearsAtCompany,
    s.YearsInCurrentRole,

    s.Attrition,

    s.BusinessTravel,
    s.OverTime,

    s.StockOptionLevel,

    s.PercentSalaryHike,

    s.EnvironmentSatisfaction,
    s.JobInvolvement,
    s.JobSatisfaction,
    s.RelationshipSatisfaction,
    s.WorkLifeBalance,

    s.TrainingTimesLastYear,

    s.MonthlyIncome,
    s.DailyRate,
    s.HourlyRate,
    s.MonthlyRate,

    s.EmployeeCount,
    s.StandardHours,
    s.Over18,

    d.department_id,
    j.job_role_id,

    NULL AS manager_id

FROM staging_employees s

INNER JOIN departments d
    ON d.department_name = TRIM(s.Department)

INNER JOIN job_roles j
    ON j.job_role_name = TRIM(s.JobRole)
   AND j.job_level = s.JobLevel

WHERE s.is_current = 1;

select * from employees limit 10;

-- ============================================================
-- 9. MANAGER UPDATE
--
-- The source IBM dataset does not contain a manager_id column.
-- Therefore manager_id cannot be derived reliably from this CSV.
--
-- It remains NULL at this stage.
--
-- This is intentional rather than inventing manager relationships.
-- ============================================================


-- ============================================================
-- 10. EMPLOYEE JOB HISTORY — SCD TYPE 2
-- ============================================================
--
-- Every staging version becomes one history record.
--
-- Example:
--
-- employee_id | employee_sk | department | level | current
-- --------------------------------------------------------
-- 10001       | 10001       | Sales      | 2     | 0
-- 10001       | 130001      | Sales      | 3     | 1
--
-- employee_id remains stable.
-- employee_sk identifies the source/version record.
-- ============================================================

CREATE TABLE IF NOT EXISTS employee_job_history (

    job_history_id BIGINT NOT NULL AUTO_INCREMENT,

    employee_sk BIGINT NOT NULL,

    employee_id INT NOT NULL,

    department_id INT NOT NULL,

    job_role_id INT NOT NULL,

    job_level INT NOT NULL,

    monthly_income INT,

    daily_rate INT,

    hourly_rate INT,

    monthly_rate INT,

    business_travel VARCHAR(50),

    over_time VARCHAR(5),

    stock_option_level INT,

    percent_salary_hike INT,

    years_in_current_role INT,

    years_since_last_promotion INT,

    years_with_curr_manager INT,

    effective_start_date DATE NOT NULL,

    effective_end_date DATE NOT NULL,

    is_current TINYINT(1) NOT NULL,

    change_reason VARCHAR(100),

    PRIMARY KEY (job_history_id),

    UNIQUE KEY uq_history_employee_sk (
        employee_sk
    ),

    INDEX idx_history_employee_id (
        employee_id
    ),

    INDEX idx_history_current (
        employee_id,
        is_current
    ),

    INDEX idx_history_dates (
        effective_start_date,
        effective_end_date
    ),

    INDEX idx_history_department (
        department_id
    ),

    INDEX idx_history_job_role (
        job_role_id
    ),

    CONSTRAINT fk_history_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_history_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id),

    CONSTRAINT fk_history_job_role
        FOREIGN KEY (job_role_id)
        REFERENCES job_roles(job_role_id)
);


-- ============================================================
-- 11. INSERT ALL SCD2 VERSIONS
-- ============================================================

INSERT INTO employee_job_history (

    employee_sk,
    employee_id,

    department_id,
    job_role_id,
    job_level,

    monthly_income,
    daily_rate,
    hourly_rate,
    monthly_rate,

    business_travel,
    over_time,

    stock_option_level,
    percent_salary_hike,

    years_in_current_role,
    years_since_last_promotion,
    years_with_curr_manager,

    effective_start_date,
    effective_end_date,

    is_current,
    change_reason
)

SELECT

    s.employee_sk,
    s.employee_id,

    d.department_id,
    j.job_role_id,
    s.JobLevel,

    s.MonthlyIncome,
    s.DailyRate,
    s.HourlyRate,
    s.MonthlyRate,

    s.BusinessTravel,
    s.OverTime,

    s.StockOptionLevel,
    s.PercentSalaryHike,

    s.YearsInCurrentRole,
    s.YearsSinceLastPromotion,
    s.YearsWithCurrManager,

    s.effective_start_date,
    s.effective_end_date,

    s.is_current,
    s.change_reason

FROM staging_employees s

INNER JOIN departments d
    ON d.department_name = TRIM(s.Department)

INNER JOIN job_roles j
    ON j.job_role_name = TRIM(s.JobRole)
   AND j.job_level = s.JobLevel

ORDER BY
    s.employee_id,
    s.effective_start_date;


-- ============================================================
-- 12. REVIEWS
--
-- The IBM dataset contains performance/review-related fields,
-- but does NOT contain an actual review date or review_id.
--
-- We therefore use:
--   EmployeeNumber as source employee identifier
--   effective_start_date as the synthesized review date
--
-- For this initial warehouse load, one review is created from
-- each CURRENT employee record.
-- ============================================================

CREATE TABLE IF NOT EXISTS reviews (

    review_id BIGINT NOT NULL AUTO_INCREMENT,

    employee_id INT NOT NULL,

    reviewer_id INT,

    review_date DATE NOT NULL,

    performance_rating INT,

    environment_satisfaction INT,

    job_involvement INT,

    job_satisfaction INT,

    relationship_satisfaction INT,

    work_life_balance INT,

    percent_salary_hike INT,

    training_times_last_year INT,

    PRIMARY KEY (review_id),

    INDEX idx_reviews_employee (
        employee_id
    ),

    INDEX idx_reviews_date (
        review_date
    ),

    INDEX idx_reviews_rating (
        performance_rating
    ),

    CONSTRAINT fk_reviews_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_reviews_reviewer
        FOREIGN KEY (reviewer_id)
        REFERENCES employees(employee_id)
);

select * from employee_job_history where change_reason!= 'CurrentRecord' limit 20 ;
-- ============================================================
-- 13. INSERT CURRENT EMPLOYEE REVIEW SNAPSHOTS
-- ============================================================

INSERT INTO reviews (

    employee_id,
    reviewer_id,
    review_date,

    performance_rating,

    environment_satisfaction,
    job_involvement,
    job_satisfaction,
    relationship_satisfaction,
    work_life_balance,

    percent_salary_hike,
    training_times_last_year
)

SELECT

    s.employee_id,

    NULL AS reviewer_id,

    s.effective_start_date,

    s.PerformanceRating,

    s.EnvironmentSatisfaction,
    s.JobInvolvement,
    s.JobSatisfaction,
    s.RelationshipSatisfaction,
    s.WorkLifeBalance,

    s.PercentSalaryHike,
    s.TrainingTimesLastYear

FROM staging_employees s

WHERE s.is_current = 1;

select * from reviews limit 10;

-- ============================================================
-- 14. PROJECTS
-- ============================================================
--
-- No project columns exist in the IBM source dataset.
--
-- We create the table now because it is part of the OLTP model,
-- but we intentionally do NOT insert fake projects here.
--
-- Project onboarding will be handled through Streamlit later.
-- ============================================================

CREATE TABLE IF NOT EXISTS projects (

    project_id INT NOT NULL AUTO_INCREMENT,

    project_name VARCHAR(150) NOT NULL,

    department_id INT,

    start_date DATE,

    end_date DATE,

    status VARCHAR(50),

    PRIMARY KEY (project_id),

    INDEX idx_projects_department (
        department_id
    ),

    CONSTRAINT fk_projects_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

select * from projects;

-- ============================================================
-- 15. ASSIGNMENTS
-- ============================================================
--
-- No assignment information exists in the IBM HR dataset.
--
-- Therefore the table is created but intentionally remains
-- empty until projects and employee assignments are created
-- through the application.
-- ============================================================

CREATE TABLE IF NOT EXISTS assignments (

    assignment_id BIGINT NOT NULL AUTO_INCREMENT,

    employee_id INT NOT NULL,

    project_id INT NOT NULL,

    role_on_project VARCHAR(100),

    allocation_ratio DECIMAL(5,2),

    assigned_date DATE NOT NULL,

    end_date DATE,

    PRIMARY KEY (assignment_id),

    INDEX idx_assignments_employee (
        employee_id
    ),

    INDEX idx_assignments_project (
        project_id
    ),

    CONSTRAINT fk_assignments_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_assignments_project
        FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
);

select * from assignments;

-- ============================================================
-- 16. FINAL ROW COUNT CHECK
-- ============================================================

SELECT
    'staging_employees' AS table_name,
    COUNT(*) AS row_count
FROM staging_employees

UNION ALL

SELECT
    'departments',
    COUNT(*)
FROM departments

UNION ALL

SELECT
    'job_roles',
    COUNT(*)
FROM job_roles

UNION ALL

SELECT
    'employees',
    COUNT(*)
FROM employees

UNION ALL

SELECT
    'employee_job_history',
    COUNT(*)
FROM employee_job_history

UNION ALL

SELECT
    'reviews',
    COUNT(*)
FROM reviews

UNION ALL

SELECT
    'projects',
    COUNT(*)
FROM projects

UNION ALL

SELECT
    'assignments',
    COUNT(*)
FROM assignments;


-- ============================================================
-- 17. SCD2 VALIDATION
-- ============================================================

-- Expected:
-- one current version per employee.
-- This query should return ZERO rows.

SELECT
    employee_id,
    COUNT(*) AS total_versions,
    SUM(is_current) AS current_versions
FROM employee_job_history
GROUP BY employee_id
HAVING SUM(is_current) <> 1;


-- Expected:
-- approximately 30,000 employees should have two versions.

SELECT
    version_count,
    COUNT(*) AS employee_count
FROM (
    SELECT
        employee_id,
        COUNT(*) AS version_count
    FROM employee_job_history
    GROUP BY employee_id
) x
GROUP BY version_count
ORDER BY version_count;


-- Expected:
-- historical/current dates should not overlap.
-- Each employee's versions should be sequential.

WITH ordered_history AS (
    SELECT
        employee_id,
        effective_start_date,
        effective_end_date,
        LEAD(effective_start_date) OVER (
            PARTITION BY employee_id
            ORDER BY effective_start_date
        ) AS next_start_date
    FROM employee_job_history
)

SELECT
    employee_id,
    effective_start_date,
    effective_end_date,
    next_start_date
FROM ordered_history
WHERE next_start_date IS NOT NULL
  AND effective_end_date >= next_start_date;


-- ============================================================
-- 18. VERIFY CURRENT EMPLOYEES
-- ============================================================

SELECT
    e.employee_id,
    e.employee_number,
    e.employee_name,
    e.email,
    e.age,
    e.gender,
    d.department_name,
    j.job_role_name,
    j.job_level,
    e.monthly_income,
    e.attrition
FROM employees e

LEFT JOIN departments d
    ON d.department_id = e.department_id

LEFT JOIN job_roles j
    ON j.job_role_id = e.job_role_id

ORDER BY e.employee_id

LIMIT 50;


-- ============================================================
-- 19. VERIFY SCD2 HISTORY
-- ============================================================

SELECT
    h.employee_id,
    h.employee_sk,
    d.department_name,
    j.job_role_name,
    h.job_level,
    h.monthly_income,
    h.effective_start_date,
    h.effective_end_date,
    h.is_current,
    h.change_reason

FROM employee_job_history h

LEFT JOIN departments d
    ON d.department_id = h.department_id

LEFT JOIN job_roles j
    ON j.job_role_id = h.job_role_id

ORDER BY
    h.employee_id,
    h.effective_start_date

LIMIT 100;


-- ============================================================
-- 20. VERIFY REVIEWS
-- ============================================================

SELECT
    r.review_id,
    r.employee_id,
    r.review_date,
    r.performance_rating,
    r.environment_satisfaction,
    r.job_involvement,
    r.job_satisfaction,
    r.relationship_satisfaction,
    r.work_life_balance
FROM reviews r
ORDER BY r.review_id
LIMIT 50;

select employee_id, manager_id from employees;
-- ============================================================
-- END OF STAGING -> OLTP LOAD
-- ============================================================

