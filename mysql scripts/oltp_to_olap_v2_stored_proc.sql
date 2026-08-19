-- ============================================================
-- STRICT STAR SCHEMA & STORED PROCEDURE ETL
-- ============================================================

USE employee_analytics_dw2;
select * from dim_employee;

-- DROP Foreign Keys to safely recreate tables
ALTER TABLE fact_performance_reviews DROP FOREIGN KEY fk_fact_employee;
ALTER TABLE dim_assignment DROP FOREIGN KEY fk_dim_assignment_employee;

-- DROP dim_employee and recreate as Strict Star Schema
DROP TABLE IF EXISTS dim_employee;

CREATE TABLE IF NOT EXISTS dim_employee (
    employee_sk INT NOT NULL AUTO_INCREMENT,
    employee_id INT NOT NULL,

    -- DENORMALIZED: Replaced department_sk with department_name
    department_name VARCHAR(100) NOT NULL,

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
    INDEX idx_dim_employee_current (employee_id, is_current),
    INDEX idx_dim_employee_dates (effective_start_date, effective_end_date)
);

-- Re-add Foreign Keys
ALTER TABLE fact_performance_reviews ADD CONSTRAINT fk_fact_employee FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk);
ALTER TABLE dim_assignment ADD CONSTRAINT fk_dim_assignment_employee FOREIGN KEY (employee_sk) REFERENCES dim_employee(employee_sk);


-- ============================================================
-- STORED PROCEDURE: INITIAL ETL LOAD
-- ============================================================
DELIMITER $$

DROP PROCEDURE IF EXISTS sp_run_full_etl_load$$
CREATE PROCEDURE sp_run_full_etl_load()
BEGIN
    -- 1. Load dim_employee (SCD2)
    -- Joins against live departments table to grab department_name directly!
    INSERT INTO dim_employee (
        employee_id,
        department_name,
        first_name, last_name, email, age, gender, marital_status, education_field,
        job_role, job_level, monthly_income, daily_rate, hourly_rate,
        business_travel, distance_from_home, years_with_curr_manager, years_since_last_promotion,
        years_at_company, attrition, manager_id, change_reason,
        effective_start_date, effective_end_date, is_current
    )
    SELECT
        h.employee_id,
        TRIM(d.department_name),
        e.first_name, e.last_name, e.email, e.age, e.gender, e.marital_status, e.education_field,
        jr.job_role_name, h.job_level, h.monthly_income, h.daily_rate, h.hourly_rate,
        h.business_travel, e.distance_from_home, h.years_with_curr_manager, h.years_since_last_promotion,
        e.years_at_company, e.attrition, e.manager_id, h.change_reason,
        h.effective_start_date, h.effective_end_date, h.is_current
    FROM employee_job_history h
    INNER JOIN employees e ON e.employee_id = h.employee_id
    INNER JOIN departments d ON d.department_id = h.department_id
    INNER JOIN job_roles jr ON jr.job_role_id = h.job_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM dim_employee de
        WHERE de.employee_id = h.employee_id
          AND de.effective_start_date = h.effective_start_date
          AND de.effective_end_date = h.effective_end_date
    );

    -- 2. Clean and Reload fact_performance_reviews
    -- (We truncate here only because this is an initial load procedure)
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE fact_performance_reviews;
    SET FOREIGN_KEY_CHECKS = 1;

    INSERT INTO fact_performance_reviews (
        employee_sk, department_sk, project_sk, date_sk, review_id, performance_rating
    )
    SELECT
        de.employee_sk,
        dd.department_sk,
        dp.project_sk,
        dt.date_sk,
        r.review_id,
        r.performance_rating
    FROM reviews r
    INNER JOIN dim_employee de 
        ON de.employee_id = r.employee_id 
        AND r.review_date >= de.effective_start_date 
        AND r.review_date <= de.effective_end_date
    INNER JOIN dim_department dd 
        ON dd.department_name = de.department_name
    INNER JOIN dim_date dt 
        ON dt.full_date = r.review_date
    LEFT JOIN (
        SELECT review_id, project_id
        FROM (
            SELECT r2.review_id, a.project_id,
                   ROW_NUMBER() OVER (PARTITION BY r2.review_id ORDER BY a.assigned_date DESC, a.assignment_id DESC) AS rnk
            FROM reviews r2
            LEFT JOIN assignments a ON a.employee_id = r2.employee_id
                AND r2.review_date >= a.assigned_date
                AND (a.end_date IS NULL OR r2.review_date <= a.end_date)
        ) ranked WHERE rnk = 1
    ) va ON va.review_id = r.review_id
    LEFT JOIN dim_project dp ON dp.project_id = va.project_id;

END$$
DELIMITER ;

CALL sp_run_full_etl_load();

select * from dim_department;

select * from fact_performance_reviews;

select * from dim_project;

select * from dim_assignment;

USE employee_analytics_dw2;

-- ==============================================================================
-- 1. DIM_DEPARTMENT STORED PROCEDURE
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_load_dim_department;
DELIMITER $$
CREATE PROCEDURE sp_load_dim_department()
BEGIN
    -- Truncate existing data safely
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE dim_department;
    SET FOREIGN_KEY_CHECKS = 1;
    
    INSERT INTO dim_department (department_id, department_name)
    SELECT d.department_id, TRIM(d.department_name)
    FROM departments d;
END$$
DELIMITER ;


-- ==============================================================================
-- 2. DIM_PROJECT STORED PROCEDURE
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_load_dim_project;
DELIMITER $$
CREATE PROCEDURE sp_load_dim_project()
BEGIN
    -- Truncate existing data safely
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE dim_project;
    SET FOREIGN_KEY_CHECKS = 1;
    
    INSERT INTO dim_project (project_id, project_name, start_date, end_date, status)
    SELECT p.project_id, p.project_name, p.start_date, p.end_date, p.status
    FROM projects p;
END$$
DELIMITER ;


-- ==============================================================================
-- 3. DIM_DATE STORED PROCEDURE (Recursive CTE)
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_load_dim_date;
DELIMITER $$
CREATE PROCEDURE sp_load_dim_date()
BEGIN
    -- Truncate existing data safely
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE dim_date;
    SET FOREIGN_KEY_CHECKS = 1;

    INSERT INTO dim_date (date_sk, full_date, day, month, month_name, quarter, year, is_weekend)
    WITH RECURSIVE date_range AS (
        SELECT MIN(review_date) AS full_date, MAX(review_date) AS max_date 
        FROM reviews WHERE review_date IS NOT NULL
        
        UNION ALL
        
        SELECT DATE_ADD(full_date, INTERVAL 1 DAY), max_date 
        FROM date_range WHERE full_date < max_date
    ),
    calendar AS (
        SELECT full_date FROM date_range WHERE full_date IS NOT NULL
    )
    SELECT 
        YEAR(c.full_date) * 10000 + MONTH(c.full_date) * 100 + DAY(c.full_date) AS date_sk,
        c.full_date, DAY(c.full_date) AS day, MONTH(c.full_date) AS month, MONTHNAME(c.full_date) AS month_name,
        QUARTER(c.full_date) AS quarter, YEAR(c.full_date) AS year,
        CASE WHEN DAYOFWEEK(c.full_date) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend
    FROM calendar c;
END$$
DELIMITER ;


-- ==============================================================================
-- 4. DIM_EMPLOYEE STORED PROCEDURE (No Truncate, Preserves SCD2)
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_load_dim_employee;
DELIMITER $$
CREATE PROCEDURE sp_load_dim_employee()
BEGIN
    -- NOTE: NO TRUNCATE HERE. We use WHERE NOT EXISTS to protect history.
    INSERT INTO dim_employee (
        employee_id, department_name, first_name, last_name, email, age, gender, marital_status, education_field,
        job_role, job_level, monthly_income, daily_rate, hourly_rate, business_travel, distance_from_home, years_with_curr_manager, years_since_last_promotion,
        years_at_company, attrition, manager_id, change_reason, effective_start_date, effective_end_date, is_current
    )
    SELECT h.employee_id, TRIM(d.department_name), e.first_name, e.last_name, e.email, e.age, e.gender, e.marital_status, e.education_field,
        jr.job_role_name, h.job_level, h.monthly_income, h.daily_rate, h.hourly_rate, h.business_travel, e.distance_from_home, h.years_with_curr_manager, h.years_since_last_promotion,
        e.years_at_company, e.attrition, e.manager_id, h.change_reason, h.effective_start_date, h.effective_end_date, h.is_current
    FROM employee_job_history h
    INNER JOIN employees e ON e.employee_id = h.employee_id
    INNER JOIN departments d ON d.department_id = h.department_id
    INNER JOIN job_roles jr ON jr.job_role_id = h.job_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM dim_employee de
        WHERE de.employee_id = h.employee_id AND de.effective_start_date = h.effective_start_date AND de.effective_end_date = h.effective_end_date
    );
END$$
DELIMITER ;


-- ==============================================================================
-- 5. DIM_ASSIGNMENT STORED PROCEDURE
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_load_dim_assignment;
DELIMITER $$
CREATE PROCEDURE sp_load_dim_assignment()
BEGIN
    -- Truncate existing data safely
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE dim_assignment;
    SET FOREIGN_KEY_CHECKS = 1;

    INSERT INTO dim_assignment (
        assignment_id, employee_sk, project_sk, role_on_project, allocation_ratio, assigned_date, end_date
    )
    SELECT a.assignment_id, de.employee_sk, dp.project_sk, a.role_on_project, a.allocation_ratio, a.assigned_date, a.end_date
    FROM assignments a
    INNER JOIN dim_employee de ON de.employee_id = a.employee_id 
        AND a.assigned_date >= de.effective_start_date 
        AND a.assigned_date <= de.effective_end_date
    INNER JOIN dim_project dp ON dp.project_id = a.project_id;
END$$
DELIMITER ;


-- ==============================================================================
-- 6. FACT_PERFORMANCE_REVIEWS STORED PROCEDURE
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_load_fact_performance_reviews;
DELIMITER $$
CREATE PROCEDURE sp_load_fact_performance_reviews()
BEGIN
    -- Truncate existing data safely
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE fact_performance_reviews;
    SET FOREIGN_KEY_CHECKS = 1;

    INSERT INTO fact_performance_reviews (employee_sk, department_sk, project_sk, date_sk, review_id, performance_rating)
    SELECT de.employee_sk, dd.department_sk, dp.project_sk, dt.date_sk, r.review_id, r.performance_rating
    FROM reviews r
    INNER JOIN dim_employee de ON de.employee_id = r.employee_id AND r.review_date >= de.effective_start_date AND r.review_date <= de.effective_end_date
    INNER JOIN dim_department dd ON dd.department_name = de.department_name
    INNER JOIN dim_date dt ON dt.full_date = r.review_date
    LEFT JOIN (
        SELECT review_id, project_id FROM (
            SELECT r2.review_id, a.project_id, ROW_NUMBER() OVER (PARTITION BY r2.review_id ORDER BY a.assigned_date DESC, a.assignment_id DESC) AS rnk
            FROM reviews r2
            LEFT JOIN assignments a ON a.employee_id = r2.employee_id AND r2.review_date >= a.assigned_date AND (a.end_date IS NULL OR r2.review_date <= a.end_date)
        ) ranked WHERE rnk = 1
    ) va ON va.review_id = r.review_id
    LEFT JOIN dim_project dp ON dp.project_id = va.project_id;
END$$
DELIMITER ;


-- ==============================================================================
-- 7. MASTER STORED PROCEDURE (Calls all the above in exact dependency order)
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_run_full_etl_load;
DELIMITER $$
CREATE PROCEDURE sp_run_full_etl_load()
BEGIN
    -- Step 1: Core Dimensions
    CALL sp_load_dim_department();
    CALL sp_load_dim_project();
    CALL sp_load_dim_date();
    
    -- Step 2: Complex SCD2 Dimension
    CALL sp_load_dim_employee();
    
    -- Step 3: Dependent Tables (Rely on employee_sk)
    CALL sp_load_dim_assignment();
    CALL sp_load_fact_performance_reviews();
END$$
DELIMITER ;

-- ==============================================================================
-- EXECUTE THE MASTER PIPELINE
-- ==============================================================================
CALL sp_run_full_etl_load();
