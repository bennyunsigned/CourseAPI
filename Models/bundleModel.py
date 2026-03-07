from pydantic import BaseModel
from typing import Optional, List
from Models.productModel import ProductResponse

class BundleRequest(BaseModel):
    bundle_name: str
    bundle_description: Optional[str]
    bundle_price: float
    bundle_discount_price: float
    is_active: Optional[bool] = True
    product_ids: List[int]
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

class BundleResponse(BaseModel):
    bundle_id: int
    bundle_name: str
    bundle_description: Optional[str]
    bundle_price: float
    bundle_discount_price: float
    is_active: bool
    created_on: str
    updated_on: str
    products: Optional[List[ProductResponse]] = []
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

class BundleUpdateRequest(BaseModel):
    bundle_name: Optional[str]
    bundle_description: Optional[str]
    bundle_price: Optional[float]
    bundle_discount_price: Optional[float]
    is_active: Optional[bool]
    product_ids: Optional[List[int]]
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
