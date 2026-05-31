from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect
from Utils.JWT import authenticate_request

load_dotenv()

trading_router = APIRouter()

# Setup Kite Connect Client
api_key = os.getenv("ZERODHA_API_KEY", "")
api_secret = os.getenv("ZERODHA_API_SECRET", "")
access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")

kite = KiteConnect(api_key=api_key)
if access_token:
    kite.set_access_token(access_token)

class OrderRequest(BaseModel):
    action: str
    symbol: str
    amount: float
    price: float

@trading_router.get("/status")
def get_trading_status(current_user: dict = Depends(authenticate_request)):
    """Check if the trading engine is connected to Zerodha."""
    return {
        "status": "Zerodha API Microservice Running", 
        "kite_configured": bool(access_token),
        "user": current_user.get("email")
    }

@trading_router.post("/place_order")
def place_order(order: OrderRequest, current_user: dict = Depends(authenticate_request)):
    """
    Places a live order via Zerodha Kite API.
    Requires JWT Authentication.
    """
    if not access_token:
        print(f"[MOCK LIVE EXECUTION] User: {current_user.get('email')} | Action: {order.action} | Symbol: {order.symbol} | Amount: {order.amount}")
        return {"status": "success", "message": "API keys not configured. Mocked execution successful."}
        
    try:
        # Determine transaction type based on Bi-Directional logic
        if order.action in ["BUY", "COVER"]:
            transaction_type = kite.TRANSACTION_TYPE_BUY
        elif order.action in ["SELL", "SHORT"]:
            transaction_type = kite.TRANSACTION_TYPE_SELL
        else:
            raise ValueError("Invalid Action")

        # Map symbol string (e.g., RELIANCE.NS to Zerodha trading symbol)
        trading_symbol = order.symbol.replace(".NS", "")
            
        order_id = kite.place_order(
            tradingsymbol=trading_symbol,
            exchange=kite.EXCHANGE_NSE,
            transaction_type=transaction_type,
            quantity=int(order.amount),
            order_type=kite.ORDER_TYPE_MARKET,
            product=kite.PRODUCT_MIS, # Margin Intraday Squareoff
            variety=kite.VARIETY_REGULAR
        )
        return {"status": "success", "order_id": order_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@trading_router.get("/positions")
def get_positions(current_user: dict = Depends(authenticate_request)):
    if not access_token:
        return {"status": "success", "positions": []}
    try:
        return kite.positions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
