
-- ============================================================
-- ENTERPRISE EMPLOYEE ANALYTICS & DATA WAREHOUSE
-- OLAP / DATA WAREHOUSE SCHEMA
--
-- Source OLTP database:
--   employee_analytics_dw2
--
-- Star Schema:
--
--                    dim_date
--                       |
--                       |
-- dim_employee ---- fact_performance_reviews ---- dim_project
--       |
--       |
-- dim_department
--
-- IMPORTANT:
--   1. This script creates ONLY the OLAP tables.
--   2. It does NOT load data.
--   3. It does NOT TRUNCATE or DROP tables.
--   4. Run this AFTER the OLTP -> staging/OLTP script.
--   5. Then run oltp_to_olap.sql.
--
-- SCD TYPE 2:
--   employee_id = stable business key
--   employee_sk = OLAP surrogate key
--   multiple dim_employee rows may share employee_id
-- ============================================================

CREATE DATABASE IF NOT EXISTS employee_analytics_dw2;

USE employee_analytics_dw2;

-- ============================================================
-- 1. DIM_DATE
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_date (
    date_sk INT NOT NULL,
    full_date DATE NOT NULL,

    day INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,

    is_weekend TINYINT(1) NOT NULL,

    PRIMARY KEY (date_sk),

    UNIQUE KEY uq_dim_date_full_date (full_date),

    INDEX idx_dim_date_year_month (year, month),
    INDEX idx_dim_date_year_quarter (year, quarter)
);
select * from dim_date;
-- ============================================================
-- 2. DIM_DEPARTMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_department (
    department_sk INT NOT NULL AUTO_INCREMENT,

    -- OLTP business/natural key
    department_id INT NOT NULL,

    department_name VARCHAR(100) NOT NULL,

    PRIMARY KEY (department_sk),

    UNIQUE KEY uq_dim_department_id (department_id),

    UNIQUE KEY uq_dim_department_name (department_name)
);
select * from dim_department;
-- ============================================================
-- 3. DIM_PROJECT
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_project (
    project_sk INT NOT NULL AUTO_INCREMENT,

    -- OLTP business key
    project_id INT NOT NULL,

    project_name VARCHAR(150) NOT NULL,

    start_date DATE,
    end_date DATE,
    status VARCHAR(50),

    PRIMARY KEY (project_sk),

    UNIQUE KEY uq_dim_project_id (project_id),

    INDEX idx_dim_project_status (status)
);
select * from employees where employee_id = 200001;
-- ============================================================
-- 4. DIM_EMPLOYEE — SCD TYPE 2
--
-- Grain:
--   One row = one historical version of one employee.
--
-- employee_id:
--   Stable employee/business identifier.
--
-- employee_sk:
--   Warehouse-generated surrogate key.
--
-- Example:
--
-- employee_sk | employee_id | department | job_level | current
-- -------------------------------------------------------------
-- 1           | 1001        | Sales      | 2         | 0
-- 2           | 1001        | Sales      | 3         | 0
-- 3           | 1001        | IT         | 3         | 1
--
-- The source employee_sk from employee_job_history is NOT
-- reused as the warehouse employee_sk.
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_employee (

    employee_sk INT NOT NULL AUTO_INCREMENT,

    -- Stable business key
    employee_id INT NOT NULL,

    -- Warehouse FK
    department_sk INT NOT NULL,

    -- Employee identity
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(150),

    -- Demographics
    age INT,
    gender VARCHAR(20),
    marital_status VARCHAR(30),
    education_field VARCHAR(100),

    -- Job
    job_role VARCHAR(100),
    job_level INT,

    -- Compensation
    monthly_income INT,
    daily_rate INT,
    hourly_rate INT,

    -- Work information
    business_travel VARCHAR(50),
    distance_from_home INT,

    -- Career / tenure
    years_with_curr_manager INT,
    years_since_last_promotion INT,
    years_at_company INT,

    -- Status
    attrition VARCHAR(10),

    -- Manager remains a business identifier.
    -- No FK is used because manager history can also be SCD2.
    manager_id INT,

    -- SCD2 metadata
    change_reason VARCHAR(100),

    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL,

    is_current TINYINT(1) NOT NULL DEFAULT 1,

    PRIMARY KEY (employee_sk),

    INDEX idx_dim_employee_id (employee_id),

    INDEX idx_dim_employee_current (
        employee_id,
        is_current
    ),

    INDEX idx_dim_employee_dates (
        effective_start_date,
        effective_end_date
    ),

    INDEX idx_dim_employee_department (
        department_sk
    ),

    INDEX idx_dim_employee_job_level (
        job_level
    ),

    INDEX idx_dim_employee_attrition (
        attrition
    ),

    CONSTRAINT fk_dim_employee_department
        FOREIGN KEY (department_sk)
        REFERENCES dim_department(department_sk)
);

-- ============================================================
-- 5. FACT_PERFORMANCE_REVIEWS
--
-- Grain:
--   ONE ROW = ONE employee performance review.
--
-- Dimension keys:
--   employee_sk
--   department_sk
--   project_sk
--   date_sk
--
-- Measures:
--   performance_rating
--
-- project_sk is nullable because the current IBM-derived OLTP
-- dataset has no project information. Projects/assignments are
-- created later through the application.
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_performance_reviews (

    review_sk INT NOT NULL AUTO_INCREMENT,

    employee_sk INT NOT NULL,
    department_sk INT NOT NULL,
    project_sk INT NULL,
    date_sk INT NOT NULL,

    -- Source OLTP review identifier
    review_id BIGINT,

    -- Measures
    performance_rating INT,

    PRIMARY KEY (review_sk),

    INDEX idx_fact_employee (
        employee_sk
    ),

    INDEX idx_fact_department (
        department_sk
    ),

    INDEX idx_fact_project (
        project_sk
    ),

    INDEX idx_fact_date (
        date_sk
    ),

    INDEX idx_fact_rating (
        performance_rating
    ),

    -- Prevent accidental duplicate loading of the same source
    -- review into the same employee history version.
    UNIQUE KEY uq_fact_source_review (
        review_id,
        employee_sk
    ),

    CONSTRAINT fk_fact_employee
        FOREIGN KEY (employee_sk)
        REFERENCES dim_employee(employee_sk),

    CONSTRAINT fk_fact_department
        FOREIGN KEY (department_sk)
        REFERENCES dim_department(department_sk),

    CONSTRAINT fk_fact_project
        FOREIGN KEY (project_sk)
        REFERENCES dim_project(project_sk),

    CONSTRAINT fk_fact_date
        FOREIGN KEY (date_sk)
        REFERENCES dim_date(date_sk)
);

-- ============================================================
-- 6. VERIFY CREATED OLAP TABLES
-- ============================================================

SHOW TABLES;

-- ============================================================
-- 7. VERIFY STRUCTURES
-- ============================================================

DESCRIBE dim_date;
DESCRIBE dim_department;
DESCRIBE dim_project;
DESCRIBE dim_employee;
DESCRIBE fact_performance_reviews;

-- ============================================================
-- 8. VERIFY FOREIGN KEYS
-- ============================================================

SELECT
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'employee_analytics_dw2'
  AND TABLE_NAME IN (
      'dim_employee',
      'fact_performance_reviews'
  )
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY
    TABLE_NAME,
    COLUMN_NAME;

-- ============================================================
-- END OF OLAP SCHEMA
-- ============================================================


-- ============================================================
-- ENTERPRISE EMPLOYEE ANALYTICS & DATA WAREHOUSE
-- OLTP -> OLAP ETL
--
-- Source OLTP database:
--     employee_analytics_dw2
--
-- Source tables:
--     departments
--     job_roles
--     employees
--     employee_job_history
--     reviews
--     projects
--     assignments
--
-- Target OLAP tables:
--     dim_date
--     dim_department
--     dim_project
--     dim_employee       (SCD TYPE 2)
--     fact_performance_reviews
--
-- IMPORTANT:
-- 1. This is an INITIAL OLTP -> OLAP load.
-- 2. No TRUNCATE or DROP statements are used.
-- 3. The OLAP schema must already exist.
-- 4. This script assumes the OLTP script has already populated
--    the source tables.
-- 5. employee_job_history contains ALL employee versions.
-- 6. employees contains CURRENT employee state only.
-- 7. Projects/assignments are currently empty because the IBM
--    source dataset has no project information.
--
-- SCD TYPE 2:
--     employee_id = stable business key
--     dim_employee.employee_sk = OLAP surrogate key
--     effective_start_date / effective_end_date define validity
--     is_current identifies the active version
--
-- CTE + WINDOW FUNCTIONS:
--     Dim_Date uses a recursive CTE.
--     SCD2 validation uses LEAD().
--     Fact loading uses ROW_NUMBER() to select a single
--     project assignment when multiple assignments overlap.
-- ============================================================

USE employee_analytics_dw2;


-- ============================================================
-- 1. VALIDATE SOURCE TABLES
-- ============================================================

SELECT 'departments' AS source_table, COUNT(*) AS row_count
FROM departments
UNION ALL
SELECT 'job_roles', COUNT(*)
FROM job_roles
UNION ALL
SELECT 'employees', COUNT(*)
FROM employees
UNION ALL
SELECT 'employee_job_history', COUNT(*)
FROM employee_job_history
UNION ALL
SELECT 'reviews', COUNT(*)
FROM reviews
UNION ALL
SELECT 'projects', COUNT(*)
FROM projects
UNION ALL
SELECT 'assignments', COUNT(*)
FROM assignments;


-- ============================================================
-- 2. LOAD DIM_DEPARTMENT
-- ============================================================
--
-- OLTP:
--     department_id
--
-- OLAP:
--     department_sk = warehouse surrogate key
--
-- ============================================================

INSERT INTO dim_department (
    department_id,
    department_name
)
SELECT
    d.department_id,
    TRIM(d.department_name)
FROM departments d
WHERE NOT EXISTS (
    SELECT 1
    FROM dim_department dd
    WHERE dd.department_id = d.department_id
);


-- ============================================================
-- 3. LOAD DIM_PROJECT
-- ============================================================
--
-- Project data is currently expected to be empty in OLTP.
-- When projects are created through Streamlit, this ETL can
-- load them into the warehouse.
--
-- ============================================================

INSERT INTO dim_project (
    project_id,
    project_name,
    start_date,
    end_date,
    status
)
SELECT
    p.project_id,
    p.project_name,
    p.start_date,
    p.end_date,
    p.status
FROM projects p
WHERE NOT EXISTS (
    SELECT 1
    FROM dim_project dp
    WHERE dp.project_id = p.project_id
);


-- ============================================================
-- 4. LOAD DIM_DATE
-- ============================================================
--
-- The OLTP reviews use effective_start_date as the synthesized
-- review_date. Generate a calendar covering all review dates.
--
-- Recursive CTE = required advanced SQL transformation.
--
-- If no reviews exist, no dates are inserted.
-- ============================================================

-- ============================================================
-- LOAD DIM_DATE
-- ============================================================
-- Generates one row for every date between the earliest and
-- latest review date in the OLTP reviews table.
--
-- Uses a recursive CTE as required by the project.
-- ============================================================
drop table dim_assignment;
desc dim_assignment;
CREATE TABLE IF NOT EXISTS dim_assignment (

    assignment_sk INT NOT NULL AUTO_INCREMENT,

    -- OLTP business key
    assignment_id BIGINT NOT NULL,

    -- OLAP surrogate keys
    employee_sk INT NOT NULL,
    project_sk INT NOT NULL,

    role_on_project VARCHAR(100),

    allocation_ratio DECIMAL(5,2),

    assigned_date DATE NOT NULL,

    end_date DATE,

    PRIMARY KEY (assignment_sk),

    UNIQUE KEY uq_dim_assignment_id (
        assignment_id
    ),

    INDEX idx_dim_assignment_employee (
        employee_sk
    ),

    INDEX idx_dim_assignment_project (
        project_sk
    ),

    INDEX idx_dim_assignment_dates (
        assigned_date,
        end_date
    ),

    CONSTRAINT fk_dim_assignment_employee
        FOREIGN KEY (employee_sk)
        REFERENCES dim_employee(employee_sk),

    CONSTRAINT fk_dim_assignment_project
        FOREIGN KEY (project_sk)
        REFERENCES dim_project(project_sk)
);


DELIMITER $$

CREATE PROCEDURE load_dim_assignment()
BEGIN

    INSERT INTO dim_assignment (
        assignment_id,
        employee_sk,
        project_sk,
        role_on_project,
        allocation_ratio,
        assigned_date,
        end_date
    )

    SELECT
        a.assignment_id,

        de.employee_sk,

        dp.project_sk,

        a.role_on_project,

        a.allocation_ratio,

        a.assigned_date,

        a.end_date

    FROM assignments a

    INNER JOIN dim_employee de
        ON de.employee_id = a.employee_id

        -- Find the SCD2 employee version that was valid
        -- when the assignment started.
        AND a.assigned_date >= de.effective_start_date
        AND a.assigned_date <= de.effective_end_date

    INNER JOIN dim_project dp
        ON dp.project_id = a.project_id

    WHERE NOT EXISTS (
        SELECT 1
        FROM dim_assignment da
        WHERE da.assignment_id = a.assignment_id
    );

END$$

DELIMITER ;


INSERT INTO dim_date (
    date_sk,
    full_date,
    day,
    month,
    month_name,
    quarter,
    year,
    is_weekend
)

WITH RECURSIVE date_range AS (

    SELECT
        MIN(review_date) AS full_date,
        MAX(review_date) AS max_date

    FROM reviews

    WHERE review_date IS NOT NULL


    UNION ALL


    SELECT
        DATE_ADD(full_date, INTERVAL 1 DAY),
        max_date

    FROM date_range

    WHERE full_date < max_date
),

calendar AS (

    SELECT
        full_date

    FROM date_range

    WHERE full_date IS NOT NULL
)

SELECT

    YEAR(c.full_date) * 10000
        + MONTH(c.full_date) * 100
        + DAY(c.full_date) AS date_sk,

    c.full_date,

    DAY(c.full_date) AS day,

    MONTH(c.full_date) AS month,

    MONTHNAME(c.full_date) AS month_name,

    QUARTER(c.full_date) AS quarter,

    YEAR(c.full_date) AS year,

    CASE
        WHEN DAYOFWEEK(c.full_date) IN (1, 7)
        THEN 1
        ELSE 0
    END AS is_weekend

FROM calendar c

WHERE NOT EXISTS (

    SELECT 1

    FROM dim_date dd

    WHERE dd.full_date = c.full_date
);


-- ============================================================
-- 5. LOAD DIM_EMPLOYEE — SCD TYPE 2
-- ============================================================
--
-- Source:
--     employee_job_history
--
-- IMPORTANT:
-- Do NOT join only on employee_id when loading SCD2.
-- Each employee_id can have multiple historical versions.
--
-- department_id from OLTP is mapped to department_sk.
--
-- job_role_id from OLTP is converted to the descriptive
-- job_role name in the warehouse.
--
-- The OLAP employee_sk is generated automatically by
-- AUTO_INCREMENT and is NOT copied from the OLTP employee_sk.
--
-- ============================================================
use employee_analytics_dw2;
select * from dim_employee where employee_id = 200003;
select * from employee_job_history where employee_id = 200001;
select * from projects;

INSERT INTO dim_employee (
    employee_id,
    department_sk,

    first_name,
    last_name,
    email,

    age,
    gender,
    marital_status,
    education_field,

    job_role,
    job_level,

    monthly_income,
    daily_rate,
    hourly_rate,

    business_travel,
    distance_from_home,

    years_with_curr_manager,
    years_since_last_promotion,
    years_at_company,

    attrition,

    manager_id,

    change_reason,

    effective_start_date,
    effective_end_date,
    is_current
)
SELECT
    h.employee_id,

    dd.department_sk,

    e.first_name,
    e.last_name,
    e.email,

    e.age,
    e.gender,
    e.marital_status,
    e.education_field,

    jr.job_role_name,
    h.job_level,

    h.monthly_income,
    h.daily_rate,
    h.hourly_rate,

    h.business_travel,
    e.distance_from_home,

    h.years_with_curr_manager,
    h.years_since_last_promotion,
    e.years_at_company,

    e.attrition,

    e.manager_id,

    h.change_reason,

    h.effective_start_date,
    h.effective_end_date,
    h.is_current

FROM employee_job_history h

INNER JOIN employees e
    ON e.employee_id = h.employee_id

INNER JOIN dim_department dd
    ON dd.department_id = h.department_id

INNER JOIN job_roles jr
    ON jr.job_role_id = h.job_role_id

WHERE NOT EXISTS (
    SELECT 1
    FROM dim_employee de
    WHERE de.employee_id = h.employee_id
      AND de.effective_start_date = h.effective_start_date
      AND de.effective_end_date = h.effective_end_date
);


-- ============================================================
-- 6. SCD TYPE 2 VALIDATION
-- ============================================================

-- Every employee must have exactly one current version.
-- Expected result: ZERO ROWS.

SELECT
    employee_id,
    COUNT(*) AS total_versions,
    SUM(is_current) AS current_versions
FROM dim_employee
GROUP BY employee_id
HAVING SUM(is_current) <> 1;


-- Historical versions should not overlap.
-- Uses LEAD() window function.
-- Expected result: ZERO ROWS.

WITH ordered_employee_history AS (

    SELECT
        employee_id,
        employee_sk,
        effective_start_date,
        effective_end_date,

        LEAD(effective_start_date) OVER (
            PARTITION BY employee_id
            ORDER BY effective_start_date
        ) AS next_start_date

    FROM dim_employee
)

SELECT
    employee_id,
    employee_sk,
    effective_start_date,
    effective_end_date,
    next_start_date

FROM ordered_employee_history

WHERE next_start_date IS NOT NULL
  AND effective_end_date >= next_start_date;


-- Check that current records are open-ended.
-- Expected result: ZERO ROWS.

SELECT
    employee_id,
    employee_sk,
    effective_end_date
FROM dim_employee
WHERE is_current = 1
  AND effective_end_date <> '9999-12-31';


-- ============================================================
-- 7. LOAD FACT_PERFORMANCE_REVIEWS
-- ============================================================
--
-- FACT GRAIN:
--     One row = one employee performance review.
--
-- Review date:
--     reviews.review_date
--
-- SCD2 mapping:
--     review_date must fall between the employee dimension
--     version's effective_start_date and effective_end_date.
--
-- Project mapping:
--     An employee may have multiple assignments.
--     ROW_NUMBER() selects one valid assignment for the
--     review date. If there is no project assignment,
--     project_sk remains NULL.
--
-- department_sk:
--     Comes from the matched historical Dim_Employee version.
--
-- ============================================================


-- ============================================================
-- LOAD FACT_PERFORMANCE_REVIEWS
-- ============================================================
-- Grain:
--     One row = one performance review
--
-- SCD TYPE 2:
--     review_date determines which historical Dim_Employee
--     record should receive the fact.
--
-- WINDOW FUNCTION:
--     ROW_NUMBER() selects the most recent valid assignment.
--
-- ============================================================

INSERT INTO fact_performance_reviews (
    employee_sk,
    department_sk,
    project_sk,
    date_sk,
    review_id,
    performance_rating
)

SELECT

    de.employee_sk,

    de.department_sk,

    dp.project_sk,

    dt.date_sk,

    r.review_id,

    r.performance_rating

FROM reviews r


-- ============================================================
-- SCD TYPE 2 EMPLOYEE LOOKUP
-- ============================================================

INNER JOIN dim_employee de

    ON de.employee_id = r.employee_id

   AND r.review_date >= de.effective_start_date

   AND r.review_date <= de.effective_end_date


-- ============================================================
-- DATE DIMENSION
-- ============================================================

INNER JOIN dim_date dt

    ON dt.full_date = r.review_date


-- ============================================================
-- VALID ASSIGNMENTS
-- ============================================================
-- The subquery uses ROW_NUMBER().
--
-- For each review:
--     rank valid assignments
--     newest assignment = rank 1
-- ============================================================

LEFT JOIN (

    SELECT
        review_id,
        project_id,
        assignment_rank

    FROM (

        SELECT

            r2.review_id,

            a.project_id,

            ROW_NUMBER() OVER (

                PARTITION BY r2.review_id

                ORDER BY
                    a.assigned_date DESC,
                    a.assignment_id DESC

            ) AS assignment_rank

        FROM reviews r2

        LEFT JOIN assignments a

            ON a.employee_id = r2.employee_id

           AND r2.review_date >= a.assigned_date

           AND (
                a.end_date IS NULL
                OR r2.review_date <= a.end_date
           )

    ) ranked_assignments

    WHERE assignment_rank = 1

) va

    ON va.review_id = r.review_id


-- ============================================================
-- PROJECT DIMENSION
-- ============================================================

LEFT JOIN dim_project dp

    ON dp.project_id = va.project_id


-- ============================================================
-- DUPLICATE PROTECTION
-- ============================================================

WHERE NOT EXISTS (

    SELECT 1

    FROM fact_performance_reviews f

    WHERE f.review_id = r.review_id
);

DELIMITER $$



-- ============================================================
-- 8. FACT VALIDATION
-- ============================================================

-- Check total fact records.

SELECT
    COUNT(*) AS fact_review_count
FROM fact_performance_reviews;


-- Check reviews that did not find an SCD2 employee version.
-- Expected result: ZERO ROWS.

SELECT
    r.review_id,
    r.employee_id,
    r.review_date
FROM reviews r
LEFT JOIN dim_employee de
    ON de.employee_id = r.employee_id
   AND r.review_date >= de.effective_start_date
   AND r.review_date <= de.effective_end_date
WHERE de.employee_sk IS NULL;


-- Check fact records with no project.
-- This is NOT an error when assignments are empty.
-- It will return all reviews until projects are created.

SELECT
    COUNT(*) AS reviews_without_project
FROM fact_performance_reviews
WHERE project_sk IS NULL;


-- ============================================================
-- 9. FINAL WAREHOUSE ROW COUNTS
-- ============================================================

SELECT
    'dim_date' AS table_name,
    COUNT(*) AS row_count
FROM dim_date

UNION ALL

SELECT
    'dim_department',
    COUNT(*)
FROM dim_department

UNION ALL

SELECT
    'dim_project',
    COUNT(*)
FROM dim_project

UNION ALL

SELECT
    'dim_employee',
    COUNT(*)
FROM dim_employee

UNION ALL

SELECT
    'fact_performance_reviews',
    COUNT(*)
FROM fact_performance_reviews;


-- ============================================================
-- 10. VERIFY DIMENSION DATA
-- ============================================================

SELECT
    de.employee_sk,
    de.employee_id,
    de.first_name,
    de.last_name,
    dd.department_name,
    de.job_role,
    de.job_level,
    de.monthly_income,
    de.effective_start_date,
    de.effective_end_date,
    de.is_current,
    de.change_reason
FROM dim_employee de

INNER JOIN dim_department dd
    ON dd.department_sk = de.department_sk

ORDER BY
    de.employee_id,
    de.effective_start_date

LIMIT 100;


-- ============================================================
-- 11. VERIFY FACT DATA
-- ============================================================

SELECT
    f.review_sk,
    f.review_id,
    f.employee_sk,
    de.employee_id,
    dd.department_name,
    dp.project_name,
    dt.full_date,
    f.performance_rating

FROM fact_performance_reviews f

INNER JOIN dim_employee de
    ON de.employee_sk = f.employee_sk

INNER JOIN dim_department dd
    ON dd.department_sk = f.department_sk

LEFT JOIN dim_project dp
    ON dp.project_sk = f.project_sk

INNER JOIN dim_date dt
    ON dt.date_sk = f.date_sk

ORDER BY
    f.review_sk

LIMIT 100;


-- ============================================================
-- 12. SCD2 EXAMPLE CHECK
-- ============================================================
--
-- Employees with more than one warehouse version.
-- This confirms that historical records were preserved.
-- ============================================================

SELECT
    employee_id,
    COUNT(*) AS version_count
FROM dim_employee
GROUP BY employee_id
HAVING COUNT(*) > 1
ORDER BY version_count DESC, employee_id
LIMIT 50;


-- ============================================================
-- 13. BASIC ANALYTICAL CHECK
-- ============================================================
--
-- Average performance by department.
-- This confirms the star schema can already support
-- analytical queries.
-- ============================================================

SELECT
    dd.department_name,
    COUNT(f.review_sk) AS review_count,
    ROUND(
        AVG(f.performance_rating),
        2
    ) AS average_performance_rating

FROM fact_performance_reviews f

INNER JOIN dim_department dd
    ON dd.department_sk = f.department_sk

GROUP BY
    dd.department_sk,
    dd.department_name

ORDER BY
    average_performance_rating DESC;


# Year-over-Year Performance Trends

WITH yearly_performance AS (

    SELECT
        d.year,
        COUNT(f.review_sk) AS total_reviews,
        ROUND(AVG(f.performance_rating), 2) AS avg_performance

    FROM fact_performance_reviews f

    INNER JOIN dim_date d
        ON d.date_sk = f.date_sk

    GROUP BY
        d.year
),

yearly_with_previous AS (

    SELECT
        year,
        total_reviews,
        avg_performance,

        LAG(avg_performance) OVER (
            ORDER BY year
        ) AS previous_year_avg

    FROM yearly_performance
)

SELECT
    year,
    total_reviews,
    avg_performance,
    previous_year_avg,

    ROUND(
        avg_performance - previous_year_avg,
        2
    ) AS performance_change

FROM yearly_with_previous

ORDER BY year;



-- ============================================================
-- END OF OLTP -> OLAP ETL
-- ============================================================