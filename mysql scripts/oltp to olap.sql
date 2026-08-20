
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
-- ============================================================
-- ENTERPRISE EMPLOYEE ANALYTICS DATA WAREHOUSE
-- OLAP STAR SCHEMA
--
-- PURPOSE:
--     Creates warehouse tables only.
--
-- DOES NOT:
--     Load data
--     Create ETL procedures
--     Run validation queries
--     Run analytical queries
--
-- SCD TYPE 2:
--     dim_employee
-- ============================================================

CREATE DATABASE IF NOT EXISTS employee_analytics_dw2;

USE employee_analytics_dw2;

-- ============================================================
-- DIM_DATE
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

-- ============================================================
-- DIM_DEPARTMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_department (

    department_sk INT NOT NULL AUTO_INCREMENT,

    department_id INT NOT NULL,

    department_name VARCHAR(100) NOT NULL,

    PRIMARY KEY (department_sk),

    UNIQUE KEY uq_dim_department_id (department_id),
    UNIQUE KEY uq_dim_department_name (department_name)

);

-- ============================================================
-- DIM_PROJECT
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_project (

    project_sk INT NOT NULL AUTO_INCREMENT,

    project_id INT NOT NULL,

    project_name VARCHAR(150) NOT NULL,

    start_date DATE,
    end_date DATE,

    status VARCHAR(50),

    PRIMARY KEY (project_sk),

    UNIQUE KEY uq_dim_project_id (project_id),

    INDEX idx_dim_project_status (status)

);

-- ============================================================
-- DIM_EMPLOYEE (SCD TYPE 2)
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_employee (

    employee_sk INT NOT NULL AUTO_INCREMENT,

    employee_id INT NOT NULL,

    department_sk INT NOT NULL,

    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(150),

    age INT,
    gender VARCHAR(20),
    marital_status VARCHAR(30),
    education_field VARCHAR(100),

    job_role VARCHAR(100),
    job_level INT,

    monthly_income INT,
    daily_rate INT,
    hourly_rate INT,

    business_travel VARCHAR(50),
    distance_from_home INT,

    years_with_curr_manager INT,
    years_since_last_promotion INT,
    years_at_company INT,

    attrition VARCHAR(10),

    manager_id INT,

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
-- DIM_ASSIGNMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_assignment (

    assignment_sk INT NOT NULL AUTO_INCREMENT,

    assignment_id BIGINT NOT NULL,

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

-- ============================================================
-- FACT_PERFORMANCE_REVIEWS
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_performance_reviews (

    review_sk INT NOT NULL AUTO_INCREMENT,

    employee_sk INT NOT NULL,
    department_sk INT NOT NULL,
    project_sk INT NULL,
    date_sk INT NOT NULL,

    review_id BIGINT,

    performance_rating INT,

    PRIMARY KEY (review_sk),

    UNIQUE KEY uq_fact_source_review (
        review_id,
        employee_sk
    ),

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
-- SCHEMA VERIFICATION
-- ============================================================

SHOW TABLES;

DESCRIBE dim_date;
DESCRIBE dim_department;
DESCRIBE dim_project;
DESCRIBE dim_employee;
DESCRIBE dim_assignment;
DESCRIBE fact_performance_reviews;

-- ============================================================
-- END OF OLAP SCHEMA
-- ============================================================