import uuid

from locust import HttpUser

from integration_tests import settings
from integration_tests.tasks import (
    Products,
    Teams,
)  # CatalogusTaskSet


class CatalogusUser(HttpUser):
    host: str = settings.CATALOGUS_URL
    base_path: str = "/"
    base_url: str = f"{host}{base_path}"

    tasks = {Teams, Products}  # , CatalogusTaskSet}

    def on_start(self):
        self.client.headers = {
            "X-User": "Catalogus Integration Tests",
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Task-Description": "Integration Tests",
            "Content-Type": "application/json",
        }
