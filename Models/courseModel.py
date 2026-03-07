from pydantic import BaseModel
from typing import Optional

class CourseRequest(BaseModel):
    category_id:int
    course_name: str
    course_description: Optional[str]
    course_info: Optional[str]
    course_language: Optional[str]
    banner_image: Optional[str]
    author: Optional[str]
    rating: Optional[float]
    actual_price: float
    discounted_price: float
    is_premium: Optional[bool]
    is_best_seller: Optional[bool]
    video_path: Optional[str]
    is_public: bool
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

class CourseResponse(BaseModel):
    category_id:int
    course_id: int
    course_name: str
    course_description: Optional[str]
    course_info: Optional[str]
    course_language: Optional[str]
    banner_image: Optional[str]
    author: Optional[str]
    rating: Optional[float]
    actual_price: float
    discounted_price: float
    is_premium: Optional[bool]
    is_best_seller: Optional[bool]
    video_path: Optional[str]
    is_public: bool
    created_by: str
    status: str
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

class CourseUpdateRequest(BaseModel):
    category_id:int
    course_name: Optional[str]
    course_description: Optional[str]
    course_info: Optional[str]
    course_language: Optional[str]
    banner_image: Optional[str]
    author: Optional[str]
    rating: Optional[float]
    actual_price: Optional[float]
    discounted_price: Optional[float]
    is_premium: Optional[bool]
    is_best_seller: Optional[bool]
    video_path: Optional[str]
    is_public: Optional[bool]
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
