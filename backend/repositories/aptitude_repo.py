from backend.database import execute, query, scalar, transaction

PER_CATEGORY = 3


def age_groups():
    return query("SELECT g.*,"
                 "       (SELECT COUNT(*) FROM puzzle p"
                 "         WHERE p.age_group_id = g.age_group_id AND p.is_active = 1) AS puzzles"
                 "  FROM age_group g ORDER BY g.difficulty")


def categories():
    return query("SELECT * FROM puzzle_category ORDER BY display_order")


def bands():
    return query("SELECT * FROM aptitude_band ORDER BY min_pct")


def student_age(student_id):
    return query(
        "SELECT dob,"
        "       CAST(strftime('%Y','now','localtime') AS INTEGER)"
        "     - CAST(strftime('%Y', dob) AS INTEGER)"
        "     - (strftime('%m-%d','now','localtime') < strftime('%m-%d', dob)) AS age"
        "  FROM student WHERE student_id = ?", (student_id,), one=True)


def group_for_age(age):
    return query("SELECT * FROM age_group WHERE ? BETWEEN min_age AND max_age"
                 " ORDER BY difficulty LIMIT 1", (age,), one=True)


def group_by_code(code):
    return query("SELECT * FROM age_group WHERE code = ?", (code,), one=True)


def get(attempt_id):
    return query("SELECT * FROM v_aptitude_summary WHERE attempt_id = ?",
                 (attempt_id,), one=True)


def in_progress_for(student_id):
    return query("SELECT attempt_id, started_at,"
                 "       (JULIANDAY('now','localtime') - JULIANDAY(started_at)) * 24 AS hours_old"
                 "  FROM aptitude_attempt"
                 " WHERE student_id = ? AND status = 'IN_PROGRESS'"
                 " ORDER BY started_at DESC LIMIT 1", (student_id,), one=True)


def abandon(attempt_id):
    execute("UPDATE aptitude_attempt SET status = 'ABANDONED' WHERE attempt_id = ?",
            (attempt_id,))


def create_attempt(student_id, age_group_id, age):
    with transaction() as tx:
        cur = tx.execute("INSERT INTO aptitude_attempt (student_id, age_group_id, age_at_attempt)"
                         " VALUES (?,?,?)", (student_id, age_group_id, age))
        attempt_id = cur.lastrowid
        picks = tx.execute(
            "SELECT puzzle_id FROM ("
            "  SELECT p.puzzle_id, c.display_order,"
            "         ROW_NUMBER() OVER (PARTITION BY p.category_id ORDER BY RANDOM()) AS pick"
            "    FROM puzzle p JOIN puzzle_category c ON p.category_id = c.category_id"
            "   WHERE p.age_group_id = ? AND p.is_active = 1"
            ") WHERE pick <= ? ORDER BY display_order, pick",
            (age_group_id, PER_CATEGORY)).fetchall()
        tx.executemany("INSERT INTO aptitude_item (attempt_id, position, puzzle_id)"
                       " VALUES (?,?,?)",
                       [(attempt_id, n, row[0]) for n, row in enumerate(picks, start=1)])
    return attempt_id


def current_item(attempt_id):
    return query(
        "SELECT i.attempt_id, i.position, i.puzzle_id, i.shown_at,"
        "       p.prompt, p.time_limit_sec,"
        "       c.code AS category_code, c.name AS category, c.skill, c.instructions,"
        "       CASE WHEN i.shown_at IS NULL THEN p.time_limit_sec"
        "            ELSE p.time_limit_sec - (JULIANDAY('now','localtime') - JULIANDAY(i.shown_at)) * 86400"
        "       END AS seconds_left"
        "  FROM aptitude_item i"
        "  JOIN puzzle p          ON i.puzzle_id   = p.puzzle_id"
        "  JOIN puzzle_category c ON p.category_id = c.category_id"
        " WHERE i.attempt_id = ? AND i.answered_at IS NULL"
        " ORDER BY i.position LIMIT 1", (attempt_id,), one=True)


def progress(attempt_id):
    return query(
        "SELECT COUNT(*) AS total,"
        "       SUM(CASE WHEN answered_at IS NOT NULL THEN 1 ELSE 0 END) AS answered"
        "  FROM aptitude_item WHERE attempt_id = ?", (attempt_id,), one=True)


def mark_shown(attempt_id, position):
    execute("UPDATE aptitude_item"
            "   SET shown_at = strftime('%Y-%m-%d %H:%M:%f','now','localtime')"
            " WHERE attempt_id = ? AND position = ? AND shown_at IS NULL",
            (attempt_id, position))


def elapsed_ms(attempt_id, position):
    return scalar("SELECT CAST((JULIANDAY('now','localtime') - JULIANDAY(shown_at)) * 86400000 AS INTEGER)"
                  "  FROM aptitude_item WHERE attempt_id = ? AND position = ?",
                  (attempt_id, position), default=None)


def options(puzzle_id):
    return query("SELECT option_id, label, color_key FROM puzzle_option"
                 " WHERE puzzle_id = ? ORDER BY display_order", (puzzle_id,))


def elements(puzzle_id):
    return query("SELECT role, position, color_key, text_value FROM puzzle_element"
                 " WHERE puzzle_id = ? ORDER BY role, position", (puzzle_id,))


def answer(attempt_id, position, option_id, response_ms):
    with transaction() as tx:
        tx.execute("UPDATE aptitude_item SET response_ms = ?, selected_option_id = ?"
                   " WHERE attempt_id = ? AND position = ? AND answered_at IS NULL",
                   (response_ms, option_id, attempt_id, position))


def skip(attempt_id, position, response_ms):
    execute("UPDATE aptitude_item"
            "   SET response_ms = ?,"
            "       answered_at = strftime('%Y-%m-%d %H:%M:%f','now','localtime')"
            " WHERE attempt_id = ? AND position = ? AND answered_at IS NULL",
            (response_ms, attempt_id, position))


def complete(attempt_id):
    execute("UPDATE aptitude_attempt SET status = 'COMPLETED'"
            " WHERE attempt_id = ? AND status = 'IN_PROGRESS'", (attempt_id,))


def category_scores(attempt_id):
    return query("SELECT * FROM v_aptitude_category_score WHERE attempt_id = ?"
                 " ORDER BY display_order", (attempt_id,))


def review(attempt_id):
    return query(
        "SELECT i.position, i.is_correct, i.response_ms, i.selected_option_id,"
        "       p.puzzle_id, p.prompt, p.explanation, p.time_limit_sec,"
        "       c.code AS category_code, c.name AS category,"
        "       chosen.label AS chosen_label, chosen.color_key AS chosen_color,"
        "       right_opt.label AS correct_label, right_opt.color_key AS correct_color"
        "  FROM aptitude_item i"
        "  JOIN puzzle p          ON i.puzzle_id   = p.puzzle_id"
        "  JOIN puzzle_category c ON p.category_id = c.category_id"
        "  LEFT JOIN puzzle_option chosen    ON chosen.option_id = i.selected_option_id"
        "  JOIN puzzle_option right_opt      ON right_opt.puzzle_id = p.puzzle_id"
        "                                   AND right_opt.is_correct = 1"
        " WHERE i.attempt_id = ?"
        " ORDER BY i.position", (attempt_id,))


def review_elements(attempt_id):
    return query(
        "SELECT e.puzzle_id, e.role, e.position, e.color_key, e.text_value"
        "  FROM puzzle_element e"
        "  JOIN aptitude_item i ON i.puzzle_id = e.puzzle_id"
        " WHERE i.attempt_id = ?"
        " ORDER BY e.puzzle_id, e.role, e.position", (attempt_id,))


def for_student(student_id, completed_only=True, limit=20):
    clause = " AND status = 'COMPLETED'" if completed_only else ""
    return query(f"SELECT * FROM v_aptitude_summary WHERE student_id = ?{clause}"
                 " ORDER BY started_at DESC LIMIT ?", (student_id, limit))


def latest_for(student_id):
    rows = for_student(student_id, limit=1)
    return rows[0] if rows else None


def recent(limit=100):
    return query("SELECT * FROM v_aptitude_summary WHERE status = 'COMPLETED'"
                 " ORDER BY completed_at DESC LIMIT ?", (limit,))


def headline():
    return query(
        "SELECT COUNT(*) AS attempts,"
        "       COUNT(DISTINCT student_id) AS students,"
        "       ROUND(AVG(accuracy_pct), 1) AS avg_accuracy,"
        "       ROUND(AVG(avg_response_ms) / 1000.0, 1) AS avg_seconds"
        "  FROM aptitude_attempt WHERE status = 'COMPLETED'", one=True)


def bank_counts():
    return query(
        "SELECT c.name AS category, c.skill, g.label AS age_group, g.difficulty, COUNT(p.puzzle_id) AS puzzles"
        "  FROM puzzle_category c"
        " CROSS JOIN age_group g"
        "  LEFT JOIN puzzle p ON p.category_id = c.category_id"
        "                    AND p.age_group_id = g.age_group_id AND p.is_active = 1"
        " GROUP BY c.category_id, g.age_group_id"
        " ORDER BY c.display_order, g.difficulty")


def by_age_group():
    return query(
        "SELECT g.label, g.min_age, g.max_age,"
        "       COUNT(a.attempt_id) AS attempts,"
        "       ROUND(AVG(a.accuracy_pct), 1) AS avg_accuracy"
        "  FROM age_group g"
        "  LEFT JOIN aptitude_attempt a ON a.age_group_id = g.age_group_id"
        "                              AND a.status = 'COMPLETED'"
        " GROUP BY g.age_group_id ORDER BY g.difficulty")


def by_category():
    return query(
        "SELECT s.category, s.skill, SUM(s.puzzles) AS puzzles, SUM(s.correct) AS correct,"
        "       ROUND(100.0 * SUM(s.correct) / NULLIF(SUM(s.puzzles), 0), 1) AS accuracy_pct,"
        "       ROUND(AVG(s.avg_response_ms) / 1000.0, 1) AS avg_seconds"
        "  FROM v_aptitude_category_score s"
        "  JOIN aptitude_attempt a ON s.attempt_id = a.attempt_id AND a.status = 'COMPLETED'"
        " GROUP BY s.category_id ORDER BY MIN(s.display_order)")


def band_counts():
    return query(
        "SELECT b.label, b.color_hex, COUNT(a.attempt_id) AS n"
        "  FROM aptitude_band b"
        "  LEFT JOIN aptitude_attempt a ON a.band_id = b.band_id AND a.status = 'COMPLETED'"
        " GROUP BY b.band_id ORDER BY b.min_pct DESC")


def focus_vs_stress():
    return query(
        "SELECT sl.level_name, sl.color_hex,"
        "       COUNT(*) AS attempts,"
        "       ROUND(AVG(a.accuracy_pct), 1) AS avg_accuracy,"
        "       ROUND(AVG(a.avg_response_ms) / 1000.0, 1) AS avg_seconds"
        "  FROM aptitude_attempt a"
        "  JOIN assessment s ON s.assessment_id = ("
        "        SELECT x.assessment_id FROM assessment x"
        "         WHERE x.student_id = a.student_id AND x.created_at <= a.started_at"
        "         ORDER BY x.created_at DESC LIMIT 1)"
        "  JOIN stress_level sl ON s.predicted_level = sl.level_code"
        " WHERE a.status = 'COMPLETED'"
        " GROUP BY sl.level_code ORDER BY sl.level_code")


def hardest(limit=6):
    return query("SELECT * FROM v_puzzle_difficulty WHERE times_answered >= 3"
                 " ORDER BY pct_correct, times_answered DESC LIMIT ?", (limit,))
