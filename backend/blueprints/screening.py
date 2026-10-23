from datetime import datetime

from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)

from backend.errors import AppError
from backend.repositories import screening_repo, lookup_repo
from backend.security import current_user, login_required
from backend.services import screening_service

bp = Blueprint("screening", __name__, url_prefix="/screening")


@bp.route("/")
@login_required()
def index():
    return render_template("screenings.html",
                           rows=screening_service.list_for(current_user()),
                           instruments=screening_service.instruments())


@bp.route("/start", methods=["GET", "POST"])
@login_required()
def start():
    user = current_user()
    if user["role"] != "student":
        flash("Only a signed-in student can take a screening.", "warning")
        return redirect(url_for("screening.index"))

    if request.method == "POST":
        screening_id, _resumed = screening_service.start(user["student_id"])
        return redirect(url_for("screening.step", screening_id=screening_id, step=1))

    completed = screening_repo.for_student(user["student_id"],
                                           completed_only=True, limit=1)
    return render_template(
        "screening_intro.html",
        instruments=screening_service.instruments(),
        previous=completed[0] if completed else None,
        unfinished=screening_repo.in_progress_for(user["student_id"]),
        total_items=lookup_repo.total_instrument_items())


@bp.route("/<int:screening_id>/step/<int:step>", methods=["GET", "POST"])
@login_required()
def step(screening_id, step):
    scr = screening_repo.get(screening_id)
    screening_service.require_access(scr)
    if scr["status"] == "COMPLETED":
        return redirect(url_for("screening.result", screening_id=screening_id))

    total = screening_service.total_steps()

    if request.method == "POST":
        if step < total:
            try:
                screening_service.save_step(screening_id, step, request.form)
            except AppError as exc:
                flash(exc.message, "warning")
                return redirect(url_for("screening.step",
                                        screening_id=screening_id, step=step))
            return redirect(url_for("screening.step",
                                    screening_id=screening_id, step=step + 1))
        return _finish(screening_id, total)

    ctx = screening_service.step_context(screening_id, step)
    template = ("screening_step.html" if step < total
                else "screening_reflection.html")
    return render_template(template, scr=scr,
                           today=datetime.now().strftime("%Y-%m-%d"), **ctx)


def _finish(screening_id, total):
    wellness = None
    if request.form.get("sleep_hours"):
        def num(name, cast):
            raw = request.form.get(name)
            try:
                return cast(raw) if raw not in (None, "") else None
            except (TypeError, ValueError):
                return None
        wellness = {
            "log_date": request.form.get("log_date"),
            "sleep_hours": num("sleep_hours", float),
            "exercise_min": num("exercise_min", int),
            "mood_rating": num("mood_rating", int),
            "screen_time_hrs": num("screen_time_hrs", float),
        }
    try:
        screening_service.finish(screening_id,
                                 request.form.get("entry_text", ""), wellness)
    except AppError as exc:
        flash(exc.message, "warning")
        return redirect(url_for("screening.step", screening_id=screening_id,
                                step=total))
    return redirect(url_for("screening.result", screening_id=screening_id))


@bp.route("/<int:screening_id>/result")
@login_required()
def result(screening_id):
    try:
        ctx = screening_service.report(screening_id)
    except AppError as exc:
        if exc.status_code == 409:
            return redirect(url_for("screening.step",
                                    screening_id=screening_id, step=1))
        raise
    return render_template("screening_result.html", scr=ctx["screening"],
                           subscales=ctx["subscales"], critical=ctx["critical"],
                           top_items=ctx["top_items"], history=ctx["history"],
                           alert=ctx["alert"],
                           recommendations=ctx["recommendations"],
                           support=ctx["support"])
