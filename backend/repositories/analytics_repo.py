from backend.database import query, scalar


def headline_stats():
    return {
        "students": scalar("SELECT COUNT(*) FROM student WHERE is_active = 1"),
        "assessments": scalar("SELECT COUNT(*) FROM assessment"),
        "assessments_7d": scalar("SELECT COUNT(*) FROM assessment"
                                 " WHERE created_at >= DATE('now','localtime','-7 days')"),
        "open_alerts": scalar("SELECT COUNT(*) FROM alert WHERE status = 'OPEN'"),
        "critical": scalar("SELECT COUNT(*) FROM alert"
                           " WHERE priority = 'CRITICAL' AND status <> 'RESOLVED'"),
        "sessions_upcoming": scalar("SELECT COUNT(*) FROM counselling_session"
                                    " WHERE status = 'SCHEDULED'"),
        "avg_stress": round(scalar("SELECT AVG(predicted_level) FROM assessment",
                                   default=0.0), 3),
        "high_pct": round(scalar(
            "SELECT 100.0 * SUM(CASE WHEN predicted_level = 2 THEN 1 ELSE 0 END)"
            " / NULLIF(COUNT(*),0) FROM assessment", default=0.0), 1),
        "screenings": scalar("SELECT COUNT(*) FROM screening"
                             " WHERE status = 'COMPLETED'"),
        "screening_high": scalar("SELECT COUNT(*) FROM screening"
                                 " WHERE composite_band = 'High'"),
        "critical_items": scalar(
            "SELECT COUNT(DISTINCT r.screening_id) FROM screening_response r"
            "  JOIN instrument_item ii ON r.item_id = ii.item_id"
            " WHERE ii.is_critical = 1 AND r.option_value > 0"),
    }


def daily_trend(days=30):
    return query("SELECT * FROM v_daily_trend WHERE entry_date >= DATE('now','localtime', ?)"
                 " ORDER BY entry_date", (f"-{days} days",))


def themes(limit=None):
    sql = "SELECT * FROM v_theme_distribution WHERE total > 0 ORDER BY total DESC"
    return query(sql + " LIMIT ?", (limit,)) if limit else query(sql)


def themes_by_high(limit=8):
    return query("SELECT * FROM v_theme_distribution WHERE total > 0"
                 " ORDER BY high DESC LIMIT ?", (limit,))


def departments():
    return query("SELECT * FROM v_dept_stress_summary ORDER BY high_stress_pct DESC")


def by_year():
    return query(
        "SELECT s.year_of_study AS yr, COUNT(a.assessment_id) AS n,"
        "       ROUND(AVG(a.predicted_level),3) AS avg_lvl,"
        "       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high"
        "  FROM student s JOIN assessment a ON s.student_id = a.student_id"
        " GROUP BY s.year_of_study ORDER BY s.year_of_study")


def by_hostel():
    return query(
        "SELECT s.hostel_status AS grp, COUNT(a.assessment_id) AS n,"
        "       ROUND(AVG(a.predicted_level),3) AS avg_lvl,"
        "       ROUND(100.0*SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)"
        "             / NULLIF(COUNT(a.assessment_id),0),1) AS high_pct"
        "  FROM student s JOIN assessment a ON s.student_id = a.student_id"
        " GROUP BY s.hostel_status")


def by_hour():
    return query(
        "SELECT CAST(STRFTIME('%H', created_at) AS INTEGER) AS hr, COUNT(*) AS n,"
        "       ROUND(AVG(predicted_level),2) AS avg_lvl"
        "  FROM assessment GROUP BY hr ORDER BY hr")


def keyword_usage(limit=18):
    return query(
        "SELECT k.word, k.category, k.weight, k.polarity,"
        "       COUNT(ak.assessment_id) AS uses,"
        "       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS in_high"
        "  FROM keyword_lexicon k"
        "  JOIN assessment_keyword ak ON k.keyword_id = ak.keyword_id"
        "  JOIN assessment a ON ak.assessment_id = a.assessment_id"
        " GROUP BY k.keyword_id HAVING uses > 0 ORDER BY uses DESC LIMIT ?",
        (limit,))


def source_mix():
    return query("SELECT source, COUNT(*) AS n, ROUND(AVG(predicted_level),2) AS avg_lvl"
                 "  FROM assessment GROUP BY source ORDER BY n DESC")


def alert_stats():
    return query("SELECT alert_type, priority, status, COUNT(*) AS n FROM alert"
                 " GROUP BY alert_type, priority, status ORDER BY n DESC")


def response_time():
    return query(
        "SELECT ROUND(AVG(JULIANDAY(resolved_at) - JULIANDAY(raised_at)) * 24, 1)"
        "         AS avg_hours, COUNT(*) AS resolved_count"
        "  FROM alert WHERE resolved_at IS NOT NULL", one=True)


def corpus_mix(limit=12):
    return query(
        "SELECT sl.level_name, t.category, COUNT(*) AS n FROM training_corpus tc"
        "  JOIN stress_level sl ON tc.label = sl.level_code"
        "  JOIN theme t ON tc.theme_id = t.theme_id"
        " GROUP BY sl.level_name, t.category ORDER BY n DESC LIMIT ?", (limit,))


def band_mix():
    return query(
        "SELECT i.code, i.measures, i.display_order, b.band_name,"
        "       b.min_score || '-' || b.max_score AS score_range,"
        "       b.color_hex, b.severity_rank, COUNT(ss.screening_id) AS students,"
        "       ROUND(COUNT(ss.screening_id) * 100.0"
        "             / NULLIF(SUM(COUNT(ss.screening_id))"
        "                      OVER (PARTITION BY i.code), 0), 1) AS pct"
        "  FROM instrument i"
        "  JOIN severity_band b ON i.instrument_id = b.instrument_id"
        "  LEFT JOIN screening_score ss ON ss.band_id = b.band_id"
        " GROUP BY i.code, b.band_id ORDER BY i.display_order, b.severity_rank")


def subscale_band_counts():
    return query(
        "SELECT i.code, i.measures, b.band_name, b.color_hex, b.severity_rank,"
        "       COUNT(*) AS n FROM screening_score ss"
        "  JOIN instrument i ON ss.instrument_id = i.instrument_id"
        "  LEFT JOIN severity_band b ON ss.band_id = b.band_id"
        " GROUP BY i.code, b.band_id ORDER BY i.display_order, b.severity_rank")


def worst_items(limit=10):
    return query("SELECT * FROM v_item_response_stats WHERE times_answered > 0"
                 " ORDER BY avg_pct_of_max DESC LIMIT ?", (limit,))


def text_vs_questionnaire():
    return query(
        "SELECT sc.composite_band,"
        "       SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END) AS text_low,"
        "       SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END) AS text_moderate,"
        "       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS text_high,"
        "       COUNT(*) AS total, ROUND(AVG(sc.composite_score), 1) AS avg_composite"
        "  FROM screening sc JOIN assessment a ON sc.assessment_id = a.assessment_id"
        " WHERE sc.status = 'COMPLETED'"
        " GROUP BY sc.composite_band ORDER BY avg_composite")


def dept_screening():
    return query(
        "SELECT d.dept_code, COUNT(DISTINCT sc.screening_id) AS screenings,"
        "       ROUND(AVG(sc.composite_score), 1) AS avg_composite,"
        "       ROUND(AVG(CASE WHEN i.code = 'PHQ-9'  THEN ss.raw_score END), 1) AS avg_phq9,"
        "       ROUND(AVG(CASE WHEN i.code = 'GAD-7'  THEN ss.raw_score END), 1) AS avg_gad7,"
        "       ROUND(AVG(CASE WHEN i.code = 'PSS-10' THEN ss.raw_score END), 1) AS avg_pss10"
        "  FROM screening sc"
        "  JOIN student s ON sc.student_id = s.student_id"
        "  JOIN department d ON s.dept_id = d.dept_id"
        "  LEFT JOIN screening_score ss ON sc.screening_id = ss.screening_id"
        "  LEFT JOIN instrument i ON ss.instrument_id = i.instrument_id"
        " WHERE sc.status = 'COMPLETED' GROUP BY d.dept_code"
        " ORDER BY avg_composite DESC")


def priorities(counsellor_id=None):
    mine = " AND assigned_to = ?" if counsellor_id else ""
    mine_args = (counsellor_id,) if counsellor_id else ()
    return {
        "critical": scalar("SELECT COUNT(*) FROM alert WHERE priority = 'CRITICAL'"
                           " AND status IN ('OPEN','ACKNOWLEDGED')"),
        "critical_mine": scalar("SELECT COUNT(*) FROM alert WHERE priority = 'CRITICAL'"
                                " AND status IN ('OPEN','ACKNOWLEDGED')" + mine, mine_args)
        if counsellor_id else None,
        "waiting": scalar("SELECT COUNT(*) FROM alert WHERE status = 'OPEN'"
                          " AND raised_at < datetime('now','localtime','-3 days')"),
        "sessions_today": scalar("SELECT COUNT(*) FROM counselling_session"
                                 " WHERE status = 'SCHEDULED'"
                                 " AND DATE(scheduled_at) = DATE('now','localtime')"
                                 + (" AND counsellor_id = ?" if counsellor_id else ""), mine_args),
        "next_session": query("SELECT cs.scheduled_at, s.full_name FROM counselling_session cs"
                              "  JOIN student s ON cs.student_id = s.student_id"
                              " WHERE cs.status = 'SCHEDULED'"
                              "   AND cs.scheduled_at >= datetime('now','localtime')"
                              + (" AND cs.counsellor_id = ?" if counsellor_id else "")
                              + " ORDER BY cs.scheduled_at LIMIT 1", mine_args, one=True),
        "entries_24h": scalar("SELECT COUNT(*) FROM assessment"
                              " WHERE created_at >= datetime('now','localtime','-1 day')"),
        "high_24h": scalar("SELECT COUNT(*) FROM assessment WHERE predicted_level = 2"
                           " AND created_at >= datetime('now','localtime','-1 day')"),
        "puzzles_7d": scalar("SELECT COUNT(*) FROM aptitude_attempt WHERE status = 'COMPLETED'"
                             " AND completed_at >= datetime('now','localtime','-7 days')"),
        "games_7d": scalar("SELECT COUNT(*) FROM rescue_game WHERE status = 'COMPLETED'"
                           " AND completed_at >= datetime('now','localtime','-7 days')"),
    }

