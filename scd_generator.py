import pandas as pd
import numpy as np

class SCD2DataEngine:
    """Engine to simulate historical career changes and output SCD Type 2 compliant datasets."""
    
    def __init__(self, input_filename: str = 'scaled_employee_data.csv', output_filename: str = 'scd2_employee_history.csv'):
        self.input_filename = input_filename
        self.output_filename = output_filename
        self.df = None

    def load_base_data(self):
        print(f"Loading '{self.input_filename}'...")
        self.df = pd.read_csv(self.input_filename)

    def apply_scd2_history(self, change_ratio: float = 0.25):
        """Simulates historical updates for 25% of employees."""
        # 1. Set base active state (v1)
        self.df['EffectiveDate'] = '2022-01-01'
        self.df['EndDate'] = None
        self.df['EndDate'] = self.df['EndDate'].astype('object')
        self.df['IsCurrent'] = 1

        # 2. Pick 25% of employees for promotions/salary boosts 2 years later
        num_changes = int(len(self.df) * change_ratio)
        change_indices = np.random.choice(self.df.index, size=num_changes, replace=False)
        
        print(f"Generating historical updates for {num_changes:,} employees...")
        
        # Copy selected rows to serve as updated active states (v2)
        v2_records = self.df.loc[change_indices].copy()

        # Mark initial state (v1) as expired
        self.df.loc[change_indices, 'EndDate'] = '2024-01-01'
        self.df.loc[change_indices, 'IsCurrent'] = 0

        # Update metadata for new active state (v2) starting 2024-01-01
        v2_records['EffectiveDate'] = '2024-01-01'
        v2_records['EndDate'] = None
        v2_records['IsCurrent'] = 1
        
        # Apply salary raise (10-20%) and increment job level
        salary_boost = np.random.uniform(1.10, 1.20, size=len(v2_records))
        v2_records['MonthlyIncome'] = (v2_records['MonthlyIncome'] * salary_boost).round().astype(int)
        v2_records['JobLevel'] = np.minimum(v2_records['JobLevel'] + 1, 5)

        # 3. Combine original and updated records
        full_history = pd.concat([self.df, v2_records], ignore_index=True)
        full_history.sort_values(by=['EmployeeNumber', 'EffectiveDate'], inplace=True)
        
        # 4. Create Surrogate Primary Key (SCD_SK)
        full_history.insert(0, 'SCD_SK', range(1, len(full_history) + 1))
        
        self.df = full_history

    def export(self):
        self.df.to_csv(self.output_filename, index=False)
        print(f"Done! Saved {len(self.df):,} total rows to '{self.output_filename}'.")

    def run(self):
        self.load_base_data()
        self.apply_scd2_history()
        self.export()

if __name__ == '__main__':
    engine = SCD2DataEngine()
    engine.run()