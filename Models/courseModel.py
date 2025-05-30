from pydantic import BaseModel
from typing import Optional

class CourseRequest(BaseModel):
    course_name: str
    course_description: Optional[str]
    video_path: Optional[str]
    actual_price: float
    discounted_price: float
    discount_percentage: float
    is_public: bool
    

class CourseResponse(BaseModel):
    course_id: int
    course_name: str
    course_description: Optional[str]
    video_path: Optional[str]
    actual_price: float
    discounted_price: float
    discount_percentage: float
    is_public: bool
    created_by: str
    status: str

class CourseUpdateRequest(BaseModel):
    course_name: Optional[str]
    course_description: Optional[str]
    video_path: Optional[str]
    actual_price: Optional[float]
    discounted_price: Optional[float]
    discount_percentage: Optional[float]
    is_public: Optional[bool]
    