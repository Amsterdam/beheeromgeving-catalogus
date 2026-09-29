import uuid

from locust import HttpUser

from integration_tests import settings
from integration_tests.tasks import (
    Me,
    Products,
)


class AuthorizedUser(HttpUser):
    host: str = settings.CATALOGUS_URL
    base_path: str = "/"
    base_url: str = f"{host}{base_path}"
    # entra token
    tasks = {Me}

    def on_start(self):
        self.client.headers = {
            "X-User": "AuthorizedUser Catalogus Integration Tests",
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Task-Description": "Integration Tests",
            "Content-Type": "application/json",
        }


class CatalogusUser(HttpUser):
    host: str = settings.CATALOGUS_URL
    base_path: str = "/"
    base_url: str = f"{host}{base_path}"
    # no auth or keycloak token
    tasks = {Products}

    def on_start(self):
        self.client.headers = {
            "X-User": "CatalogusUser Catalogus Integration Tests",
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Task-Description": "Integration Tests",
            "Content-Type": "application/json",
        }
