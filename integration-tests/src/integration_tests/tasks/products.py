import logging

from locust import tag, task

from integration_tests.tasks.base import BaseTaskSet

logger = logging.getLogger(__name__)
# Als medewerker van amsterdam wil ik een succesvol get request kunnen maken naar het /products
# endpoint met een keycloak/entra authorisatie token.
# Als anonieme gebruiker wil ik een succesvol get request kunnen maken naar het /products endpoint.


@tag("products")
class Products(BaseTaskSet):
    path = "/products"

    def _validate_payload_structure(self, payload, request_type) -> bool:
        products = payload.get("products") if isinstance(payload, dict) else None
        return isinstance(products, list) and payload.get("type") == request_type

    @task
    def anonymous_request_to_products_endpoint(self):
        url = self.user.base_url + "products"
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")

    @task
    def anonymous_request_internal_products(self):
        url = self.user.base_url + "products"
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")

            if response.status_code == 403:
                response.success()

    @task
    def employee_request_to_products_endpoint(self):
        url = self.user.base_url + "products"
        # employee keycloak token?
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.keycloak_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

    @task
    def employee_request_internal_products(self):
        url = self.user.base_url + "products"
        # employee keycloak token?
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.keycloak_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")
