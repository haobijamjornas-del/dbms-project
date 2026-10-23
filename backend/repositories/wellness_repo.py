from backend.database import execute, query


def for_student(student_id, limit=30):
    return query("SELECT * FROM v_wellness_vs_stress WHERE student_id = ?"
                 " ORDER BY log_date DESC LIMIT ?", (student_id, limit))


def raw_for_student(student_id, limit=14):
    return query(
        "SELECT log_date, sleep_hours, mood_rating, exercise_min, screen_time_hrs"
        "  FROM wellness_log WHERE student_id = ?"
        " ORDER BY log_date DESC LIMIT ?", (student_id, limit))


def averages(student_id, days=30):
    return query(
        "SELECT ROUND(AVG(sleep_hours),1) AS sleep,"
        "       ROUND(AVG(mood_rating),1) AS mood,"
        "       ROUND(AVG(exercise_min),0) AS exercise,"
        "       ROUND(AVG(screen_time_hrs),1) AS screen"
        "  FROM wellness_log WHERE student_id = ?"
        "   AND log_date >= DATE('now','localtime', ?)", (student_id, f"-{days} days"), one=True)


def set_mood(student_id, log_date, rating):
    return execute(
        "INSERT INTO wellness_log (student_id, log_date, mood_rating) VALUES (?,?,?)"
        " ON CONFLICT(student_id, log_date) DO UPDATE SET mood_rating = excluded.mood_rating",
        (student_id, log_date, rating))


def upsert(student_id, data):
    return execute(
        "INSERT INTO wellness_log (student_id, log_date, sleep_hours,"
        " exercise_min, mood_rating, screen_time_hrs) VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(student_id, log_date) DO UPDATE SET"
        "   sleep_hours = excluded.sleep_hours,"
        "   exercise_min = excluded.exercise_min,"
        "   mood_rating = excluded.mood_rating,"
        "   screen_time_hrs = excluded.screen_time_hrs",
        (student_id, data["log_date"], data.get("sleep_hours"),
         data.get("exercise_min"), data.get("mood_rating"),
         data.get("screen_time_hrs")))
