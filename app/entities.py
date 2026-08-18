"""
entities.py
───────────
Entity classes: Employee, Project, Review
Each class encapsulates attributes and domain behaviors.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import math


@dataclass
class Employee:
    """Represents an employee in the OLTP system."""
    # ── required identity fields ─────────────────────────────
    employee_number:  int
    first_name:       str
    last_name:        str
    email:            str
    department_id:    int
    job_role:         str

    # ── role / compensation ──────────────────────────────────
    job_level:              int   = 1
    monthly_income:         float = 0.0

    # ── demographics ─────────────────────────────────────────
    gender:           str  = ""
    marital_status:   str  = ""
    education:        int  = 3          # 1=Below College…5=Doctor
    education_field:  str  = ""
    age:              int  = 0
    distance_from_home: int = 0
    over_18:          str  = "Y"

    # ── work history / tenure ────────────────────────────────
    num_companies_worked:       int = 0
    total_working_years:        int = 0
    years_at_company:           int = 0
    years_in_current_role:      int = 0
    years_since_last_promotion: int = 0
    years_with_curr_manager:    int = 0

    # ── work style ───────────────────────────────────────────
    attrition:        str  = "No"
    business_travel:  str  = "Non-Travel"
    over_time:        str  = "No"
    stock_option_level: int = 0

    # ── performance / satisfaction ───────────────────────────
    percent_salary_hike:       int = 0
    environment_satisfaction:  int = 3   # 1-4
    job_involvement:           int = 3   # 1-4
    job_satisfaction:          int = 3   # 1-4
    relationship_satisfaction: int = 3   # 1-4
    work_life_balance:         int = 3   # 1-4
    training_times_last_year:  int = 0

    # ── administrative (fixed / auto-calculated) ─────────────
    employee_count:  int = 1
    standard_hours:  int = 80

    # ── manager ──────────────────────────────────────────────
    manager_id: Optional[int] = None

    # ── computed properties ──────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def employee_name(self) -> str:
        """Concatenated name for the employee_name column."""
        return f"{self.first_name} {self.last_name}"

    @property
    def daily_rate(self) -> int:
        """Derived from monthly_income ÷ 22 working days."""
        return max(1, round(self.monthly_income / 22))

    @property
    def hourly_rate(self) -> int:
        """Derived from daily_rate ÷ 8 hours."""
        return max(1, round(self.daily_rate / 8))

    @property
    def monthly_rate(self) -> int:
        """Monthly rate — same as monthly income for new hires."""
        return round(self.monthly_income)

    # ── behaviours ───────────────────────────────────────────
    def promote(self, new_role: str, new_level: int = None, new_income: float = None):
        """Promote the employee. Triggers SCD2 in the warehouse."""
        self.job_role = new_role
        if new_level  is not None: self.job_level = new_level
        if new_income is not None: self.monthly_income = new_income

    def to_dict(self) -> dict:
        return {
            "employee_number":           self.employee_number,
            "employee_name":             self.employee_name,
            "first_name":                self.first_name,
            "last_name":                 self.last_name,
            "email":                     self.email,
            "department_id":             self.department_id,
            "job_role":                  self.job_role,
            "job_level":                 self.job_level,
            "monthly_income":            self.monthly_income,
            "daily_rate":                self.daily_rate,
            "hourly_rate":               self.hourly_rate,
            "monthly_rate":              self.monthly_rate,
            "gender":                    self.gender,
            "marital_status":            self.marital_status,
            "education":                 self.education,
            "education_field":           self.education_field,
            "age":                       self.age,
            "distance_from_home":        self.distance_from_home,
            "over_18":                   self.over_18,
            "num_companies_worked":      self.num_companies_worked,
            "total_working_years":       self.total_working_years,
            "years_at_company":          self.years_at_company,
            "years_in_current_role":     self.years_in_current_role,
            "years_since_last_promotion":self.years_since_last_promotion,
            "years_with_curr_manager":   self.years_with_curr_manager,
            "attrition":                 self.attrition,
            "business_travel":           self.business_travel,
            "over_time":                 self.over_time,
            "stock_option_level":        self.stock_option_level,
            "percent_salary_hike":       self.percent_salary_hike,
            "environment_satisfaction":  self.environment_satisfaction,
            "job_involvement":           self.job_involvement,
            "job_satisfaction":          self.job_satisfaction,
            "relationship_satisfaction": self.relationship_satisfaction,
            "work_life_balance":         self.work_life_balance,
            "training_times_last_year":  self.training_times_last_year,
            "employee_count":            self.employee_count,
            "standard_hours":            self.standard_hours,
            "manager_id":                self.manager_id,
        }

    def __repr__(self):
        return f"Employee({self.full_name}, {self.job_role}, Lvl {self.job_level})"


@dataclass
class Project:
    """Represents a project."""
    project_name:  str
    department_id: int
    status:        str        = "Active"
    start_date:    date       = field(default_factory=date.today)
    end_date:      Optional[date] = None

    def is_active(self) -> bool:
        return self.status == "Active"

    def to_dict(self) -> dict:
        return {
            "project_name":  self.project_name,
            "department_id": self.department_id,
            "status":        self.status,
            "start_date":    str(self.start_date),
            "end_date":      str(self.end_date) if self.end_date else None,
        }

    def __repr__(self):
        return f"Project({self.project_name}, {self.status})"


@dataclass
class Review:
    """Represents a performance review event."""
    employee_id:        int
    performance_rating: int          # 1-5
    review_date:        date  = field(default_factory=date.today)
    reviewer_id:        Optional[int] = None

    def is_high_performer(self) -> bool:
        return self.performance_rating >= 4

    def to_dict(self) -> dict:
        return {
            "employee_id":        self.employee_id,
            "performance_rating": self.performance_rating,
            "review_date":        str(self.review_date),
            "reviewer_id":        self.reviewer_id,
        }

    def __repr__(self):
        return f"Review(emp={self.employee_id}, rating={self.performance_rating}/5)"