import uuid

from fastapi.testclient import TestClient

from backend.main import app


def register_and_login(client, prefix):
    email = f"{prefix}-{uuid.uuid4()}@example.com"
    password = "test-password-with-12-chars"
    register = client.post("/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_private_resources_are_scoped_to_their_owner():
    with TestClient(app) as client:
        first_user = register_and_login(client, "first")
        second_user = register_and_login(client, "second")

        created = client.post(
            "/saved_screens",
            headers=first_user,
            json={"name": "Growth", "criteria": {"min_revenue_growth": 10}},
        )
        assert created.status_code == 201

        first_list = client.get("/saved_screens", headers=first_user)
        second_list = client.get("/saved_screens", headers=second_user)

    assert len(first_list.json()) == 1
    assert second_list.json() == []


def test_private_endpoint_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/watchlist")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
