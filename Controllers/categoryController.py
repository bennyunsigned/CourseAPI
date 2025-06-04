from fastapi import APIRouter, Depends
from Models.categoryModel import CategoryRequest, CategoryResponse, CategoryUpdateRequest
from Services.categoryService import (
    create_category, get_all_categories, get_category_by_id, update_category, delete_category
    
)
from Utils.JWT import authenticate_request

category_router = APIRouter()

@category_router.post("/", response_model=CategoryResponse)
def create_category_endpoint(category_data: CategoryRequest, claims: dict = Depends(authenticate_request)):
    user_id = claims["id"]
    return create_category(category_data, user_id)

@category_router.get("/", response_model=list[CategoryResponse])
def get_all_category_endpoint(claims: dict = Depends(authenticate_request)):
    return get_all_categories()

@category_router.get("/{category_id}", response_model=CategoryResponse)
def get_category_by_id_endpoint(category_id: int, claims: dict = Depends(authenticate_request)):
    return get_category_by_id(category_id)

@category_router.put("/{category_id}")
def update_category_endpoint(category_id: int, category_data: CategoryUpdateRequest, claims: dict = Depends(authenticate_request)):
    user_id = claims["id"]
    return {"message": update_category(category_id, category_data, user_id)}

@category_router.delete("/{category_id}")
def delete_category_endpoint(category_id: int, claims: dict = Depends(authenticate_request)):
    return {"message": delete_category(category_id)}


