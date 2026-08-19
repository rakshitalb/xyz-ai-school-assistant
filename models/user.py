from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    PRINCIPAL = "principal"


class EscalationTarget(str, Enum):
    TEACHER = "teacher"
    SCHOOL_MANAGEMENT = "school_management"


# Languages required by the assessment spec (section 4: Language Support).
SUPPORTED_LANGUAGES = {
    "english",
    "hindi",
    "tamil",
    "telugu",
    "marathi",
    "bengali",
    "gujarati",
    "punjabi",
    "kannada",
    "malayalam",
    "urdu",
}