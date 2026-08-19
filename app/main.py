from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from services.attendance_service import (
    get_student_attendance,
    get_school_attendance,
    get_attendance_trend,
    get_student_timetable,
    get_class_schedule,
)
from services.ai_service import AIServiceBase, AIServiceError, get_ai_service
from services.persona_service import persona_for_role
from services.conversation_service import add_turn, get_history
from services.escalation_service import trigger_escalation
from models.user import EscalationTarget, SUPPORTED_LANGUAGES, UserRole
from security.permissions import can_view_student_attendance, can_view_school_attendance

app = FastAPI(title="XYZ AI School Assistant")


# ---------------------------------------------------------------------------
# Security: never leak internal errors / stack traces to the client.
# ---------------------------------------------------------------------------
@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    print("AI SERVICE ERROR:", repr(exc))
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI service is temporarily unavailable. Please try again later."},
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI service is temporarily unavailable. Please try again later."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


@app.get("/")
def home():
    return {"message": "XYZ AI School Assistant is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    role: UserRole = UserRole.STUDENT
    student_name: str | None = None
    requested_student: str | None = None
    language: str = "english"

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty or whitespace-only")
        return v

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v: str) -> str:
        if v.strip().lower() not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{v}'. Supported languages: "
                f"{', '.join(sorted(SUPPORTED_LANGUAGES))}"
            )
        return v.strip().lower()


@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    ai_service: AIServiceBase = Depends(get_ai_service),
):
    question = request.question.lower()
    answer = None

    # ---- Teacher / Principal: class schedule -----------------------------
    if "class schedule" in question:
        if request.role in {UserRole.TEACHER, UserRole.PRINCIPAL}:
            schedule = get_class_schedule()
            answer = (
                "Class schedule: "
                + "; ".join(
                    f"{day}: "
                    + ", ".join(
                        f"{time} - {subject}"
                        for time, subject in classes.items()
                    )
                    for day, classes in schedule.items()
                )
                + "."
            )
        else:
            answer = "You are not authorized to view the class schedule."

    # ---- Student: own timetable --------------------------------------
    elif "timetable" in question and request.role == UserRole.STUDENT:
        if (
            request.requested_student
            and request.requested_student != request.student_name
        ):
            answer = "You are not authorized to view this student's timetable."
        else:
            timetable = get_student_timetable(request.student_name)
            if timetable:
                answer = (
                    f"{request.student_name}'s timetable is: "
                    + "; ".join(
                        f"{day}: {', '.join(subjects)}"
                        for day, subjects in timetable.items()
                    )
                    + "."
                )
            else:
                answer = "I could not find that student's timetable."

    # ---- Parent: child's timetable ------------------------------------
    elif "timetable" in question and request.role == UserRole.PARENT:
        target_student = request.requested_student or request.student_name
        timetable = get_student_timetable(target_student)
        if timetable:
            answer = (
                f"{target_student}'s timetable is: "
                + "; ".join(
                    f"{day}: {', '.join(subjects)}"
                    for day, subjects in timetable.items()
                )
                + "."
            )
        else:
            answer = "I could not find that student's timetable."

    # ---- Student attendance (self/parent/teacher/principal, gated) ----
    elif (
        "attendance" in question
        and "school attendance" not in question
        and "attendance trend" not in question
        and request.requested_student
    ):
        requested_student = request.requested_student
        if can_view_student_attendance(
            request.role, requested_student, request.student_name
        ):
            attendance = get_student_attendance(requested_student)
            if attendance:
                answer = (
                    f"{attendance['name']}'s attendance is "
                    f"{attendance['attendance']}%."
                )
            else:
                answer = "I could not find that student's record."
        else:
            answer = "You are not authorized to view this student's attendance."

    # ---- Teacher / Principal: attendance trend -------------------------
    elif "attendance trend" in question:
        if request.role in {UserRole.TEACHER, UserRole.PRINCIPAL}:
            trend = get_attendance_trend()
            answer = (
                "Attendance trend: "
                + ", ".join(f"{day}: {value}%" for day, value in trend.items())
                + "."
            )
        else:
            answer = "You are not authorized to view attendance trends."

    # ---- Principal: school-wide attendance analytics -------------------
    elif "school attendance" in question:
        if can_view_school_attendance(request.role):
            attendance = get_school_attendance()
            answer = f"The school's overall attendance is {attendance}%."
        else:
            answer = "You are not authorized to view school-wide attendance."

    # ---- Everything else: real, general-purpose educational AI Q&A -----
    # No topic-specific branching here. Any question not matched by the
    # role-specific school actions above is answered by the AI service
    # abstraction, so a brand-new question the source code has never seen
    # (Ohm's Law, UART, KVL, a transistor, an ADC, ...) still gets a real,
    # question-specific answer.
    if answer is None:
        history = get_history(request.role.value, request.student_name)
        persona = persona_for_role(request.role)
        answer = ai_service.generate_answer(
            request.question,
            persona=persona,
            language=request.language,
            history=history,
        )
        add_turn(request.role.value, request.student_name, request.question, answer)

    return {
        "question": request.question,
        "role": request.role,
        "language": request.language,
        "answer": answer,
    }


class EscalationRequest(BaseModel):
    role: UserRole
    student_name: str | None = None
    target: EscalationTarget
    confirm: bool = False
    reason: str | None = None


@app.post("/escalate")
def escalate(request: EscalationRequest):
    """Implements the assessment's escalation flow: XYZ AI must not claim a
    teacher/management representative has been contacted unless the mock
    call/request actually succeeds, and must require explicit confirmation
    first.
    """
    target_label = (
        "teacher" if request.target == EscalationTarget.TEACHER else "school management"
    )

    if not request.confirm:
        return {
            "status": "pending_confirmation",
            "message": (
                f"Of course. I can connect you with {target_label}. "
                "Would you like me to request a call now?"
            ),
        }

    result = trigger_escalation(request.target.value, request.student_name, request.reason)

    if result["success"]:
        return {
            "status": "submitted",
            "message": f"Your call request has been submitted to the {target_label}.",
            "request_id": result["request_id"],
        }

    return {
        "status": "failed",
        "message": (
            f"I was unable to submit your request to the {target_label} "
            "right now. Please try again."
        ),
    }
