import pandas as pd
import numpy as np
from faker import Faker

# Initialize Faker generator
fake = Faker()

# 1. Load the original base dataset
base_df = pd.read_csv('WA_Fn-UseC_-HR-Employee-Attrition.csv')

TARGET_ROWS = 100000

# 2. Resample base data to reach 100,000+ rows with replacement
scaled_df = base_df.sample(n=TARGET_ROWS, replace=True).reset_index(drop=True)

# 3. Overwrite unique identifiers using Faker
print("Generating synthetic identities...")
scaled_df['EmployeeNumber'] = range(100001, 100001 + TARGET_ROWS)
scaled_df['EmployeeName'] = [fake.name() for _ in range(TARGET_ROWS)]
scaled_df['Email'] = [fake.company_email() for _ in range(TARGET_ROWS)]

# 4. Inject subtle variations so data isn't exact duplicated rows
# Apply ±5% variation to MonthlyIncome
income_noise = np.random.uniform(-0.05, 0.05, size=TARGET_ROWS)
scaled_df['MonthlyIncome'] = (scaled_df['MonthlyIncome'] * (1 + income_noise)).round().astype(int)

# 5. Export the scaled dataset
output_filename = 'scaled_employee_data.csv'
scaled_df.to_csv(output_filename, index=False)
print(f"Success! Exported {len(scaled_df)} rows to '{output_filename}'.")