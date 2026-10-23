from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.errors import AppError, ValidationError
from backend.security import current_user, login_required
from backend.services import aptitude_service

bp = Blueprint("puzzles", __name__, url_prefix="/puzzles")


@bp.route("/")
@login_required()
def index():
    user = current_user()
    if user["role"] == "student":
        return render_template("puzzles_intro.html",
                               **aptitude_service.intro_context(user["student_id"]))
    return render_template("puzzles_staff.html", **aptitude_service.staff_context())


@bp.route("/start", methods=["POST"])
@login_required("student")
def start():
    attempt_id, resumed = aptitude_service.start(current_user()["student_id"])
    if resumed:
        flash("Welcome back. We have picked up where you left off.", "success")
    return redirect(url_for("puzzles.play", attempt_id=attempt_id))


@bp.route("/<int:attempt_id>/play")
@login_required()
def play(attempt_id):
    ctx = aptitude_service.play_context(attempt_id)
    if ctx is None:
        return redirect(url_for("puzzles.result", attempt_id=attempt_id))
    if current_user()["role"] != "student":
        flash("Only the student who started these puzzles can answer them.", "warning")
        return redirect(url_for("puzzles.index"))
    return render_template("puzzles_play.html", swatch=aptitude_service.swatch, **ctx)


@bp.route("/<int:attempt_id>/answer", methods=["POST"])
@login_required("student")
def answer(attempt_id):
    try:
        finished = aptitude_service.submit(attempt_id, request.form)
    except ValidationError as exc:
        flash(exc.message, "warning")
        return redirect(url_for("puzzles.play", attempt_id=attempt_id))
    if finished:
        return redirect(url_for("puzzles.result", attempt_id=attempt_id))
    return redirect(url_for("puzzles.play", attempt_id=attempt_id))


@bp.route("/<int:attempt_id>/result")
@login_required()
def result(attempt_id):
    try:
        ctx = aptitude_service.report(attempt_id)
    except AppError as exc:
        if exc.status_code == 409:
            return redirect(url_for("puzzles.play", attempt_id=attempt_id))
        raise
    return render_template("puzzles_result.html", swatch=aptitude_service.swatch, **ctx)
