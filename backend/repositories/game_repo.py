from backend.database import execute, query, scalar, transaction

ROUNDS = 8


def places():
    return query("SELECT * FROM place ORDER BY display_order")


def get(game_id):
    return query("SELECT * FROM v_rescue_summary WHERE game_id = ?", (game_id,), one=True)


def in_progress_for(student_id):
    return query("SELECT game_id, started_at,"
                 "       (JULIANDAY('now','localtime') - JULIANDAY(started_at)) * 24 AS hours_old"
                 "  FROM rescue_game"
                 " WHERE student_id = ? AND status = 'IN_PROGRESS'"
                 " ORDER BY started_at DESC LIMIT 1", (student_id,), one=True)


def abandon(game_id):
    execute("UPDATE rescue_game SET status = 'ABANDONED' WHERE game_id = ?", (game_id,))


def create_game(student_id, age_group_id, age):
    with transaction() as tx:
        cur = tx.execute("INSERT INTO rescue_game (student_id, age_group_id, age_at_play) VALUES (?,?,?)",
                         (student_id, age_group_id, age))
        game_id = cur.lastrowid
        picks = tx.execute("SELECT scenario_id FROM scenario"
                           " WHERE age_group_id = ? AND is_active = 1"
                           " ORDER BY is_opening DESC, RANDOM() LIMIT ?",
                           (age_group_id, ROUNDS)).fetchall()
        tx.executemany("INSERT INTO rescue_round (game_id, round_no, scenario_id) VALUES (?,?,?)",
                       [(game_id, n, row[0]) for n, row in enumerate(picks, start=1)])
    return game_id


def current_round(game_id):
    return query(
        "SELECT r.game_id, r.round_no, r.scenario_id, r.shown_at,"
        "       s.icon, s.title, s.story, s.urgency, s.time_limit_sec,"
        "       CASE WHEN r.shown_at IS NULL THEN s.time_limit_sec"
        "            ELSE s.time_limit_sec - (JULIANDAY('now','localtime') - JULIANDAY(r.shown_at)) * 86400"
        "       END AS seconds_left"
        "  FROM rescue_round r JOIN scenario s ON r.scenario_id = s.scenario_id"
        " WHERE r.game_id = ? AND r.answered_at IS NULL"
        " ORDER BY r.round_no LIMIT 1", (game_id,), one=True)


def round_detail(game_id, round_no):
    return query(
        "SELECT r.*, s.icon, s.title, s.story, s.explanation, s.time_limit_sec, s.correct_place_id,"
        "       right_place.name AS correct_place, right_place.code AS correct_code,"
        "       chosen.name AS chosen_place, chosen.code AS chosen_code"
        "  FROM rescue_round r"
        "  JOIN scenario s          ON r.scenario_id = s.scenario_id"
        "  JOIN place right_place   ON right_place.place_id = s.correct_place_id"
        "  LEFT JOIN place chosen   ON chosen.place_id = r.chosen_place_id"
        " WHERE r.game_id = ? AND r.round_no = ?", (game_id, round_no), one=True)


def progress(game_id):
    return query(
        "SELECT COUNT(*) AS total,"
        "       SUM(CASE WHEN answered_at IS NOT NULL THEN 1 ELSE 0 END) AS answered,"
        "       COALESCE(SUM(points), 0) AS points"
        "  FROM rescue_round WHERE game_id = ?", (game_id,), one=True)


def mark_shown(game_id, round_no):
    execute("UPDATE rescue_round"
            "   SET shown_at = strftime('%Y-%m-%d %H:%M:%f','now','localtime')"
            " WHERE game_id = ? AND round_no = ? AND shown_at IS NULL", (game_id, round_no))


def elapsed_ms(game_id, round_no):
    return scalar("SELECT CAST((JULIANDAY('now','localtime') - JULIANDAY(shown_at)) * 86400000 AS INTEGER)"
                  "  FROM rescue_round WHERE game_id = ? AND round_no = ?", (game_id, round_no), default=None)


def place_exists(place_id):
    return scalar("SELECT COUNT(*) FROM place WHERE place_id = ?", (place_id,)) == 1


def choose(game_id, round_no, place_id, response_ms):
    with transaction() as tx:
        tx.execute("UPDATE rescue_round SET response_ms = ?, chosen_place_id = ?"
                   " WHERE game_id = ? AND round_no = ? AND answered_at IS NULL",
                   (response_ms, place_id, game_id, round_no))


def time_out(game_id, round_no, response_ms):
    execute("UPDATE rescue_round"
            "   SET response_ms = ?,"
            "       answered_at = strftime('%Y-%m-%d %H:%M:%f','now','localtime')"
            " WHERE game_id = ? AND round_no = ? AND answered_at IS NULL",
            (response_ms, game_id, round_no))


def complete(game_id):
    execute("UPDATE rescue_game SET status = 'COMPLETED'"
            " WHERE game_id = ? AND status = 'IN_PROGRESS'", (game_id,))


def rounds(game_id):
    return query(
        "SELECT r.round_no, r.is_correct, r.points, r.response_ms, r.chosen_place_id,"
        "       s.icon, s.title, s.explanation, right_place.name AS correct_place,"
        "       chosen.name AS chosen_place"
        "  FROM rescue_round r"
        "  JOIN scenario s        ON r.scenario_id = s.scenario_id"
        "  JOIN place right_place ON right_place.place_id = s.correct_place_id"
        "  LEFT JOIN place chosen ON chosen.place_id = r.chosen_place_id"
        " WHERE r.game_id = ? ORDER BY r.round_no", (game_id,))


def for_student(student_id, completed_only=True, limit=20):
    clause = " AND status = 'COMPLETED'" if completed_only else ""
    return query(f"SELECT * FROM v_rescue_summary WHERE student_id = ?{clause}"
                 " ORDER BY started_at DESC LIMIT ?", (student_id, limit))


def latest_for(student_id):
    rows = for_student(student_id, limit=1)
    return rows[0] if rows else None


def best_for(student_id):
    return query("SELECT MAX(score) AS best, COUNT(*) AS played FROM rescue_game"
                 " WHERE student_id = ? AND status = 'COMPLETED'", (student_id,), one=True)


def recent(limit=100):
    return query("SELECT * FROM v_rescue_summary WHERE status = 'COMPLETED'"
                 " ORDER BY completed_at DESC LIMIT ?", (limit,))


def headline():
    return query(
        "SELECT COUNT(*) AS games,"
        "       COUNT(DISTINCT student_id) AS students,"
        "       ROUND(AVG(accuracy_pct), 1) AS avg_accuracy,"
        "       ROUND(AVG(score), 1) AS avg_score,"
        "       ROUND(AVG(avg_response_ms) / 1000.0, 1) AS avg_seconds"
        "  FROM rescue_game WHERE status = 'COMPLETED'", one=True)


def confusion():
    return query("SELECT * FROM v_place_confusion ORDER BY correct_order, chosen_order")


def hardest(limit=6):
    return query("SELECT * FROM v_scenario_stats WHERE plays >= 3"
                 " ORDER BY pct_correct, plays DESC LIMIT ?", (limit,))


def by_age_group():
    return query(
        "SELECT g.label, g.min_age, g.max_age,"
        "       (SELECT COUNT(*) FROM scenario s WHERE s.age_group_id = g.age_group_id AND s.is_active = 1) AS scenarios,"
        "       COUNT(r.game_id) AS games,"
        "       ROUND(AVG(r.accuracy_pct), 1) AS avg_accuracy"
        "  FROM age_group g"
        "  LEFT JOIN rescue_game r ON r.age_group_id = g.age_group_id AND r.status = 'COMPLETED'"
        " GROUP BY g.age_group_id ORDER BY g.difficulty")


def star_counts():
    return query("SELECT stars, COUNT(*) AS n FROM rescue_game WHERE status = 'COMPLETED'"
                 " GROUP BY stars ORDER BY stars DESC")
