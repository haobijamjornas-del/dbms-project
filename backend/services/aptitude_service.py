from backend.errors import AppError, NotFoundError, ValidationError
from backend.repositories import aptitude_repo, student_repo
from backend.security import current_user

DEFAULT_GROUP = "INTERMEDIATE"
RESUME_WITHIN_HOURS = 12
GRACE_MS = 1500
LAG_MS = 5000
STRENGTH_PCT = 60

SWATCHES = {
    "red": "#E5484D",
    "blue": "#3E63DD",
    "green": "#2F9E62",
    "orange": "#F17A1A",
    "purple": "#8E4EC6",
    "pink": "#E04A9B",
}

PRACTICE_TIPS = {
    "LOGIC": "Slow down and put the question in your own words. For order or family puzzles, "
             "a quick sketch or a line of names makes the answer much easier to see.",
    "NUMBER": "Write the gap between each pair of numbers. If the gaps are not equal, "
              "look at the gaps between the gaps, or try multiplying.",
    "STROOP": "Look at the colour, not the letters. Short daily practice, fewer "
              "distractions and a good night's sleep all sharpen this kind of focus.",
    "PATTERN": "Say the colours aloud in small groups and find the point where the "
               "pattern starts again.",
    "CODE": "Read the key first, then work one colour at a time. Jotting numbers down "
            "frees up memory for the actual sum.",
}

STRENGTH_NOTES = {
    "LOGIC": "You read carefully and reason step by step.",
    "NUMBER": "You spot numerical rules quickly.",
    "STROOP": "You keep your attention steady even when something tries to distract you.",
    "PATTERN": "You notice visual patterns and repetition easily.",
    "CODE": "You hold several pieces of information in mind at once.",
}


def swatch(key):
    return SWATCHES.get(key or "", "#98a1b0")


def age_profile(student_id):
    row = aptitude_repo.student_age(student_id)
    age = row["age"] if row and row["dob"] else None
    group = aptitude_repo.group_for_age(age) if age is not None else None
    return {
        "age": age,
        "group": group or aptitude_repo.group_by_code(DEFAULT_GROUP),
        "matched": group is not None,
    }


def require_access(attempt):
    if attempt is None:
        raise NotFoundError("That puzzle session does not exist.")
    user = current_user()
    if user["role"] == "student" and attempt["student_id"] != user["student_id"]:
        raise AppError("You may only view your own puzzle results.", 403)


def start(student_id):
    open_attempt = aptitude_repo.in_progress_for(student_id)
    if open_attempt:
        if open_attempt["hours_old"] < RESUME_WITHIN_HOURS:
            return open_attempt["attempt_id"], True
        aptitude_repo.abandon(open_attempt["attempt_id"])
    profile = age_profile(student_id)
    attempt_id = aptitude_repo.create_attempt(student_id, profile["group"]["age_group_id"],
                                              profile["age"])
    return attempt_id, False


def play_context(attempt_id):
    attempt = aptitude_repo.get(attempt_id)
    require_access(attempt)
    if attempt["status"] != "IN_PROGRESS":
        return None

    item = aptitude_repo.current_item(attempt_id)
    while item and item["shown_at"] and item["seconds_left"] <= 0:
        aptitude_repo.skip(attempt_id, item["position"], item["time_limit_sec"] * 1000)
        item = aptitude_repo.current_item(attempt_id)
    if item is None:
        aptitude_repo.complete(attempt_id)
        return None

    aptitude_repo.mark_shown(attempt_id, item["position"])
    elements = aptitude_repo.elements(item["puzzle_id"])
    prog = aptitude_repo.progress(attempt_id)
    return {
        "attempt": attempt,
        "item": item,
        "seconds_left": max(1, int(item["seconds_left"])),
        "options": aptitude_repo.options(item["puzzle_id"]),
        "word": next((e for e in elements if e["role"] == "WORD"), None),
        "sequence": [e for e in elements if e["role"] == "SEQUENCE"],
        "key": [e for e in elements if e["role"] == "KEY"],
        "total": prog["total"],
        "answered": prog["answered"] or 0,
    }


def _parse_int(raw):
    try:
        return int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


def submit(attempt_id, form):
    attempt = aptitude_repo.get(attempt_id)
    require_access(attempt)
    if attempt["status"] != "IN_PROGRESS":
        return True

    item = aptitude_repo.current_item(attempt_id)
    position = _parse_int(form.get("position"))
    if item is None or position != item["position"]:
        return item is None

    measured = aptitude_repo.elapsed_ms(attempt_id, position)
    reported = _parse_int(form.get("response_ms"))
    if measured is None:
        response_ms = reported
    elif reported is None or not measured - LAG_MS <= reported <= measured + GRACE_MS:
        response_ms = measured
    else:
        response_ms = reported

    option_id = _parse_int(form.get("option_id"))
    if option_id is None:
        aptitude_repo.skip(attempt_id, position, response_ms)
    else:
        if option_id not in {o["option_id"] for o in aptitude_repo.options(item["puzzle_id"])}:
            raise ValidationError("That answer does not belong to this puzzle.")
        aptitude_repo.answer(attempt_id, position, option_id, response_ms)

    if aptitude_repo.current_item(attempt_id) is None:
        aptitude_repo.complete(attempt_id)
        return True
    return False


def report(attempt_id):
    attempt = aptitude_repo.get(attempt_id)
    require_access(attempt)
    if attempt["status"] != "COMPLETED":
        raise AppError("This puzzle session is not finished yet.", 409)

    scores = aptitude_repo.category_scores(attempt_id)
    strengths = [dict(s, note=STRENGTH_NOTES.get(s["category_code"], ""))
                 for s in scores if s["accuracy_pct"] >= STRENGTH_PCT]
    practice = [dict(s, tip=PRACTICE_TIPS.get(s["category_code"], ""))
                for s in scores if s["accuracy_pct"] < STRENGTH_PCT]
    history = aptitude_repo.for_student(attempt["student_id"], limit=8)
    previous = next((h for h in history if h["attempt_id"] != attempt_id
                     and h["started_at"] < attempt["started_at"]), None)
    profile = student_repo.profile(attempt["student_id"])
    visuals = {}
    for e in aptitude_repo.review_elements(attempt_id):
        visuals.setdefault(e["puzzle_id"], {"WORD": [], "SEQUENCE": [], "KEY": []})[e["role"]].append(e)
    return {
        "attempt": attempt,
        "scores": scores,
        "strengths": strengths,
        "practice": practice,
        "review": aptitude_repo.review(attempt_id),
        "visuals": visuals,
        "history": list(reversed(history)),
        "previous": previous,
        "latest_level": profile["latest_level"] if profile else None,
    }


def intro_context(student_id):
    return {
        "profile": age_profile(student_id),
        "unfinished": aptitude_repo.in_progress_for(student_id),
        "attempts": aptitude_repo.for_student(student_id),
        "groups": aptitude_repo.age_groups(),
        "categories": aptitude_repo.categories(),
    }


def staff_context():
    return {
        "attempts": aptitude_repo.recent(60),
        "headline": aptitude_repo.headline(),
        "groups": aptitude_repo.age_groups(),
        "categories": aptitude_repo.categories(),
        "by_category": aptitude_repo.by_category(),
        "by_group": aptitude_repo.by_age_group(),
        "bands": aptitude_repo.band_counts(),
        "focus": aptitude_repo.focus_vs_stress(),
        "hardest": aptitude_repo.hardest(),
    }
