from flask import Blueprint, current_app, jsonify, request

from backend.errors import AppError, NotFoundError
from backend.repositories import (admin_repo, alert_repo, analytics_repo, aptitude_repo, game_repo,
                                  assessment_repo, lookup_repo, screening_repo,
                                  session_repo, student_repo, wellness_repo)
from backend.schemas import (AlertUpdateSchema, AssessmentSchema, LoginSchema,
                             PaginationSchema, SessionSchema)
from backend.security import (api_login_required, current_user,
                              owns_student_or_staff)
from backend.services import (alert_service, aptitude_service, assessment_service, game_service,
                              auth_service, screening_service, session_service)

bp = Blueprint("api", __name__, url_prefix="/api/v1")


def rows(result):
    if result is None:
        return None
    if isinstance(result, (list, tuple)):
        return [dict(r) for r in result]
    return dict(result)


def ok(data, meta=None, status=200):
    body = {"data": data}
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status


def payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def paging():
    return PaginationSchema.load(request.args)


def page_meta(page, per_page, total):
    return {"page": page, "per_page": per_page, "total": total,
            "pages": max(1, (total + per_page - 1) // per_page),
            "has_next": page * per_page < total,
            "has_prev": page > 1}


@bp.route("/health")
def health():
    from backend.database import scalar
    return ok({"status": "ok", "version": "1.0",
               "students": scalar("SELECT COUNT(*) FROM student"),
               "model": (lookup_repo.active_model() or {})["algorithm"]
                        if lookup_repo.active_model() else None})


@bp.route("/")
def index():
    routes = []
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: str(r)):
        if not str(rule).startswith(current_app.config["API_PREFIX"]):
            continue
        methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
        routes.append({
            "path": str(rule),
            "methods": methods,
            "summary": rule.endpoint.split(".")[-1].replace("_", " ").capitalize(),
        })
    return ok({"name": "MindCare API", "version": "1.0", "routes": routes})


@bp.route("/auth/login", methods=["POST"])
def login():
    data = LoginSchema.load(payload())
    user, token, expires = auth_service.login_with_token(data["username"],
                                                         data["password"])
    return ok({"token": token, "expires_at": expires,
               "user": {"user_id": user["user_id"], "username": user["username"],
                        "role": user["role"], "student_id": user["student_id"],
                        "counsellor_id": user["counsellor_id"]}})


@bp.route("/auth/me")
@api_login_required()
def me():
    from flask import g
    return ok({**current_user(), "auth_method": g.auth_method})


@bp.route("/students")
@api_login_required("counsellor", "admin")
def list_students():
    p = paging()
    result, total = student_repo.search(
        q=request.args.get("q") or None,
        dept=request.args.get("dept", type=int),
        year=request.args.get("year", type=int),
        risk=request.args.get("risk"),
        page=p["page"], per_page=p["per_page"],
        sort=request.args.get("sort", "risk"),
        direction=request.args.get("dir", "desc"))
    return ok(rows(result), page_meta(p["page"], p["per_page"], total))


@bp.route("/students/<int:student_id>")
@api_login_required()
def get_student(student_id):
    owns_student_or_staff(student_id)
    student = student_repo.get(student_id)
    if not student:
        raise NotFoundError("That student does not exist.")
    return ok({
        "student": rows(student),
        "profile": rows(student_repo.profile(student_id)),
        "themes": rows(student_repo.theme_breakdown(student_id)),
        "trend": rows(student_repo.daily_trend(student_id)),
        "alerts": rows(alert_repo.for_student(student_id)),
        "sessions": rows(session_repo.for_student(student_id)),
    })


@bp.route("/students/<int:student_id>/assessments")
@api_login_required()
def student_assessments(student_id):
    owns_student_or_staff(student_id)
    p = paging()
    return ok(rows(assessment_repo.for_student(student_id, limit=p["per_page"])))


@bp.route("/students/<int:student_id>/wellness")
@api_login_required()
def student_wellness(student_id):
    owns_student_or_staff(student_id)
    return ok(rows(wellness_repo.for_student(student_id)))


@bp.route("/assessments", methods=["POST"])
@api_login_required()
def create_assessment():
    data = AssessmentSchema.load(payload())
    user = current_user()
    target = user["student_id"] if user["role"] == "student" else data["student_id"]
    assessment_id, result = assessment_service.record(
        target, data["entry_text"], source=data["source"])
    return ok({"assessment_id": assessment_id,
               "prediction": {k: v for k, v in result.items()
                              if k != "keywords"}}, status=201)


@bp.route("/assessments/analyse", methods=["POST"])
@api_login_required()
def analyse_only():
    data = payload()
    text = (data.get("entry_text") or "").strip()
    if len(text) < 10:
        raise AppError("Provide at least 10 characters of text.", 422)
    result = assessment_service.analyse(text)
    return ok({k: v for k, v in result.items() if k != "keywords"})


@bp.route("/assessments/<int:assessment_id>")
@api_login_required()
def get_assessment(assessment_id):
    ctx = assessment_service.full_detail(assessment_id)
    user = current_user()
    if user["role"] == "student" and \
            ctx["assessment"]["student_id"] != user["student_id"]:
        raise AppError("You may only view your own entries.", 403)
    return ok({"assessment": rows(ctx["assessment"]),
               "scores": rows(ctx["scores"]),
               "keywords": rows(ctx["keywords"]),
               "alert": rows(ctx["alert"]),
               "recommendations": ctx["recommendations"]})


@bp.route("/alerts")
@api_login_required("counsellor", "admin")
def list_alerts():
    p = paging()
    mine = request.args.get("mine") == "1"
    result, total = alert_service.search(
        status=request.args.get("status", "OPEN"),
        priority=request.args.get("priority") or None,
        counsellor_id=current_user()["counsellor_id"] if mine else None,
        page=p["page"], per_page=p["per_page"])
    meta = page_meta(p["page"], p["per_page"], total)
    meta["counts"] = alert_repo.status_counts()
    return ok(rows(result), meta)


@bp.route("/alerts/<int:alert_id>", methods=["PATCH", "POST"])
@api_login_required("counsellor", "admin")
def update_alert(alert_id):
    data = AlertUpdateSchema.load(payload())
    updated = alert_service.update(alert_id, status=data["status"],
                                   assigned_to=data["assigned_to"],
                                   remarks=data["remarks"])
    return ok(rows(updated))


@bp.route("/sessions")
@api_login_required("counsellor", "admin")
def list_sessions():
    p = paging()
    result, total = session_service.search(
        status=request.args.get("status", "SCHEDULED"),
        page=p["page"], per_page=p["per_page"])
    meta = page_meta(p["page"], p["per_page"], total)
    meta["counts"] = session_repo.status_counts()
    return ok(rows(result), meta)


@bp.route("/sessions", methods=["POST"])
@api_login_required("counsellor", "admin")
def create_session():
    session_id = session_service.book(SessionSchema.load(payload()))
    return ok(rows(session_repo.get(session_id)), status=201)


@bp.route("/sessions/<int:session_id>", methods=["PATCH", "POST"])
@api_login_required("counsellor", "admin")
def update_session(session_id):
    data = payload()
    updated = session_service.set_status(session_id, data.get("status"),
                                         data.get("notes"))
    return ok(rows(updated))


@bp.route("/screenings")
@api_login_required()
def list_screenings():
    return ok(rows(screening_service.list_for(current_user())))


@bp.route("/screenings/<int:screening_id>")
@api_login_required()
def get_screening(screening_id):
    ctx = screening_service.report(screening_id)
    return ok({"screening": rows(ctx["screening"]),
               "subscales": rows(ctx["subscales"]),
               "critical": rows(ctx["critical"]),
               "top_items": rows(ctx["top_items"]),
               "history": rows(ctx["history"]),
               "recommendations": ctx["recommendations"]})


@bp.route("/puzzles/attempts")
@api_login_required()
def list_puzzle_attempts():
    user = current_user()
    if user["role"] == "student":
        return ok(rows(aptitude_repo.for_student(user["student_id"])))
    return ok(rows(aptitude_repo.recent()))


@bp.route("/puzzles/attempts/<int:attempt_id>")
@api_login_required()
def get_puzzle_attempt(attempt_id):
    ctx = aptitude_service.report(attempt_id)
    return ok({"attempt": rows(ctx["attempt"]),
               "categories": rows(ctx["scores"]),
               "review": rows(ctx["review"])})


@bp.route("/puzzles/age-groups")
@api_login_required()
def list_age_groups():
    return ok(rows(aptitude_repo.age_groups()))


@bp.route("/game/places")
@api_login_required()
def list_places():
    return ok(rows(game_repo.places()))


@bp.route("/game/games")
@api_login_required()
def list_games():
    user = current_user()
    if user["role"] == "student":
        return ok(rows(game_repo.for_student(user["student_id"])))
    return ok(rows(game_repo.recent()))


@bp.route("/game/games/<int:game_id>")
@api_login_required()
def get_game(game_id):
    ctx = game_service.report(game_id)
    return ok({"game": rows(ctx["game"]), "rounds": rows(ctx["rounds"])})


@bp.route("/instruments")
@api_login_required()
def list_instruments():
    out = []
    for ins in lookup_repo.instruments():
        out.append({**dict(ins),
                    "items": rows(screening_repo.items_for(ins["instrument_id"])),
                    "options": rows(screening_repo.options_for(ins["instrument_id"]))})
    return ok(out)


@bp.route("/analytics/summary")
@api_login_required("counsellor", "admin")
def analytics_summary():
    return ok(analytics_repo.headline_stats())


@bp.route("/analytics/trend")
@api_login_required("counsellor", "admin")
def analytics_trend():
    days = min(request.args.get("days", 30, type=int), 365)
    return ok(rows(analytics_repo.daily_trend(days)))


@bp.route("/analytics/themes")
@api_login_required("counsellor", "admin")
def analytics_themes():
    return ok(rows(analytics_repo.themes()))


@bp.route("/analytics/departments")
@api_login_required("counsellor", "admin")
def analytics_departments():
    return ok(rows(analytics_repo.departments()))


@bp.route("/analytics/bands")
@api_login_required("counsellor", "admin")
def analytics_bands():
    return ok(rows(analytics_repo.band_mix()))


@bp.route("/models")
@api_login_required("admin")
def list_models():
    return ok({"models": rows(admin_repo.models()),
               "usage": rows(admin_repo.model_usage())})


@bp.route("/models/<int:model_id>/activate", methods=["POST"])
@api_login_required("admin")
def activate_model(model_id):
    admin_repo.activate_model(model_id)
    return ok(rows(admin_repo.models()))
