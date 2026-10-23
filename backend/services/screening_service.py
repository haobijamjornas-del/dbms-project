from backend.errors import AppError, NotFoundError, ValidationError
from backend.repositories import (alert_repo, lookup_repo, screening_repo,
                                  wellness_repo)
from backend.security import current_user
from backend.services import assessment_service

BAND_TO_LEVEL = {"Low": 0, "Medium": 1, "High": 2}


def instruments():
    return lookup_repo.instruments()


def total_steps():
    return len(instruments()) + 1


def require_access(screening):
    if screening is None:
        raise NotFoundError("That screening does not exist.")
    user = current_user()
    if user["role"] == "student" and screening["student_id"] != user["student_id"]:
        raise AppError("You may only view your own assessments.", 403)


def start(student_id):
    existing = screening_repo.in_progress_for(student_id)
    if existing:
        return existing["screening_id"], True
    is_baseline = 0 if screening_repo.completed_count(student_id) else 1
    return screening_repo.create(student_id, is_baseline), False


def step_context(screening_id, step):
    ins = instruments()
    total = len(ins) + 1
    if step < 1 or step > total:
        raise NotFoundError("There is no such step in this assessment.")
    ctx = {
        "step": step,
        "total_steps": total,
        "answered": screening_repo.answered_count(screening_id),
        "total_items": lookup_repo.total_instrument_items(),
    }
    if step <= len(ins):
        instrument = ins[step - 1]
        ctx.update(instrument=instrument,
                   items=screening_repo.items_for(instrument["instrument_id"]),
                   options=screening_repo.options_for(instrument["instrument_id"]),
                   saved=screening_repo.saved_answers(screening_id))
    return ctx


def save_step(screening_id, step, form):
    ins = instruments()
    if step > len(ins):
        raise ValidationError("That step does not collect answers.")
    instrument = ins[step - 1]
    items = screening_repo.items_for(instrument["instrument_id"])

    answers, missing = [], 0
    for item in items:
        raw = form.get(f"item_{item['item_id']}")
        if raw is None or raw == "":
            missing += 1
            continue
        try:
            answers.append((item["item_id"], int(raw)))
        except (TypeError, ValueError):
            raise ValidationError("An answer was not a valid option.")
    if missing:
        raise ValidationError(
            f"Please answer all {len(items)} questions ({missing} still blank).")

    screening_repo.save_responses(screening_id, answers)
    return len(answers)


def finish(screening_id, entry_text, wellness=None):
    screening = screening_repo.get(screening_id)
    require_access(screening)
    if screening["status"] == "COMPLETED":
        return screening_id

    if not entry_text or len(entry_text.strip()) < 10:
        raise ValidationError(
            "Please write at least a sentence so the text can be analysed.")

    outstanding = screening_repo.unanswered_count(screening_id)
    if outstanding:
        raise ValidationError(
            f"{outstanding} question(s) are still unanswered. "
            f"Please go back and complete them.")

    assessment_id, _ = assessment_service.record(
        screening["student_id"], entry_text.strip(), source="web")
    screening_repo.link_assessment(screening_id, assessment_id)

    if wellness and wellness.get("log_date") and wellness.get("sleep_hours") is not None:
        try:
            wellness_repo.upsert(screening["student_id"], wellness)
        except Exception:
            pass

    screening_repo.mark_complete(screening_id)
    return screening_id


def report(screening_id):
    summary = screening_repo.summary(screening_id)
    require_access(summary)
    if summary["status"] != "COMPLETED":
        raise AppError("That assessment is not finished yet.", 409)

    band = summary["composite_band"]
    return {
        "screening": summary,
        "subscales": screening_repo.subscales(screening_id),
        "critical": screening_repo.critical_flags(screening_id),
        "top_items": screening_repo.top_items(screening_id),
        "history": screening_repo.composite_history(summary["student_id"]),
        "alert": alert_repo.for_assessment(summary["assessment_id"])
                 if summary["assessment_id"] else None,
        "recommendations": assessment_service.recommendations_for(
            BAND_TO_LEVEL.get(band, 1)),
        "support": assessment_service.support_for(
            BAND_TO_LEVEL.get(band, 1), summary["text_theme"]),
    }


def list_for(user):
    if user["role"] == "student":
        return screening_repo.for_student(user["student_id"])
    return screening_repo.recent()
