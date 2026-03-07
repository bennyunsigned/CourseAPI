from pydantic import BaseModel, EmailStr
from typing import Optional

class ProductPaymentRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    product_id: int
    amount: Optional[float] = None
    payment_id: str

class BundlePaymentRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    bundle_id: int
    amount: Optional[float] = None
    payment_id: str

class PaymentResponse(BaseModel):
    message: str
    user_id: int
    payment_record_id: int
