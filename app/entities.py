"""
entities.py
───────────
Entity classes: Employee, Project, Review
Each class encapsulates attributes and domain behaviors.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Employee:
    """Represents an employee in the OLTP system."""
    employee_number:  int
    first_name:       str
    last_name:        str
    email:            str
    department_id:    int
    job_role:         str
    job_level:        int  = 1
    monthly_income:   float = 0.0
    gender:           str  = ""
    marital_status:   str  = ""
    education_field:  str  = ""
    attrition:        str  = "No"
    age:              int  = 0
    distance_from_home: int = 0
    years_at_company: int  = 0
    manager_id:       Optional[int] = None

    # ── computed properties ─────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    # ── behaviours ──────────────────────────────────────────
    def promote(self, new_role: str, new_level: int = None, new_income: float = None):
        """Promote the employee. Triggers SCD2 in the warehouse."""
        self.job_role = new_role
        if new_level  is not None: self.job_level = new_level
        if new_income is not None: self.monthly_income = new_income

    def to_dict(self) -> dict:
        return {
            "employee_number":    self.employee_number,
            "first_name":         self.first_name,
            "last_name":          self.last_name,
            "email":              self.email,
            "department_id":      self.department_id,
            "job_role":           self.job_role,
            "job_level":          self.job_level,
            "monthly_income":     self.monthly_income,
            "gender":             self.gender,
            "marital_status":     self.marital_status,
            "education_field":    self.education_field,
            "attrition":          self.attrition,
            "age":                self.age,
            "distance_from_home": self.distance_from_home,
            "years_at_company":   self.years_at_company,
            "manager_id":         self.manager_id,
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