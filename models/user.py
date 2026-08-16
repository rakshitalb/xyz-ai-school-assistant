from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    PRINCIPAL = "principal"