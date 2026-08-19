"""
Mock escalation service. Simulates handing a conversation off to a real
teacher or school management, per the assessment's escalation flow:

    XYZ AI offers "Talk to Teacher" / "Contact School Management"
    -> user confirms
    -> system triggers a mock call/support request
    -> XYZ AI only confirms success if the mock service actually succeeds

This is a mock integration point. Swapping in a real teacher-notification
or ticketing system later only requires changing trigger_escalation's
implementation -- callers (the /escalate route) don't need to change.
"""

from __future__ import annotations

import uuid
from typing import Optional


def trigger_escalation(
    target: str,
    student_name: Optional[str],
    reason: Optional[str],
) -> dict:
    """Simulate placing a call/support request with a teacher or school
    management. Always "succeeds" in this mock, but returns a structured
    result so the caller can honestly report success/failure rather than
    assuming success.
    """
    request_id = str(uuid.uuid4())
    return {
        "success": True,
        "request_id": request_id,
        "target": target,
        "student_name": student_name,
        "reason": reason,
    }
