from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ask_python():
    response = client.post(
        "/ask",
        json={
            "question": "What is Python?",
            "role": "student",
            "student_name": "Rakshita",
            "requested_student": "Rakshita"
        }
    )

    assert response.status_code == 200
    assert "question" in response.json()
    assert "answer" in response.json()