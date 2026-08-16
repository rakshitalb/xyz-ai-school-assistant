from models.user import UserRole


def can_view_student_attendance(role: UserRole, requested_student: str, current_student: str | None = None) -> bool:
    if role == UserRole.STUDENT:
        return requested_student.lower() == (current_student or "").lower()

    if role in {UserRole.PARENT, UserRole.TEACHER, UserRole.PRINCIPAL}:
        return True

    return False


def can_view_school_attendance(role: UserRole) -> bool:
    return role in {
        UserRole.TEACHER,
        UserRole.PRINCIPAL,
    }