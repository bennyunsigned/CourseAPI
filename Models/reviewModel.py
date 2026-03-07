from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReviewCreate(BaseModel):
    userId: int
    courseId: Optional[int] = None
    bundleId: Optional[int] = None
    productId: Optional[int] = None
    rating: int  # 1 to 5
    reviewText: Optional[str] = None

class ReviewResponse(BaseModel):
    reviewId: int
    userId: int
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    userPhone: Optional[str] = None
    userImage: Optional[str] = None
    courseId: Optional[int] = None
    bundleId: Optional[int] = None
    productId: Optional[int] = None
    rating: int
    reviewText: Optional[str] = None
    createdAt: datetime
    status: str
