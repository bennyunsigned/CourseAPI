from fastapi import APIRouter, Depends
from Models.courseModuleModel import CourseModuleRequest, CourseModuleResponse, CourseModuleUpdateRequest
from Models.moduleVideoModel import ModuleVideoRequest, ModuleVideoResponse
from Services.courseModuleService import (
    create_module, get_all_modules, get_module_by_id, update_module, delete_module
)
from Services.courseService import (
    insert_module_video, get_module_videos, delete_module_video
)
from Utils.JWT import authenticate_request

course_module_router = APIRouter()

@course_module_router.post("/", response_model=CourseModuleResponse)
def create_module_endpoint(module_data: CourseModuleRequest, claims: dict = Depends(authenticate_request)):
    user_id = claims["id"]
    return create_module(module_data, user_id)

@course_module_router.get("/", response_model=list[CourseModuleResponse])
def get_all_modules_endpoint(course_id: int, claims: dict = Depends(authenticate_request)):
    return get_all_modules(course_id)

@course_module_router.get("/{module_id}", response_model=CourseModuleResponse)
def get_module_by_id_endpoint(module_id: int, claims: dict = Depends(authenticate_request)):
    return get_module_by_id(module_id)

@course_module_router.put("/{module_id}")
def update_module_endpoint(module_id: int, module_data: CourseModuleUpdateRequest, claims: dict = Depends(authenticate_request)):
    user_id = claims["id"]
    return {"message": update_module(module_id, module_data, user_id)}

@course_module_router.delete("/{module_id}")
def delete_module_endpoint(module_id: int, claims: dict = Depends(authenticate_request)):
    return {"message": delete_module(module_id)}

# ---------------- Module Video Endpoints ----------------

@course_module_router.post("/moduleVideo/", response_model=ModuleVideoResponse)
def insert_module_video_endpoint(video_data: ModuleVideoRequest, claims: dict = Depends(authenticate_request)):
    return insert_module_video(video_data)

@course_module_router.get("/moduleVideo/", response_model=list[ModuleVideoResponse])
def get_module_videos_endpoint(course_id: int, module_id: int, claims: dict = Depends(authenticate_request)):
    return get_module_videos(course_id, module_id)

@course_module_router.delete("/moduleVideo/{video_id}")
def delete_module_video_endpoint(video_id: int, claims: dict = Depends(authenticate_request)):
    return {"message": delete_module_video(video_id)}


