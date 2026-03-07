from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseGateway(ABC):
    @abstractmethod
    def create_payment_request(self, amount: float, purpose: str, buyer_name: str, email: str, phone: str = None, redirect_url: str = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_payment_status(self, payment_req_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_payment_request(self, payment_req_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_payment_requests(self) -> Dict[str, Any]:
        pass
