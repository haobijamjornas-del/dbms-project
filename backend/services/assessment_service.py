from backend.errors import AppError, NotFoundError
from backend.repositories import (alert_repo, assessment_repo, lookup_repo,
                                  student_repo, support_repo)
from backend.services.prediction_service import THEME_ADVICE, StressPredictor


def analyse(text):
    try:
        return StressPredictor().predict(text)
    except ValueError as exc:
        raise AppError(str(exc), 422)


def record(student_id, text, source="web"):
    if not student_id:
        raise AppError("A student must be selected for this entry.", 422)
    if not student_repo.get(student_id):
        raise NotFoundError("That student does not exist.")

    model = lookup_repo.active_model()
    if not model:
        raise AppError("No active model in the registry. "
                       "Run: python ml/train_model.py", 503)

    result = analyse(text)
    theme = lookup_repo.theme_by_code(result["theme_code"])
    assessment_id = assessment_repo.create(
        student_id, model["model_id"], text, result,
        theme["theme_id"] if theme else None, source=source)
    return assessment_id, result


def detail(assessment_id):
    row = assessment_repo.detail(assessment_id)
    if not row:
        raise NotFoundError("That assessment does not exist.")
    return row


def theme_advice(theme_name):
    if not theme_name:
        return None
    code = lookup_repo.theme_code_by_name(theme_name)
    return THEME_ADVICE.get(code["theme_code"]) if code else None


def recommendations_for(level_code, theme_name=None):
    recs = [f"{t['title']}: {t['body']}" for t in support_repo.tips_for(level_code, "ADVICE")]
    extra = theme_advice(theme_name)
    if extra:
        recs.append(extra)
    return recs


def support_for(level_code, theme_name=None):
    return {
        "level_code": level_code,
        "advice": support_repo.tips_for(level_code, "ADVICE"),
        "coping": support_repo.tips_for(level_code, "COPING"),
        "theme_advice": theme_advice(theme_name),
        "helplines": support_repo.helplines(),
    }


def full_detail(assessment_id):
    row = detail(assessment_id)
    return {
        "assessment": row,
        "scores": assessment_repo.scores(assessment_id),
        "keywords": assessment_repo.keywords(assessment_id),
        "alert": alert_repo.for_assessment(assessment_id),
        "guidance": lookup_repo.level_guidance(row["level_code"]),
        "history": assessment_repo.history(row["student_id"]),
        "recommendations": recommendations_for(row["level_code"], row["theme_name"]),
        "support": support_for(row["level_code"], row["theme_name"]),
    }
