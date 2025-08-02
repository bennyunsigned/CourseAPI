from pydantic import BaseModel
from typing import List, Optional

class VideoModel(BaseModel):
    VideoId: int
    VideoTitle: str
    VideoUrl: str
    DurationInSeconds: int
    VideoSequenceNo: int

class ModuleModel(BaseModel):
    ModuleId: int
    ModuleName: str
    ModuleDescription: str
    ModuleSequenceNo: int
    TotalDurationPerModule: int
    Videos: List[VideoModel]

class CourseContentModel(BaseModel):
    CourseId: int
    CourseName: str
    CourseDescription: str
    CourseInfo: Optional[str]
    CourseLanguage: Optional[str]
    BannerImage: Optional[str]  # base64 string
    Author: Optional[str]
    Rating: Optional[float]  # <-- Change here
    ActualPrice: float
    DiscountedPrice: float
    IsPremium: int
    IsBestSeller: int
    VideoPath: Optional[str]
    IsPublic: int
    TotalDurationPerCourse: int
    Modules: List[ModuleModel]