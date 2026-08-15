class Employee:
    def __init__(self, employee_number: int, first_name: str, last_name: str, email: str, department_id: int = None, job_title: str = "Staff"):
        self.employee_number = employee_number
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.department_id = department_id
        self.job_title = job_title

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def promote(self, new_title: str):
        self.job_title = new_title


class Project:
    def __init__(self, project_name: str, budget: float, status: str = "Planning", project_id: int = None):
        self.project_id = project_id
        self.project_name = project_name
        self.budget = budget
        self.status = status

    def is_active(self) -> bool:
        return self.status == "Active"


class Review:
    def __init__(self, employee_number: int, reviewer_id: int, performance_rating: int, comments: str = "", review_id: int = None):
        self.review_id = review_id
        self.employee_number = employee_number
        self.reviewer_id = reviewer_id
        self.performance_rating = performance_rating
        self.comments = comments

    def is_high_performer(self) -> bool:
        return self.performance_rating >= 4