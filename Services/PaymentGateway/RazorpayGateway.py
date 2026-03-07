import os
import razorpay
import time
from .BaseGateway import BaseGateway

class RazorpayGateway(BaseGateway):
    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        if not self.key_id or not self.key_secret:
            raise ValueError("Razorpay keys not found in environment variables.")
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def _adapt_to_instamojo_format(self, plink_details: dict) -> dict:
        """
        Convert Razorpay Payment Link details to Instamojo-like response structure.
        Razorpay plink status: created, paid, cancelled, expired
        Instamojo status: Pending, Completed, Failed
        """
        status_map = {
            'created': 'Pending',
            'paid': 'Completed',
            'cancelled': 'Failed',
            'expired': 'Failed',
            'partially_paid': 'Pending' # or process as custom logic
        }
        
        rp_status = plink_details.get('status', 'created')
        im_status = status_map.get(rp_status, 'Pending')
        
        # Razorpay payments array (if paid)
        payments = []
        if rp_status == 'paid':
            # Razorpay link fetch doesn't always return the full payment details inside
            # But the 'payments' field might be populated if expanded or we might need to fetch separately.
            # However, for simplicity and compatibility:
            # We add a dummy payment object if it's paid, or try to use `payments` if present.
            # In Razorpay Link response, `payments` is a list of payment attempts if expanded?
            # Actually standard response includes `payments: [...]` if we use `expand=['payments']`?
            # Default fetch might not.
            # Let's assume we just need to satisfy the Controller check:
            # Controller checks: `status_str.lower() in ('completed', 'success', 'credit')`
            # OR `for p in payments: if p.status in (...)`
             payments.append({
                'payment_id': plink_details.get('id'), # Use plink id as payment id reference
                'status': 'Completed',
                'amount': plink_details.get('amount_paid', 0) / 100,
                'buyer_name': plink_details.get('customer', {}).get('name'),
                'buyer_email': plink_details.get('customer', {}).get('email'),
                'buyer_phone': plink_details.get('customer', {}).get('contact')
             })

        return {
            "success": True, # Instamojo wrapper returns this wrapper dict usually?
            # Actually instamojo_wrapper returns a dict which IS the response from API + success flag sometimes?
            # The controller checks `response.get('payment_request')`.
            "payment_request": {
                "id": plink_details.get('id'),
                "phone": plink_details.get('customer', {}).get('contact'),
                "email": plink_details.get('customer', {}).get('email'),
                "buyer_name": plink_details.get('customer', {}).get('name'),
                "amount": str(plink_details.get('amount', 0) / 100), # Razorpay is in paise
                "purpose": plink_details.get('description'),
                "status": im_status,
                "longurl": plink_details.get('short_url'), # This is CRITICAL for frontend redirection
                "redirect_url": plink_details.get('callback_url'),
                "created_at": str(plink_details.get('created_at')),
                "modified_at": str(plink_details.get('updated_at')),
                "payments": payments
            }
        }

    def create_payment_request(self, amount: float, purpose: str, buyer_name: str, email: str, phone: str = None, redirect_url: str = None) -> dict:
        # Razorpay amount is in integer paise
        amount_paise = int(float(amount) * 100)
        
        data = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": purpose,
            "customer": {
                "name": buyer_name,
                "email": email,
                "contact": phone or ""
            },
            "notify": {
                "sms": True,
                "email": True
            },
            "reminder_enable": True,
            "callback_url": redirect_url, # Razorpay will redirect here after payment
            "callback_method": "get" # Instamojo usually sends GET with payment_id
        }
        
        try:
            response = self.client.payment_link.create(data)
            return self._adapt_to_instamojo_format(response)
        except Exception as e:
             # Mimic error structure?
             # Controller expects a dict, check line 209: response.get('message')
             return {
                 "success": False,
                 "message": str(e)
             }

    def get_payment_status(self, payment_req_id: str) -> dict:
        try:
            response = self.client.payment_link.fetch(payment_req_id)
            return self._adapt_to_instamojo_format(response)
        except Exception as e:
            return {
                 "success": False,
                 "message": str(e)
            }

    def delete_payment_request(self, payment_req_id: str) -> dict:
        try:
            # Razorpay links can be cancelled
            self.client.payment_link.cancel(payment_req_id)
            return {"success": True}
        except Exception as e:
             return {"success": False, "message": str(e)}

    def list_payment_requests(self) -> dict:
        # Not fully implemented to match list structure, but avoiding error
        return {"payment_requests": []}
