from fastapi.testclient import TestClient

from api.main import app
from core.config import CORS_ALLOWED_ORIGINS


def test_cors_preflight_allows_configured_origin():
    client = TestClient(app)
    origin = CORS_ALLOWED_ORIGINS[0]

    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_preflight_rejects_unknown_origin():
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None
