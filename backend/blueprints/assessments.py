from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)

from backend.errors import AppError
from backend.schemas import AssessmentSchema
from backend.security import current_user, login_required
from backend.services import assessment_service
from backend.repositories import student_repo

bp = Blueprint("assessments", __name__)


@bp.route("/assess", methods=["GET", "POST"])
@login_required()
def create():
    user = current_user()
    students = [] if user["role"] == "student" else student_repo.options()

    if request.method == "POST":
        try:
            data = AssessmentSchema.load(request.form)
            target = (user["student_id"] if user["role"] == "student"
                      else data["student_id"])
            assessment_id, _ = assessment_service.record(
                target, data["entry_text"], source=data["source"])
            return redirect(url_for("assessments.detail",
                                    assessment_id=assessment_id))
        except AppError as exc:
            flash(exc.message, "warning")
            return render_template("assess.html", students=students,
                                   entry_text=request.form.get("entry_text", ""))

    return render_template("assess.html", students=students, entry_text="")


@bp.route("/assessment/<int:assessment_id>")
@login_required()
def detail(assessment_id):
    ctx = assessment_service.full_detail(assessment_id)
    user = current_user()
    if user["role"] == "student" and \
            ctx["assessment"]["student_id"] != user["student_id"]:
        raise AppError("You may only view your own entries.", 403)
    return render_template("assessment_detail.html", a=ctx["assessment"],
                           scores=ctx["scores"], keywords=ctx["keywords"],
                           alert=ctx["alert"], guidance=ctx["guidance"],
                           history=ctx["history"],
                           recommendations=ctx["recommendations"],
                           support=ctx["support"])
