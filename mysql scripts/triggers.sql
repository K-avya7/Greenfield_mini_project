-- ==============================================================================
-- DATABASE TRIGGERS: OLTP to OLAP Syncing
-- ==============================================================================
-- These triggers automatically sync new insertions from the live operational 
-- databases (`projects`, `assignments`) directly into the analytical 
-- Star Schema (`dim_project`, `dim_assignment`).
-- ==============================================================================

DELIMITER $$

-- 1. Trigger for Projects
-- Fires automatically after a new project is created in the Streamlit UI.
DROP TRIGGER IF EXISTS trg_after_insert_project$$

CREATE TRIGGER trg_after_insert_project
AFTER INSERT ON projects
FOR EACH ROW
BEGIN
    INSERT INTO dim_project (
        project_id, 
        project_name, 
        start_date, 
        end_date, 
        status
    ) VALUES (
        NEW.project_id, 
        NEW.project_name, 
        NEW.start_date, 
        NEW.end_date, 
        NEW.status
    );
END$$


-- 2. Trigger for Assignments
-- Fires automatically after an employee is assigned to a project.
-- It dynamically looks up the correct Surrogate Keys (SKs) for the 
-- Employee (ensuring they are the active SCD2 record) and the Project.
DROP TRIGGER IF EXISTS trg_after_insert_assignment$$

CREATE TRIGGER trg_after_insert_assignment
AFTER INSERT ON assignments
FOR EACH ROW
BEGIN
    DECLARE v_emp_sk INT;
    DECLARE v_proj_sk INT;

    -- Lookup the Active Surrogate Key for the Employee (SCD Type 2)
    SELECT employee_sk INTO v_emp_sk 
    FROM dim_employee 
    WHERE employee_id = NEW.employee_id 
      AND is_current = 1 
    LIMIT 1;

    -- Lookup the Surrogate Key for the Project
    SELECT project_sk INTO v_proj_sk 
    FROM dim_project 
    WHERE project_id = NEW.project_id 
    ORDER BY project_sk DESC 
    LIMIT 1;

    -- Insert into the Dimensional Table
    IF v_emp_sk IS NOT NULL AND v_proj_sk IS NOT NULL THEN
        INSERT INTO dim_assignment (
            assignment_id, 
            employee_sk, 
            project_sk, 
            role_on_project, 
            allocation_ratio, 
            assigned_date, 
            end_date
        ) VALUES (
            NEW.assignment_id,
            v_emp_sk,
            v_proj_sk,
            NEW.role_on_project,
            NEW.allocation_ratio,
            NEW.assigned_date,
            NEW.end_date
        );
    END IF;
END$$

DELIMITER ;
