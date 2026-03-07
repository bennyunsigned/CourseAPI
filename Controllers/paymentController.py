from fastapi import APIRouter, HTTPException
from Models.paymentModel import ProductPaymentRequest, BundlePaymentRequest, PaymentResponse
from Services.paymentService import process_product_payment, process_bundle_payment

payment_router = APIRouter()

@payment_router.post("/product", response_model=PaymentResponse, name="Process Product Guest Payment")
def product_payment_endpoint(data: ProductPaymentRequest):
    try:
        return process_product_payment(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@payment_router.post("/bundle", response_model=PaymentResponse, name="Process Bundle Guest Payment")
def bundle_payment_endpoint(data: BundlePaymentRequest):
    try:
        return process_bundle_payment(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
