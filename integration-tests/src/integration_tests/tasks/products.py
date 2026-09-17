from locust import tag

from integration_tests.tasks.base import BaseTaskSet


@tag("products")
class Products(BaseTaskSet):
    path = "/partnerhistorie"

    def _validate_payload_structure(self, payload, request_type) -> bool:
        products = payload.get("products") if isinstance(payload, dict) else None
        return isinstance(products, list) and payload.get("type") == request_type
