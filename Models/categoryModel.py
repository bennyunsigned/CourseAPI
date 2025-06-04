from pydantic import BaseModel
from typing import Optional

class CategoryRequest(BaseModel):    
    CategoryName: Optional[str]   
    

class CategoryResponse(BaseModel):
    CategoryId: int
    CategoryName: str    
    CreatedBy: str
    Status: str

class CategoryUpdateRequest(BaseModel):
    CategoryName: str
    
    