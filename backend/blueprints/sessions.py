from datetime import datetime, timedelta

from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)

from backend.errors import AppError
from backend.repositories import alert_repo, lookup_repo, session_repo, student_repo
from backend.schemas import SessionSchema
from backend.security import current_user, login_required
from backend.services import session_service

bp = Blueprint("sessions", __name__, url_prefix="/sessions")


@bp.route("/", methods=["GET", "POST"])
@login_required("counsellor", "admin")
def index():
    if request.method == "POST":
        try:
            session_service.book(SessionSchema.load(request.form))
            flash("Session booked.", "success")
        except AppError as exc:
            flash(exc.message, "danger")
        return redirect(url_for("sessions.index"))

    status = request.args.get("status", "SCHEDULED")
    rows, total = session_service.search(status=status, per_page=200)
    return render_template(
        "sessions.html", rows=rows, total=total, status=status,
        counts=session_repo.status_counts(), workload=session_repo.workload(),
        students=student_repo.options(), counsellors=lookup_repo.counsellors(),
        open_alerts=alert_repo.open_for_booking(),
        default_dt=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00"))


@bp.route("/<int:session_id>/status", methods=["POST"])
@login_required("counsellor", "admin")
def update_status(session_id):
    session_service.set_status(session_id, request.form.get("status"),
                               request.form.get("notes", "").strip() or None)
    flash(f"Session #{session_id} marked {request.form.get('status')}.", "success")
    return redirect(request.referrer or url_for("sessions.index"))
