from pydantic import BaseModel
from typing import Optional

class ModuleVideoRequest(BaseModel):
    course_id: int
    module_id: int
    video_title: str
    video_url: Optional[str] = None
    duration_in_seconds: Optional[str] = None
    sequence_no: Optional[int] = None
    created_by: str

class ModuleVideoResponse(BaseModel):
    video_id: int
    course_id: int
    module_id: int
    video_title: str
    video_url: Optional[str] = None
    duration_in_seconds: Optional[str] = None
    sequence_no: Optional[int] = None
    created_by: str
    created_at: str
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None
    status: str