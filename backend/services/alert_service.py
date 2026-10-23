from backend.errors import NotFoundError, ValidationError
from backend.repositories import alert_repo


def search(**kwargs):
    return alert_repo.search(**kwargs)


def get(alert_id):
    row = alert_repo.get(alert_id)
    if not row:
        raise NotFoundError("That alert does not exist.")
    return row


def update(alert_id, status=None, assigned_to=None, remarks=None):
    get(alert_id)
    if status and status not in alert_repo.STATUSES:
        raise ValidationError(f"Status must be one of: {', '.join(alert_repo.STATUSES)}.")

    if assigned_to:
        alert_repo.assign(alert_id, assigned_to)
    if remarks:
        alert_repo.set_remarks(alert_id, remarks)
    if status:
        alert_repo.set_status(alert_id, status)
    return alert_repo.get(alert_id)
