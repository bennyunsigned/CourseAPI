from pydantic import BaseModel
from typing import Optional

class CourseModuleRequest(BaseModel):
    CourseId: int
    ModuleName: str
    ModuleDescription: Optional[str]
    SequenceNo: Optional[str]
    Status: str = "Active"

class CourseModuleResponse(BaseModel):
    ModuleId: int
    CourseId: int
    ModuleName: str
    ModuleDescription: Optional[str]
    SequenceNo: Optional[str]
    Status: str = "Active"
    CreatedBy: str
    CourseName: Optional[str] = None
    

class CourseModuleUpdateRequest(BaseModel):
    CourseId: int
    ModuleName: Optional[str]
    ModuleDescription: Optional[str]
    SequenceNo: Optional[str]
    Status: Optional[str]
