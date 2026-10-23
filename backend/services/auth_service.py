from datetime import date, datetime

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.database import transaction
from backend.errors import AppError, ValidationError
from backend.repositories import student_repo, user_repo
from backend.security import issue_token

HASH_METHOD = "pbkdf2:sha256"


def authenticate(username, password):
    user = user_repo.get_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        raise AppError("Invalid username or password.", 401)
    return user


def start_session(user):
    session.clear()
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["student_id"] = user["student_id"]
    session["counsellor_id"] = user["counsellor_id"]
    session["display_name"] = (user["student_name"] if "student_name" in user.keys()
                               else None) or \
                              (user["counsellor_name"] if "counsellor_name" in user.keys()
                               else None) or "Administrator"
    user_repo.touch_login(user["user_id"])


def end_session():
    session.clear()


def login_with_token(username, password):
    user = authenticate(username, password)
    token, expires = issue_token(user["user_id"], user["role"])
    return user, token, expires


def register_student(data):
    if user_repo.username_taken(data["username"]):
        raise ValidationError("That username is taken already.",
                              details={"field": "username"})
    if student_repo.enrollment_taken(data["enrollment_no"]):
        raise ValidationError("That enrollment number is registered already.",
                              details={"field": "enrollment_no"})
    if data.get("dob"):
        born = datetime.strptime(str(data["dob"])[:10], "%Y-%m-%d").date()
        if born > date.today() or (date.today() - born).days > 120 * 366:
            raise ValidationError("Please enter a real date of birth.",
                                  details={"field": "dob"})
    if student_repo.email_taken(data["email"]):
        raise ValidationError("That email is registered already.",
                              details={"field": "email"})

    with transaction() as tx:
        cur = tx.execute(
            "INSERT INTO student (enrollment_no, full_name, email, phone, gender,"
            " dob, dept_id, year_of_study, hostel_status, admission_year)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (data["enrollment_no"], data["full_name"], data["email"],
             data.get("phone"), data.get("gender"), data.get("dob"),
             data["dept_id"], data["year_of_study"], data["hostel_status"],
             2026 - data["year_of_study"]))
        student_id = cur.lastrowid
        tx.execute(
            "INSERT INTO app_user (username, password_hash, role, student_id)"
            " VALUES (?,?,?,?)",
            (data["username"].lower(),
             generate_password_hash(data["password"], method=HASH_METHOD),
             "student", student_id))
    return student_id
