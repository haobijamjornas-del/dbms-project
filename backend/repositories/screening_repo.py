from backend.database import execute, query, scalar, transaction


def items_for(instrument_id):
    return query("SELECT * FROM instrument_item WHERE instrument_id = ?"
                 " ORDER BY item_no", (instrument_id,))


def options_for(instrument_id):
    return query("SELECT * FROM response_option WHERE instrument_id = ?"
                 " ORDER BY option_value", (instrument_id,))


def get(screening_id):
    return query("SELECT * FROM screening WHERE screening_id = ?",
                 (screening_id,), one=True)


def summary(screening_id):
    return query("SELECT * FROM v_screening_summary WHERE screening_id = ?",
                 (screening_id,), one=True)


def for_student(student_id, completed_only=False, limit=50):
    clause = " AND status = 'COMPLETED'" if completed_only else ""
    order = "completed_at" if completed_only else "started_at"
    return query(f"SELECT * FROM v_screening_summary WHERE student_id = ?{clause}"
                 f" ORDER BY {order} DESC LIMIT ?", (student_id, limit))


def recent(limit=100):
    return query("SELECT * FROM v_screening_summary WHERE status = 'COMPLETED'"
                 " ORDER BY completed_at DESC LIMIT ?", (limit,))


def in_progress_for(student_id):
    return query("SELECT screening_id, started_at FROM screening"
                 " WHERE student_id = ? AND status = 'IN_PROGRESS'"
                 " ORDER BY started_at DESC", (student_id,), one=True)


def completed_count(student_id):
    return scalar("SELECT COUNT(*) FROM screening WHERE student_id = ?"
                  "   AND status = 'COMPLETED'", (student_id,))


def create(student_id, is_baseline):
    return execute("INSERT INTO screening (student_id, status, is_baseline)"
                   " VALUES (?, 'IN_PROGRESS', ?)", (student_id, is_baseline))


def save_responses(screening_id, answers):
    with transaction() as tx:
        tx.executemany(
            "INSERT INTO screening_response (screening_id, item_id, option_value)"
            " VALUES (?,?,?)"
            " ON CONFLICT(screening_id, item_id) DO UPDATE SET"
            "   option_value = excluded.option_value,"
            "   answered_at  = datetime('now','localtime')",
            [(screening_id, item_id, value) for item_id, value in answers])


def answered_count(screening_id):
    return scalar("SELECT COUNT(*) FROM screening_response WHERE screening_id = ?",
                  (screening_id,))


def saved_answers(screening_id):
    return {r["item_id"]: r["option_value"] for r in query(
        "SELECT item_id, option_value FROM screening_response WHERE screening_id = ?",
        (screening_id,))}


def unanswered_count(screening_id):
    return scalar(
        "SELECT COUNT(*) FROM instrument_item ii"
        "  JOIN instrument i ON ii.instrument_id = i.instrument_id"
        " WHERE i.is_active = 1"
        "   AND ii.item_id NOT IN (SELECT item_id FROM screening_response"
        "                           WHERE screening_id = ?)", (screening_id,))


def link_assessment(screening_id, assessment_id):
    execute("UPDATE screening SET assessment_id = ? WHERE screening_id = ?",
            (assessment_id, screening_id))


def mark_complete(screening_id):
    execute("UPDATE screening SET status = 'COMPLETED',"
            " completed_at = datetime('now','localtime') WHERE screening_id = ?",
            (screening_id,))


def subscales(screening_id):
    return query("SELECT * FROM v_screening_subscale WHERE screening_id = ?"
                 " ORDER BY display_order", (screening_id,))


def critical_flags(screening_id):
    return query(
        "SELECT ii.question_text, r.option_value, o.option_label, i.code"
        "  FROM screening_response r"
        "  JOIN instrument_item ii ON r.item_id = ii.item_id"
        "  JOIN instrument i ON ii.instrument_id = i.instrument_id"
        "  JOIN response_option o ON o.instrument_id = i.instrument_id"
        "                        AND o.option_value = r.option_value"
        " WHERE r.screening_id = ? AND ii.is_critical = 1 AND r.option_value > 0",
        (screening_id,))


def top_items(screening_id, limit=8):
    return query(
        "SELECT i.code, ii.item_no, ii.question_text, ii.reverse_scored,"
        "       r.option_value, o.option_label, i.option_max"
        "  FROM screening_response r"
        "  JOIN instrument_item ii ON r.item_id = ii.item_id"
        "  JOIN instrument i ON ii.instrument_id = i.instrument_id"
        "  JOIN response_option o ON o.instrument_id = i.instrument_id"
        "                        AND o.option_value = r.option_value"
        " WHERE r.screening_id = ?"
        " ORDER BY (CASE WHEN ii.reverse_scored = 1"
        "                THEN i.option_max - r.option_value"
        "                ELSE r.option_value END) DESC, i.display_order, ii.item_no"
        " LIMIT ?", (screening_id, limit))


def composite_history(student_id):
    return query(
        "SELECT screening_id, completed_at, composite_score, composite_band"
        "  FROM v_screening_summary WHERE student_id = ? AND status = 'COMPLETED'"
        " ORDER BY completed_at", (student_id,))


def subscale_trend(student_id, limit=30):
    return query(
        "SELECT i.code, i.measures, sc.completed_at, ss.raw_score, i.score_max,"
        "       b.band_name, b.color_hex"
        "  FROM screening_score ss"
        "  JOIN screening  sc ON ss.screening_id  = sc.screening_id"
        "  JOIN instrument i  ON ss.instrument_id = i.instrument_id"
        "  LEFT JOIN severity_band b ON ss.band_id = b.band_id"
        " WHERE sc.student_id = ? AND sc.status = 'COMPLETED'"
        " ORDER BY sc.completed_at DESC, i.display_order LIMIT ?",
        (student_id, limit))
