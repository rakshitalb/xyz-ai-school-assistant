from fastapi import FastAPI
from services.attendance_service import (
    get_student_attendance,
    get_school_attendance,
    get_attendance_trend,
    get_student_timetable,
    get_class_schedule,
)
from models.user import UserRole
from security.permissions import can_view_student_attendance, can_view_school_attendance

app = FastAPI(title="XYZ AI School Assistant")


@app.get("/")
def home():
    return {"message": "XYZ AI School Assistant is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str
    role: UserRole = UserRole.STUDENT
    student_name: str | None = None
    requested_student: str | None = None


@app.post("/ask")
def ask_question(request: QuestionRequest):
    question = request.question.lower()
    answer = "I could not understand the question."

    # Teacher class schedule
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

    # Student timetable
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

    elif "timetable" in question and request.role == UserRole.PARENT:
        target_student = request.requested_student or request.student_name
        if "timetable" in question:
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
        else:
            answer = "You are not authorized to view this student's timetable."
    elif "attendance" in question and "school attendance" not in question and request.requested_student:
            requested_student = request.requested_student
            if can_view_student_attendance(
                request.role,
                requested_student,
                request.student_name
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
    # Attendance trend
    elif "attendance trend" in question:
        if request.role in {UserRole.TEACHER, UserRole.PRINCIPAL}:
            trend = get_attendance_trend()

            answer = (
                "Attendance trend: "
                + ", ".join(
                    f"{day}: {value}%"
                    for day, value in trend.items()
                )
                + "."
            )
        else:
            answer = "You are not authorized to view attendance trends."
    # School-wide attendance
    elif "school attendance" in question:
        if can_view_school_attendance(request.role):
            attendance = get_school_attendance()
            answer = f"The school's overall attendance is {attendance}%."
        else:
            answer = "You are not authorized to view school-wide attendance."

    # Basic AI questions
    elif "iot" in question:
        answer = (
            "IoT stands for Internet of Things. It connects physical "
            "devices to the internet so they can collect and exchange data."
        )

    elif "python" in question:
        answer = (
            "Python is a high-level programming language known for its "
            "simple syntax and wide use in AI, data science, and software development."
        )

    elif "ai" in question or "artificial intelligence" in question:
        answer = (
            "Artificial Intelligence is the ability of machines to perform "
            "tasks that normally require human intelligence, such as learning, "
            "reasoning, and decision making."
        )

    else:
        answer = (
            "I am the XYZ AI School Assistant. I can answer questions about "
            "basic AI, Python, IoT, and school information."
        )

    return {
        "question": request.question,
        "role": request.role,
        "answer": answer
    }