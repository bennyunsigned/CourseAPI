from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

from Services.populateReviewsService import (
    get_dummy_users,
    clean_dummy_reviews,
    insert_dummy_users,
    get_all_items,
    get_item_reviewers,
    insert_reviews
)

populate_router = APIRouter()

class DummyUserRequest(BaseModel):
    domain: str

class CleanReviewsRequest(BaseModel):
    userIds: List[int]

class NewUser(BaseModel):
    name: str
    email: str
    password: str
    phone: str

class InsertUsersRequest(BaseModel):
    users: List[NewUser]

class ItemReviewersRequest(BaseModel):
    colName: str
    itemId: int

class ReviewData(BaseModel):
    userId: int
    colName: str
    itemId: int
    rating: int
    reviewText: str

class InsertReviewsRequest(BaseModel):
    reviews: List[ReviewData]


@populate_router.get("/dummy-users")
def fetch_dummy_users(domain: str):
    try:
        users = get_dummy_users(domain)
        return {"userIds": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@populate_router.post("/clean-reviews")
def clean_reviews(req: CleanReviewsRequest):
    try:
        deleted_count = clean_dummy_reviews(req.userIds)
        return {"deleted": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@populate_router.post("/dummy-users")
def add_dummy_users(req: InsertUsersRequest):
    try:
        users_dict = [u.dict() for u in req.users]
        inserted = insert_dummy_users(users_dict)
        return {"inserted": inserted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@populate_router.get("/items")
def fetch_items():
    try:
        items = get_all_items()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@populate_router.get("/item-reviewers")
def fetch_item_reviewers(colName: str, itemId: int):
    try:
        user_ids = get_item_reviewers(colName, itemId)
        return {"userIds": user_ids}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@populate_router.post("/reviews")
def add_reviews(req: InsertReviewsRequest):
    try:
        reviews_dict = [r.dict() for r in req.reviews]
        inserted = insert_reviews(reviews_dict)
        return {"inserted": inserted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
