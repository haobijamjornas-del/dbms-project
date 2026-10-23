from backend.repositories import (alert_repo, analytics_repo, lookup_repo,
                                  student_repo)
from backend.services import daily_service


def staff_dashboard(counsellor_id=None):
    return {
        "priorities": analytics_repo.priorities(counsellor_id),
        "today": daily_service.pretty_today(),
        "stats": analytics_repo.headline_stats(),
        "level_mix": lookup_repo.level_mix(),
        "trend": analytics_repo.daily_trend(30),
        "queue": alert_repo.queue(8),
        "at_risk": student_repo.at_risk(8),
        "themes": analytics_repo.themes_by_high(8),
        "subscale_mix": analytics_repo.subscale_band_counts(),
    }


def full_report():
    return {
        "depts": analytics_repo.departments(),
        "themes": analytics_repo.themes(),
        "trend": analytics_repo.daily_trend(45),
        "by_year": analytics_repo.by_year(),
        "by_hostel": analytics_repo.by_hostel(),
        "by_hour": analytics_repo.by_hour(),
        "keywords": analytics_repo.keyword_usage(),
        "source_mix": analytics_repo.source_mix(),
        "alert_stats": analytics_repo.alert_stats(),
        "response": analytics_repo.response_time(),
        "corpus": analytics_repo.corpus_mix(),
        "band_mix": analytics_repo.band_mix(),
        "worst_items": analytics_repo.worst_items(),
        "agreement": analytics_repo.text_vs_questionnaire(),
        "dept_screening": analytics_repo.dept_screening(),
    }
