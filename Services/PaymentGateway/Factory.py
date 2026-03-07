import os
from .RazorpayGateway import RazorpayGateway

def get_payment_gateway():
    return RazorpayGateway()
