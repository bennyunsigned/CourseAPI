from fastapi import APIRouter, HTTPException, Depends, Query
from Models.reviewModel import ReviewCreate, ReviewResponse
from Services.reviewService import add_review, get_top_reviews
from Utils.JWT import authenticate_request
from typing import List, Optional

review_router = APIRouter()

@review_router.post("/", response_model=dict)
def create_review(review: ReviewCreate, current_user: dict = Depends(authenticate_request)):
    """
    Store a new customer review.
    Requires authentication.
    """
    try:
        # Override userId from token for security
        review.userId = int(current_user.get("id"))
        review_id = add_review(review)
        return {"message": "Review added successfully", "reviewId": review_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@review_router.get("/top-30", response_model=List[ReviewResponse])
def fetch_top_reviews(
    courseId: Optional[int] = Query(None),
    bundleId: Optional[int] = Query(None),
    productId: Optional[int] = Query(None)
):
    """
    Retrieve the latest top 30 customer reviews.
    Can be filtered by courseId, bundleId, or productId.
    """
    try:
        reviews = get_top_reviews(limit=30, course_id=courseId, bundle_id=bundleId, product_id=productId)
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
