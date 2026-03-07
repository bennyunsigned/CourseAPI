from pydantic import BaseModel
from typing import Optional

class ProductRequest(BaseModel):
    product_name: str
    product_price: float
    product_discount_price: float
    product_description: Optional[str]
    product_content: Optional[str]
    product_image: Optional[str]
    is_active: Optional[bool] = True
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

class ProductAttachmentRequest(BaseModel):
    file_name: Optional[str]
    file_url: str
    file_type: Optional[str]

class ProductAttachmentResponse(BaseModel):
    attachment_id: int
    product_id: int
    file_name: Optional[str]
    file_url: str
    file_type: Optional[str]
    uploaded_on: str

class ProductResponse(BaseModel):
    product_id: int
    product_name: str
    product_price: float
    product_discount_price: float
    product_description: Optional[str]
    product_content: Optional[str]
    product_image: Optional[str]
    is_active: bool
    created_on: str
    updated_on: str
    attachments: Optional[list[ProductAttachmentResponse]] = []
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

class ProductUpdateRequest(BaseModel):
    product_name: Optional[str]
    product_price: Optional[float]
    product_discount_price: Optional[float]
    product_description: Optional[str]
    product_content: Optional[str]
    product_image: Optional[str]
    is_active: Optional[bool]
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
