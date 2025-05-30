from fastapi import APIRouter, Depends
from Models.courseModel import CourseRequest, CourseResponse, CourseUpdateRequest
from Services.courseService import (
    create_course,
    get_all_courses,
    get_course_by_id,
    update_course,
    delete_course,
)
from Utils.JWT import authenticate_request

course_router = APIRouter()

@course_router.post("/", response_model=CourseResponse, name="Create a Course")
def create_course_endpoint(
    course_data: CourseRequest, claims: dict = Depends(authenticate_request)
):
    user_id = claims["id"]
    return create_course(course_data, user_id)

@course_router.get("/", response_model=list[CourseResponse], name="Get All Courses")
def get_all_courses_endpoint(claims: dict = Depends(authenticate_request)):
    return get_all_courses()

@course_router.get("/{course_id}", response_model=CourseResponse, name="Get Course by ID")
def get_course_by_id_endpoint(course_id: int, claims: dict = Depends(authenticate_request)):
    
    return get_course_by_id(course_id)

@course_router.put("/{course_id}", name="Update a Course")
def update_course_endpoint(
    course_id: int, course_data: CourseUpdateRequest, claims: dict = Depends(authenticate_request)
):
    user_id = claims["id"]
    return {"message": update_course(course_id, course_data, user_id)}

@course_router.delete("/{course_id}", name="Delete a Course")
def delete_course_endpoint(course_id: int, claims: dict = Depends(authenticate_request)):
    return {"message": delete_course(course_id)}