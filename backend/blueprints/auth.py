from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)

from backend.errors import AppError
from backend.repositories import lookup_repo, user_repo
from backend.schemas import LoginSchema, RegistrationSchema
from backend.security import current_user
from backend.services import auth_service

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = LoginSchema.load(request.form)
            user = auth_service.authenticate(data["username"], data["password"])
            auth_service.start_session(user)
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for("main.dashboard"))
        except AppError as exc:
            flash(exc.message, "danger")
    return render_template("login.html",
                           sample_student=user_repo.sample_student_username(),
                           username=request.form.get("username")
                           or request.args.get("username", ""))


@bp.route("/logout")
def logout():
    auth_service.end_session()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("main.dashboard"))

    departments = lookup_repo.departments()
    form = {}
    if request.method == "POST":
        form = {k: (v or "").strip() for k, v in request.form.items()}
        try:
            if request.form.get("password") != request.form.get("confirm_password"):
                raise AppError("The two passwords do not match.", 422)
            if not request.form.get("consent"):
                raise AppError("You must consent to your entries being stored "
                               "to continue.", 422)
            data = RegistrationSchema.load(request.form)
            auth_service.register_student(data)
            flash("Account created. Sign in with your new username and password.",
                  "success")
            return redirect(url_for("auth.login", username=data["username"].lower()))
        except AppError as exc:
            flash(exc.message, "danger")
    return render_template("register.html", departments=departments, form=form)
