import os
from instamojo_wrapper import Instamojo
from .BaseGateway import BaseGateway

class InstamojoGateway(BaseGateway):
    def __init__(self):
        self.api_key = os.getenv("INSTAMOJO_API_KEY")
        self.auth_token = os.getenv("INSTAMOJO_AUTH_TOKEN")
        self.api_url = os.getenv("INSTAMOJO_API_URL")
        self.client = Instamojo(api_key=self.api_key, auth_token=self.auth_token, endpoint=self.api_url)

    def create_payment_request(self, amount: float, purpose: str, buyer_name: str, email: str, phone: str = None, redirect_url: str = None) -> dict:
        return self.client.payment_request_create(
            amount=str(amount),
            purpose=purpose,
            buyer_name=buyer_name,
            email=email,
            phone=phone,
            redirect_url=redirect_url
        )

    def get_payment_status(self, payment_req_id: str) -> dict:
        return self.client.payment_request_status(payment_req_id)

    def delete_payment_request(self, payment_req_id: str) -> dict:
        # Note: Instamojo's python wrapper might not expose delete, checking usage in controller
        # The controller was calling `api.payment_request_delete` line 636
        # The `Instamojo` wrapper might not have it or it's dynamically bound?
        # Let's check `dir(client)` if possible, but assuming it works as per existing code:
        # If the original code called it, I assume it's there.
        # However, typical Instamojo API uses DELETE /payment-requests/{id}/
        # The python wrapper usually maps endpoints.
        # If it fails, we catch it.
        if hasattr(self.client, 'payment_request_delete'):
            return self.client.payment_request_delete(payment_req_id)
        # Fallback or error if not supported
        raise NotImplementedError("Start Delete not supported by this wrapper version or method missing.")

    def list_payment_requests(self) -> dict:
        return self.client.payment_requests_list()
