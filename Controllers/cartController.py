from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Body

from Models.cartModel import AddToCartRequest, CartItemResponse, RemoveFromCartRequest  # adjust imports if names differ
from Services.cartService import (
    add_course_to_cart,
    get_cart_products_by_user,
    remove_course_from_cart,
)
from Utils.JWT import authenticate_request

logger = logging.getLogger(__name__)
cart_router = APIRouter()


@cart_router.post('/', name='Add to Cart', status_code=status.HTTP_201_CREATED)
def add_to_cart(req: AddToCartRequest, claims: dict = Depends(authenticate_request)):
    """
    Add the given course to the authenticated user's cart.
    """
    try:
        user_id = claims.get('id')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth claims")

        cart_id = add_course_to_cart(user_id, req.course_id)
        return {"CartId": cart_id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add course %s to cart for user %s", getattr(req, "course_id", None), claims.get("id"))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@cart_router.get('/', response_model=list[CartItemResponse], name='Get Cart Items')
def get_cart(claims: dict = Depends(authenticate_request)):
    """
    Return list of cart items for the authenticated user.
    """
    try:
        user_id = claims.get('id')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth claims")

        items = get_cart_products_by_user(user_id)
        return items
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get cart for user %s", claims.get("id"))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@cart_router.delete('/', name='Remove from Cart')
def remove_from_cart(
    course_id: Optional[int] = None,
    body: Optional[RemoveFromCartRequest] = Body(None),
    claims: dict = Depends(authenticate_request),
):
    """
    Remove the given course from the authenticated user's cart.

    Accepts course_id as a query param (?course_id=123) or as JSON body { "course_id": 123 }.
    """
    try:
        # Accept either query param or JSON body
        if course_id is None and body is not None:
            course_id = body.course_id

        if course_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="course_id is required")

        user_id = claims.get('id')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth claims")

        ok = remove_course_from_cart(user_id, course_id)
        if ok:
            return {"success": True}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to remove course %s from cart for user %s", course_id, claims.get("id"))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")