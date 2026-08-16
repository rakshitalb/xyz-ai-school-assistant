from database.school_data import (
    ATTENDANCE_TREND,
    CLASS_SCHEDULE,
    SCHOOL_ATTENDANCE,
    STUDENTS,
    TIMETABLE,
)
def get_class_schedule():
    return CLASS_SCHEDULE
def get_student_timetable(student_name: str):
    return TIMETABLE.get(student_name)
def get_attendance_trend():
    return ATTENDANCE_TREND
def get_student_attendance(student_name: str):
    student = STUDENTS.get(student_name.lower())

    if not student:
        return None

    return {
        "name": student["name"],
        "attendance": student["attendance"],
        "recent_attendance": student["recent_attendance"],
    }


def get_school_attendance():
    return SCHOOL_ATTENDANCE["overall_attendance"]