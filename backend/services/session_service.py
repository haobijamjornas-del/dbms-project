import sqlite3

from backend.errors import AppError, NotFoundError, ValidationError
from backend.repositories import session_repo

STATUSES = ("SCHEDULED", "COMPLETED", "CANCELLED", "NO_SHOW")


def search(**kwargs):
    return session_repo.search(**kwargs)


def book(data):
    scheduled = str(data["scheduled_at"]).replace("T", " ")
    if len(scheduled) == 16:
        scheduled += ":00"
    payload = dict(data, scheduled_at=scheduled)
    try:
        return session_repo.create(payload)
    except sqlite3.IntegrityError as exc:
        if "already has a session" in str(exc):
            raise AppError("That counsellor is already booked at this time.", 409)
        raise


def set_status(session_id, status, notes=None):
    if status not in STATUSES:
        raise ValidationError(f"Status must be one of: {', '.join(STATUSES)}.")
    if not session_repo.get(session_id):
        raise NotFoundError("That session does not exist.")
    if notes:
        session_repo.set_notes(session_id, notes)
    session_repo.set_status(session_id, status)
    return session_repo.get(session_id)
