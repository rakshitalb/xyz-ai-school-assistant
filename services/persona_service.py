"""Maps user roles to the AI persona described in the assessment spec."""

from models.user import UserRole

_PERSONAS: dict[UserRole, str] = {
    UserRole.STUDENT: (
        "You are acting as a friendly and supportive Academic Assistant "
        "for a student."
    ),
    UserRole.PARENT: (
        "You are acting as a caring and patient Parent Support Assistant "
        "for a parent."
    ),
    UserRole.TEACHER: (
        "You are acting as a professional Teaching Assistant for a "
        "teacher."
    ),
    UserRole.PRINCIPAL: (
        "You are acting as a professional Management Assistant for a "
        "school principal."
    ),
}


def persona_for_role(role: UserRole) -> str:
    return _PERSONAS.get(role, _PERSONAS[UserRole.STUDENT])
