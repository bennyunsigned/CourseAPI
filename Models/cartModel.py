from pydantic import BaseModel
from typing import Optional


class AddToCartRequest(BaseModel):
    course_id: int


class RemoveFromCartRequest(BaseModel):
    course_id: int


class CartItemResponse(BaseModel):
    CartId: int
    UserId: int
    CourseId: int
    CourseName: Optional[str]
    BannerImage: Optional[str]
    ActualPrice: Optional[float]
    DiscountedPrice: Optional[float]
    CreatedAt: Optional[str]
    Status: Optional[str]
