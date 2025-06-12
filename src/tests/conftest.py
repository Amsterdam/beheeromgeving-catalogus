from __future__ import annotations

from pathlib import Path

import pytest
from rest_framework.test import APIClient

HERE = Path(__file__).parent


@pytest.fixture()
def api_client() -> APIClient:
    """Return a client that has unhindered access to the API views"""
    api_client = APIClient()
    api_client.default_format = "json"  # instead of multipart
    return api_client
