import logging

from locust import tag, task

from integration_tests.tasks.base import BaseTaskSet

logger = logging.getLogger(__name__)


@tag("products")
class Products(BaseTaskSet):
    path = "/products"

    def _validate_payload_structure(self, payload, request_type) -> bool:
        products = payload.get("products") if isinstance(payload, dict) else None
        return isinstance(products, list) and payload.get("type") == request_type

    @task
    def anonymous_request_to_products_endpoint(self):
        url = self.user.base_url + "products/55"
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

    @task
    def employee_request_to_products_endpoint(self):
        url = self.user.base_url + "products/55"
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.employee_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

    @task
    def team_member_request_to_products_endpoint(self):
        url = self.user.base_url + "products/55"
        self.client.headers.update({"Authorization": f"Bearer {self.user.environment.team_token}"})
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

    @task
    def admin_request_to_products_endpoint(self):
        url = self.user.base_url + "products/55"
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.admin_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

    @task
    def anonymous_request_internal_products(self):
        url = self.user.base_url + "products/339"
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

            if response.status_code == 401:
                response.success()

    @task
    def employee_request_internal_products(self):
        url = self.user.base_url + "products/339"
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.employee_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")
