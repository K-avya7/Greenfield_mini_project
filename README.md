# Enterprise Employee Analytics & Data Warehouse 

Purpose

This repository implements an OOP Python application and supporting SQL scripts to synthesize employee data, implement SCD Type 2 history, load into OLTP/OLAP schemas (MySQL), and expose an interactive Streamlit UI for onboarding and analytics — aligned to the enterprise problem statement provided.

Quick commands

- Create & activate venv (Windows PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

- Create a .env file 
  example env
  DB_HOST=localhost
  DB_USER=<your_username>
  DB_PASSWORD=<your_password>
  DB_NAME=employee_analytics_dw2

- Install dependencies:
  pip install -r [requirements.txt]

- Generate synthetic SCD2 data (example):
  python [employee_data_synthesizer_scd2.py]

- Run Streamlit UI locally:
  streamlit run [app/streamlit_app.py]

Core deliverables 

- Data synthesizer that scales the IBM HR dataset and generates SCD Type 2 histories.
- Normalized OLTP schema and a Star Schema (OLAP) with surrogate keys and SCD Type 2 support for Dim_Employee.
- SQL scripts (DDL/DML/Stored Procedures) for ETL between OLTP and OLAP.
- OOP Python backend (DB manager, entity classes, manager/DAL classes).
- Streamlit application for data entry and analytics dashboards suitable for deployment to Streamlit Community Cloud.

Repository files 

- [app/__init__.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/app/__init__.py) — package marker for the app module.
- [app/db_manager.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/app/db_manager.py) — DatabaseConnection/utility classes (Singleton pattern recommended).
- [app/entities.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/app/entities.py) — OOP entity models (Employee, Project, Review).
- [app/managers.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/app/managers.py) — Data Access Layer (EmployeeManager, AnalyticsManager) for CRUD and ETL logic.
- [app/streamlit_app.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/app/streamlit_app.py) — Streamlit UI for onboarding and dashboards.
- [employee_data_synthesizer_scd2.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/employee_data_synthesizer_scd2.py) — Synthesizer using pandas + Faker to scale and create SCD2 histories.
- [main.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/main.py) — project entry / demo runner that wires components together.
- [test.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/test.py) — quick smoke/demo checks.
- [requirements.txt](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/requirements.txt) — Python dependencies (pandas, faker, mysql-connector or pymysql, streamlit, etc.).
- [data/WA_Fn-UseC_-HR-Employee-Attrition.csv](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/data/WA_Fn-UseC_-HR-Employee-Attrition.csv) — base IBM HR snapshot used for synthesis.
- [data/employee_scd2_130k.csv](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/data/employee_scd2_130k.csv) — example synthesized SCD2 dataset (large-volume sample).
- [employee_data_synthesizer_scd2.py](C:/Users/KavyaAgrawal/Desktop/greenfield%20mini%20porject.worktrees/add-project-readme/employee_data_synthesizer_scd2.py) — (duplicate listing) primary synth script.
- [mysql scripts/oltp to olap.sql](</C:/Users/KavyaAgrawal/Desktop/greenfield mini porject.worktrees/add-project-readme/mysql scripts/oltp to olap.sql>) — SQL to transform OLTP rows into OLAP star schema (ETL logic).
- [mysql scripts/staging_to_oltp.sql](</C:/Users/KavyaAgrawal/Desktop/greenfield mini porject.worktrees/add-project-readme/mysql scripts/staging_to_oltp.sql>) — SQL for staging → OLTP loading and initial transforms.


