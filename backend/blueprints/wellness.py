from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.errors import AppError
from backend.repositories import wellness_repo
from backend.schemas import WellnessSchema
from backend.security import current_user, login_required
from backend.services import daily_service

bp = Blueprint("wellness", __name__, url_prefix="/wellness")


@bp.route("/", methods=["GET", "POST"])
@login_required("student")
def index():
    student_id = current_user()["student_id"]
    if request.method == "POST":
        try:
            wellness_repo.upsert(student_id, WellnessSchema.load(request.form))
            flash("Wellness log saved.", "success")
        except AppError as exc:
            flash(exc.message, "warning")
        return redirect(url_for("wellness.index"))

    return render_template("wellness.html",
                           rows=wellness_repo.for_student(student_id, limit=30),
                           avg=wellness_repo.averages(student_id),
                           today=datetime.now().strftime("%Y-%m-%d"))


@bp.route("/checkin", methods=["POST"])
@login_required("student")
def checkin():
    ratings = {value for value, _key, _label in daily_service.MOODS}
    try:
        rating = int(request.form.get("mood", ""))
    except ValueError:
        rating = None
    if rating not in ratings:
        flash("Please pick one of the faces to check in.", "warning")
    else:
        wellness_repo.set_mood(current_user()["student_id"],
                               datetime.now().strftime("%Y-%m-%d"), rating)
    return redirect(url_for("main.dashboard") + "#checkin")
