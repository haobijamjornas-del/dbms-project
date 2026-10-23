from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.errors import AppError, ValidationError
from backend.security import current_user, login_required
from backend.services import game_service

bp = Blueprint("game", __name__, url_prefix="/game")


@bp.route("/")
@login_required()
def index():
    user = current_user()
    if user["role"] == "student":
        return render_template("game_intro.html", **game_service.intro_context(user["student_id"]))
    return render_template("game_staff.html", **game_service.staff_context())


@bp.route("/start", methods=["POST"])
@login_required("student")
def start():
    game_id, resumed = game_service.start(current_user()["student_id"])
    if resumed:
        flash("Welcome back. Your game carries on from where you stopped.", "success")
    return redirect(url_for("game.play", game_id=game_id))


@bp.route("/<int:game_id>/play")
@login_required()
def play(game_id):
    ctx = game_service.play_context(game_id)
    if ctx.get("finished"):
        return redirect(url_for("game.result", game_id=game_id))
    if ctx.get("feedback"):
        return redirect(url_for("game.feedback", game_id=game_id, round_no=ctx["feedback"]))
    if current_user()["role"] != "student":
        flash("Only the student who started this game can play it.", "warning")
        return redirect(url_for("game.index"))
    return render_template("game_play.html", **ctx)


@bp.route("/<int:game_id>/send", methods=["POST"])
@login_required("student")
def send(game_id):
    try:
        round_no = game_service.submit(game_id, request.form)
    except ValidationError as exc:
        flash(exc.message, "warning")
        return redirect(url_for("game.play", game_id=game_id))
    if round_no is None:
        return redirect(url_for("game.result", game_id=game_id))
    return redirect(url_for("game.feedback", game_id=game_id, round_no=round_no))


@bp.route("/<int:game_id>/round/<int:round_no>")
@login_required()
def feedback(game_id, round_no):
    ctx = game_service.feedback_context(game_id, round_no)
    if ctx is None:
        return redirect(url_for("game.play", game_id=game_id))
    return render_template("game_feedback.html", **ctx)


@bp.route("/<int:game_id>/result")
@login_required()
def result(game_id):
    try:
        ctx = game_service.report(game_id)
    except AppError as exc:
        if exc.status_code == 409:
            return redirect(url_for("game.play", game_id=game_id))
        raise
    return render_template("game_result.html", **ctx)
