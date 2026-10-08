from pydantic import BaseModel, Field
from typing import Optional


class StudentProfile(BaseModel):
    name: str
    email: str

    education_level: Optional[str] = None
    course: Optional[str] = None

    category: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    year: Optional[str] = None

    marks: Optional[float] = Field(default=None, ge=0)
    family_income: Optional[float] = Field(default=None, ge=0)