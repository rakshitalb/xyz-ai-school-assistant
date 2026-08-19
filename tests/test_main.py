import pytest
from fastapi.testclient import TestClient

from app.main import app
from services.ai_service import AIServiceBase, AIServiceError, get_ai_service

client = TestClient(app)


# ---------------------------------------------------------------------------
# Basic health/home
# ---------------------------------------------------------------------------
def test_home():
    response = client.get("/")
    assert response.status_code == 200


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# /ask -- general educational AI Q&A (uses the offline FakeAIProvider by
# default, since no AI_API_KEY is set in the test environment). These tests
# verify BEHAVIOR and the API CONTRACT, not one exact hardcoded sentence:
# the answer must exist, be non-empty, and be specific to the question
# asked -- never a canned "please ask a valid question" style response.
# ---------------------------------------------------------------------------
def _ask(question, role="student", student_name="Rakshita", requested_student="Rakshita", **extra):
    payload = {
        "question": question,
        "role": role,
        "student_name": student_name,
        "requested_student": requested_student,
    }
    payload.update(extra)
    return client.post("/ask", json=payload)


def test_ask_returns_contract_shape():
    response = _ask("What is Python?")
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "role" in data
    assert "answer" in data
    assert "language" in data


def test_ask_python_is_question_specific():
    response = _ask("What is Python?")
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is Python?"
    assert data["role"] == "student"
    assert "Python" in data["answer"]
    assert data["answer"].strip() != ""


def test_ask_iot_is_question_specific():
    response = _ask("What is IoT?")
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is IoT?"
    assert "IoT" in data["answer"]


@pytest.mark.parametrize(
    "question,expected_fragment",
    [
        ("What is Ohm's Law?", "Ohm"),
        ("What is UART?", "UART"),
        ("Explain Kirchhoff's Voltage Law.", "Kirchhoff"),
        ("What is a transistor?", "transistor"),
        ("How does an ADC work?", "ADC"),
        ("What is the difference between RAM and ROM?", "RAM and ROM"),
        ("Explain TCP and UDP.", "TCP and UDP"),
        ("What is recursion?", "recursion"),
    ],
)
def test_ask_handles_arbitrary_unseen_questions(question, expected_fragment):
    """None of these questions/topics are hardcoded anywhere in the source
    code. This proves /ask is not a fixed if/elif lookup table: the answer
    it returns is derived from the question text itself at request time.
    """
    response = _ask(question)
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == question
    assert data["answer"].strip() != ""
    assert expected_fragment in data["answer"]
    # Must not be a generic non-answer.
    assert "please ask a valid question" not in data["answer"].lower()
    assert data["answer"].lower() != "this is an educational question."


def test_two_different_questions_get_different_answers():
    r1 = _ask("What is Ohm's Law?")
    r2 = _ask("What is UART?")
    assert r1.json()["answer"] != r2.json()["answer"]


# ---------------------------------------------------------------------------
# Conversation history: same student asking twice should not error and
# should still get a specific answer (context passed through, not required
# to change output for the fake provider, but must not break the flow).
# ---------------------------------------------------------------------------
def test_follow_up_question_still_works():
    r1 = _ask("What is a capacitor?", student_name="HistoryTester", requested_student="HistoryTester")
    assert r1.status_code == 200
    r2 = _ask("What is an inductor?", student_name="HistoryTester", requested_student="HistoryTester")
    assert r2.status_code == 200
    assert "capacitor" in r1.json()["answer"].lower()
    assert "inductor" in r2.json()["answer"].lower()


# ---------------------------------------------------------------------------
# Validation / error handling
# ---------------------------------------------------------------------------
def test_ask_missing_question_field_returns_422():
    response = client.post("/ask", json={"role": "student"})
    assert response.status_code == 422


def test_ask_empty_question_returns_422():
    response = _ask("")
    assert response.status_code == 422


def test_ask_whitespace_only_question_returns_422():
    response = _ask("    ")
    assert response.status_code == 422


def test_ask_invalid_role_returns_422():
    response = _ask("What is Python?", role="hacker")
    assert response.status_code == 422


def test_ask_unsupported_language_returns_422():
    response = _ask("What is Python?", language="klingon")
    assert response.status_code == 422


def test_ask_supported_language_accepted():
    response = _ask("What is Python?", language="Hindi")
    assert response.status_code == 200
    assert response.json()["language"] == "hindi"


def test_ask_malformed_json_body_returns_422():
    response = client.post(
        "/ask",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# AI service failure handling: swap in a provider that always fails and
# confirm the API degrades gracefully (503, no stack trace leaked).
# ---------------------------------------------------------------------------
class _AlwaysFailingProvider(AIServiceBase):
    def generate_answer(self, question, *, persona="", language="english", history=None):
        raise AIServiceError("simulated provider outage")


def test_ai_service_failure_returns_503_without_leaking_internals():
    app.dependency_overrides[get_ai_service] = lambda: _AlwaysFailingProvider()
    try:
        response = _ask("What is Ohm's Law?")
        assert response.status_code == 503
        body = response.json()
        assert "detail" in body
        assert "simulated provider outage" not in body["detail"]
        assert "Traceback" not in str(body)
    finally:
        app.dependency_overrides.pop(get_ai_service, None)


# ---------------------------------------------------------------------------
# Role-based attendance use cases (existing functionality, preserved)
# ---------------------------------------------------------------------------
def test_student_can_view_own_attendance():
    response = _ask(
        "What is my attendance?",
        role="student",
        student_name="Rahul",
        requested_student="Rahul",
    )
    assert response.status_code == 200
    assert "91.2" in response.json()["answer"]


def test_student_cannot_view_another_students_attendance():
    response = _ask(
        "What is my attendance?",
        role="student",
        student_name="Rahul",
        requested_student="Priya",
    )
    assert response.status_code == 200
    assert "not authorized" in response.json()["answer"].lower()


def test_parent_can_view_childs_attendance():
    response = _ask(
        "How much attendance does my child have?",
        role="parent",
        student_name="ParentUser",
        requested_student="Rahul",
    )
    assert response.status_code == 200
    assert "91.2" in response.json()["answer"]


def test_principal_can_view_school_attendance():
    response = _ask(
        "What is the overall school attendance?",
        role="principal",
        student_name=None,
        requested_student=None,
    )
    assert response.status_code == 200
    assert "89.7" in response.json()["answer"]


def test_student_cannot_view_school_attendance():
    response = _ask(
        "What is the overall school attendance?",
        role="student",
        student_name="Rahul",
        requested_student=None,
    )
    assert response.status_code == 200
    assert "not authorized" in response.json()["answer"].lower()


def test_teacher_can_view_attendance_trend():
    response = _ask(
        "Show me the attendance trend",
        role="teacher",
        student_name=None,
        requested_student=None,
    )
    assert response.status_code == 200
    assert "%" in response.json()["answer"]


def test_teacher_can_view_class_schedule():
    response = _ask(
        "What is the class schedule?",
        role="teacher",
        student_name=None,
        requested_student=None,
    )
    assert response.status_code == 200
    assert "Mathematics" in response.json()["answer"]


def test_student_cannot_view_class_schedule():
    response = _ask(
        "What is the class schedule?",
        role="student",
        student_name="Rahul",
        requested_student=None,
    )
    assert response.status_code == 200
    assert "not authorized" in response.json()["answer"].lower()


# ---------------------------------------------------------------------------
# Escalation flow
# ---------------------------------------------------------------------------
def test_escalation_requires_confirmation_first():
    response = client.post(
        "/escalate",
        json={"role": "parent", "student_name": "Rahul", "target": "teacher", "confirm": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_confirmation"


def test_escalation_submits_after_confirmation():
    response = client.post(
        "/escalate",
        json={
            "role": "parent",
            "student_name": "Rahul",
            "target": "teacher",
            "confirm": True,
            "reason": "Not satisfied with attendance answer",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "submitted"
    assert "teacher" in data["message"].lower()
    assert "request_id" in data


def test_escalation_to_school_management():
    response = client.post(
        "/escalate",
        json={
            "role": "parent",
            "student_name": "Rahul",
            "target": "school_management",
            "confirm": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"


def test_escalation_invalid_target_returns_422():
    response = client.post(
        "/escalate",
        json={"role": "parent", "target": "random_department", "confirm": True},
    )
    assert response.status_code == 422
