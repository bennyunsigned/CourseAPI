from fastapi import APIRouter, Depends
from Services.bundleService import (
    create_bundle,
    get_all_bundles,
    get_bundle_by_id,
    update_bundle,
    delete_bundle
)
from Models.bundleModel import BundleRequest, BundleResponse, BundleUpdateRequest
from Utils.JWT import authenticate_request

bundle_router = APIRouter()

@bundle_router.post("/", response_model=BundleResponse, name="Create a Bundle")
def create_bundle_endpoint(
    bundle_data: BundleRequest, claims: dict = Depends(authenticate_request)
):
    return create_bundle(bundle_data)

@bundle_router.get("/", response_model=list[BundleResponse], name="Get All Bundles")
def get_all_bundles_endpoint():
    return get_all_bundles()

@bundle_router.get("/{bundle_id}", response_model=BundleResponse, name="Get Bundle by ID")
def get_bundle_by_id_endpoint(bundle_id: int):
    return get_bundle_by_id(bundle_id)

@bundle_router.put("/{bundle_id}", name="Update a Bundle")
def update_bundle_endpoint(
    bundle_id: int, bundle_data: BundleUpdateRequest, claims: dict = Depends(authenticate_request)
):
    return {"message": update_bundle(bundle_id, bundle_data)}

@bundle_router.delete("/{bundle_id}", name="Delete a Bundle")
def delete_bundle_endpoint(bundle_id: int, claims: dict = Depends(authenticate_request)):
    return {"message": delete_bundle(bundle_id)}
