from flask import Blueprint, render_template

from backend.repositories import (alert_repo, aptitude_repo, assessment_repo, screening_repo,
                                  session_repo, student_repo, support_repo,
                                  wellness_repo)
from backend.security import current_user, login_required
from backend.services import analytics_service, daily_service

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required()
def dashboard():
    user = current_user()
    if user["role"] == "student":
        return _student_dashboard(user["student_id"])
    return render_template("dashboard_staff.html",
                           **analytics_service.staff_dashboard(user.get("counsellor_id")))


def _student_dashboard(student_id):
    screenings = screening_repo.for_student(student_id, completed_only=True,
                                            limit=5)
    latest = screenings[0] if screenings else None
    return render_template(
        "dashboard_student.html",
        profile=student_repo.profile(student_id),
        recent=assessment_repo.for_student(student_id, limit=8),
        trend=student_repo.daily_trend(student_id, days=30),
        wellness=wellness_repo.raw_for_student(student_id, limit=14),
        sessions=session_repo.for_student(student_id, limit=5),
        screenings=screenings,
        latest_screening=latest,
        subscales=screening_repo.subscales(latest["screening_id"]) if latest else [],
        alerts=alert_repo.for_student(student_id, limit=3),
        helplines=support_repo.helplines(),
        mood=daily_service.today_mood(student_id),
        moods=daily_service.MOODS,
        week=daily_service.week_strip(student_id),
        today=daily_service.pretty_today(),
        puzzle=aptitude_repo.latest_for(student_id))
