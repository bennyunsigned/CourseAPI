from fastapi import APIRouter, Depends
from Services.productService import (
    create_product,
    get_all_products,
    get_product_by_id,
    update_product,
    delete_product,
    save_product_attachments,
    delete_product_attachment,
    get_all_attachment_details,
)
from Models.productModel import (
    ProductRequest,
    ProductResponse,
    ProductUpdateRequest,
    ProductAttachmentRequest,
    ProductAttachmentResponse,
)
from Utils.JWT import authenticate_request

product_router = APIRouter()

@product_router.post("", response_model=ProductResponse, name="Create a Product")
def create_product_endpoint(
    product_data: ProductRequest, claims: dict = Depends(authenticate_request)
):
    return create_product(product_data)

@product_router.get("", response_model=list[ProductResponse], name="Get All Products")
def get_all_products_endpoint():
    return get_all_products()

@product_router.get("/{product_id}", response_model=ProductResponse, name="Get Product by ID")
def get_product_by_id_endpoint(product_id: int):
    return get_product_by_id(product_id)

@product_router.get("/{product_id}/attachments", response_model=list[ProductAttachmentResponse], name="Get Attachment Details by Product")
def get_all_attachments_endpoint(product_id: int, claims: dict = Depends(authenticate_request)):
    return get_all_attachment_details(product_id)

@product_router.post("/{product_id}/attachments", name="Save Product Attachments")
def save_product_attachments_endpoint(
    product_id: int, attachments: list[ProductAttachmentRequest], claims: dict = Depends(authenticate_request)
):
    return {"message": save_product_attachments(product_id, attachments)}

@product_router.delete("/{product_id}/attachments/{attachment_id}", name="Delete Product Attachment")
def delete_product_attachment_endpoint(
    product_id: int, attachment_id: int, claims: dict = Depends(authenticate_request)
):
    return {"message": delete_product_attachment(attachment_id)}

@product_router.put("/{product_id}", name="Update a Product")
def update_product_endpoint(
    product_id: int, product_data: ProductUpdateRequest, claims: dict = Depends(authenticate_request)
):
    return {"message": update_product(product_id, product_data)}

@product_router.delete("/{product_id}", name="Delete a Product")
def delete_product_endpoint(product_id: int, claims: dict = Depends(authenticate_request)):
    return {"message": delete_product(product_id)}
