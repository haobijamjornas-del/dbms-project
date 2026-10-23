from backend.errors import AppError, NotFoundError, ValidationError
from backend.repositories import game_repo
from backend.security import current_user
from backend.services import aptitude_service

RESUME_WITHIN_HOURS = 12
GRACE_MS = 1500
LAG_MS = 5000

EMERGENCY_NUMBERS = [
    ("112", "Any emergency: police, fire or ambulance"),
    ("1930", "Cyber crime and online money fraud"),
    ("1906", "LPG cooking gas leak"),
    ("181", "Women's helpline"),
    ("1098", "Childline, for children who need help"),
    ("14416", "Tele-MANAS, free mental health support"),
]


def require_access(game):
    if game is None:
        raise NotFoundError("That game does not exist.")
    user = current_user()
    if user["role"] == "student" and game["student_id"] != user["student_id"]:
        raise AppError("You may only view your own games.", 403)


def start(student_id):
    open_game = game_repo.in_progress_for(student_id)
    if open_game:
        if open_game["hours_old"] < RESUME_WITHIN_HOURS:
            return open_game["game_id"], True
        game_repo.abandon(open_game["game_id"])
    profile = aptitude_service.age_profile(student_id)
    return game_repo.create_game(student_id, profile["group"]["age_group_id"], profile["age"]), False


def _parse_int(raw):
    try:
        return int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


def play_context(game_id):
    game = game_repo.get(game_id)
    require_access(game)
    if game["status"] != "IN_PROGRESS":
        return {"finished": True}

    current = game_repo.current_round(game_id)
    if current is None:
        game_repo.complete(game_id)
        return {"finished": True}
    if current["shown_at"] and current["seconds_left"] <= 0:
        game_repo.time_out(game_id, current["round_no"], current["time_limit_sec"] * 1000)
        return {"feedback": current["round_no"]}

    game_repo.mark_shown(game_id, current["round_no"])
    prog = game_repo.progress(game_id)
    return {
        "game": game,
        "round": current,
        "seconds_left": max(1, int(current["seconds_left"])),
        "places": game_repo.places(),
        "total": prog["total"],
        "answered": prog["answered"] or 0,
        "points": prog["points"],
    }


def submit(game_id, form):
    game = game_repo.get(game_id)
    require_access(game)
    if game["status"] != "IN_PROGRESS":
        return None

    current = game_repo.current_round(game_id)
    round_no = _parse_int(form.get("round_no"))
    if current is None or round_no != current["round_no"]:
        return round_no

    measured = game_repo.elapsed_ms(game_id, round_no)
    reported = _parse_int(form.get("response_ms"))
    if measured is None:
        response_ms = reported
    elif reported is None or not measured - LAG_MS <= reported <= measured + GRACE_MS:
        response_ms = measured
    else:
        response_ms = reported

    place_id = _parse_int(form.get("place_id"))
    if place_id is None:
        game_repo.time_out(game_id, round_no, response_ms)
    elif not game_repo.place_exists(place_id):
        raise ValidationError("That place is not on the map.")
    else:
        game_repo.choose(game_id, round_no, place_id, response_ms)
    return round_no


def feedback_context(game_id, round_no):
    game = game_repo.get(game_id)
    require_access(game)
    detail = game_repo.round_detail(game_id, round_no)
    if detail is None:
        raise NotFoundError("There is no such round in this game.")
    if detail["answered_at"] is None:
        return None
    prog = game_repo.progress(game_id)
    remaining = game_repo.current_round(game_id)
    if remaining is None and game["status"] == "IN_PROGRESS":
        game_repo.complete(game_id)
    return {
        "game": game,
        "detail": detail,
        "places": game_repo.places(),
        "total": prog["total"],
        "answered": prog["answered"] or 0,
        "points": prog["points"],
        "is_last": remaining is None,
    }


def report(game_id):
    game = game_repo.get(game_id)
    require_access(game)
    if game["status"] != "COMPLETED":
        raise AppError("This game is not finished yet.", 409)
    rounds = game_repo.rounds(game_id)
    history = game_repo.for_student(game["student_id"], limit=8)
    previous = next((h for h in history if h["game_id"] != game_id
                     and h["started_at"] < game["started_at"]), None)
    return {
        "game": game,
        "rounds": rounds,
        "missed": [r for r in rounds if not r["is_correct"]],
        "previous": previous,
        "best": game_repo.best_for(game["student_id"]),
        "numbers": EMERGENCY_NUMBERS,
    }


def intro_context(student_id):
    return {
        "profile": aptitude_service.age_profile(student_id),
        "unfinished": game_repo.in_progress_for(student_id),
        "games": game_repo.for_student(student_id),
        "best": game_repo.best_for(student_id),
        "places": game_repo.places(),
        "numbers": EMERGENCY_NUMBERS,
        "rounds": game_repo.ROUNDS,
    }


def staff_context():
    places = game_repo.places()
    cells = {(c["correct_place"], c["chosen_place"]): c["times"] for c in game_repo.confusion()}
    columns = [p["name"] for p in places] + ["Time ran out"]
    matrix = []
    for p in places:
        row = [cells.get((p["name"], col), 0) for col in columns]
        matrix.append({"place": p, "cells": row, "total": sum(row)})
    peak = max([n for r in matrix for n in r["cells"]] or [1])
    return {
        "games": game_repo.recent(60),
        "headline": game_repo.headline(),
        "places": places,
        "columns": columns,
        "matrix": matrix,
        "peak": peak,
        "hardest": game_repo.hardest(),
        "by_group": game_repo.by_age_group(),
        "stars": game_repo.star_counts(),
    }
