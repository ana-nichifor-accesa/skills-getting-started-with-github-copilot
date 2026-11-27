import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    activities = {
        "Chess Club": {
            "description": "Play chess",
            "schedule": "Fridays",
            "max_participants": 4,
            "participants": ["existing@example.com"],
        }
    }
    monkeypatch.setattr(app_module, "activities", activities)
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_root_redirects_to_static_index(client):
    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_details(client):
    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "Chess Club": {
            "description": "Play chess",
            "schedule": "Fridays",
            "max_participants": 4,
            "participants": ["existing@example.com"],
        }
    }


def test_signup_updates_activity(client):
    # Arrange
    email = "new+student@example.com"

    # Act
    signup = client.post("/activities/Chess Club/signup", params={"email": email})

    # Assert
    assert signup.status_code == 200
    assert signup.json() == {"message": f"Signed up {email} for Chess Club"}
    assert client.get("/activities").json()["Chess Club"]["participants"] == [
        "existing@example.com",
        email,
    ]


def test_unregister_updates_activity(client):
    # Arrange
    email = "existing@example.com"

    # Act
    unregister = client.delete(
        "/activities/Chess Club/unregister", params={"email": email}
    )

    # Assert
    assert unregister.status_code == 200
    assert unregister.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert client.get("/activities").json()["Chess Club"]["participants"] == []


@pytest.mark.parametrize(
    ("method", "path", "email", "status", "detail"),
    [
        (
            "POST", "/activities/Unknown/signup", "new@example.com", 404,
            "Activity not found",
        ),
        (
            "DELETE", "/activities/Unknown/unregister", "existing@example.com", 404,
            "Activity not found",
        ),
        (
            "POST", "/activities/Chess Club/signup", "existing@example.com", 400,
            "Student already signed up for this activity",
        ),
        (
            "DELETE", "/activities/Chess Club/unregister", "missing@example.com", 400,
            "Student is not signed up for this activity",
        ),
    ],
)
def test_rejected_registration_changes_leave_participants_unchanged(
    client, method, path, email, status, detail
):
    # Arrange
    initial = client.get("/activities").json()

    # Act
    response = client.request(method, path, params={"email": email})

    # Assert
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert client.get("/activities").json() == initial


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/activities/Chess Club/signup"),
        ("DELETE", "/activities/Chess Club/unregister"),
    ],
)
def test_registration_change_requires_email(client, method, path):
    # Arrange
    initial = client.get("/activities").json()

    # Act
    response = client.request(method, path)

    # Assert
    assert response.status_code == 422
    assert client.get("/activities").json() == initial
