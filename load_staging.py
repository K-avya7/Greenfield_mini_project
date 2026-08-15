import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote

DB_USER = "root"
DB_PASS = "V@mpire3053"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "hr_staging"

def load_csv_to_staging():
    print("Reading scd2_employee_history.csv...")
    df = pd.read_csv("scd2_employee_history.csv")
    # URL-encode the password to handle special characters
    encoded_password = quote(DB_PASS, safe='')
    connection_url = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print(f"Connecting to {DB_HOST}:{DB_PORT}...")
    engine = create_engine(connection_url, echo=False)
    print(f"Uploading {len(df):,} rows into hr_staging.stg_employee_history...")
    df.to_sql(
        name="stg_employee_history",
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=10000
    )
    print("Bulk load complete!")

if __name__ == "__main__":
    load_csv_to_staging()
    df.to_sql(
        name="stg_employee_history",
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=10000
    )
    print("Bulk load complete!")

if __name__ == "__main__":
    load_csv_to_staging()