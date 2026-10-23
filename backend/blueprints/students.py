from flask import Blueprint, render_template, request

from backend.errors import NotFoundError
from backend.repositories import (alert_repo, aptitude_repo, assessment_repo, game_repo, lookup_repo,
                                  screening_repo, session_repo, student_repo,
                                  wellness_repo)
from backend.security import login_required, owns_student_or_staff

bp = Blueprint("students", __name__, url_prefix="/students")


@bp.route("/")
@login_required("counsellor", "admin")
def index():
    page = max(1, request.args.get("page", 1, type=int))
    rows, total = student_repo.search(
        q=request.args.get("q", "").strip() or None,
        dept=request.args.get("dept", type=int),
        year=request.args.get("year", type=int),
        risk=request.args.get("risk", ""),
        page=page, per_page=15,
        sort=request.args.get("sort", "risk"),
        direction=request.args.get("dir", "desc"))
    return render_template(
        "students.html", rows=rows, total=total, page=page, per_page=15,
        pages=max(1, (total + 14) // 15),
        q=request.args.get("q", ""), dept=request.args.get("dept", type=int),
        year=request.args.get("year", type=int), risk=request.args.get("risk", ""),
        sort=request.args.get("sort", "risk"), dir=request.args.get("dir", "desc"),
        departments=lookup_repo.departments())


@bp.route("/<int:student_id>")
@login_required()
def detail(student_id):
    owns_student_or_staff(student_id)
    student = student_repo.get(student_id)
    if not student:
        raise NotFoundError("That student does not exist.")
    return render_template(
        "student_detail.html", s=student,
        profile=student_repo.profile(student_id),
        assessments=assessment_repo.for_student(student_id, limit=25),
        themes=student_repo.theme_breakdown(student_id),
        alerts=alert_repo.for_student(student_id),
        sessions=session_repo.for_student(student_id),
        wellness=wellness_repo.for_student(student_id, limit=21),
        trend=student_repo.daily_trend(student_id),
        screenings=screening_repo.for_student(student_id, completed_only=True,
                                              limit=10),
        subscale_trend=screening_repo.subscale_trend(student_id),
        puzzles=aptitude_repo.for_student(student_id, limit=6),
        games=game_repo.for_student(student_id, limit=5))
