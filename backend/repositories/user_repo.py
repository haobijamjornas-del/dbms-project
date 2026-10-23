from backend.database import execute, query


def get_by_id(user_id):
    return query("SELECT * FROM app_user WHERE user_id = ? AND is_active = 1",
                 (user_id,), one=True)


def get_by_username(username):
    return query(
        "SELECT u.*, s.full_name AS student_name, c.full_name AS counsellor_name"
        "  FROM app_user u"
        "  LEFT JOIN student    s ON u.student_id    = s.student_id"
        "  LEFT JOIN counsellor c ON u.counsellor_id = c.counsellor_id"
        " WHERE LOWER(u.username) = LOWER(?) AND u.is_active = 1",
        (username,), one=True)


def username_taken(username):
    return query("SELECT 1 FROM app_user WHERE LOWER(username) = LOWER(?)",
                 (username,), one=True) is not None


def touch_login(user_id):
    execute("UPDATE app_user SET last_login = datetime('now','localtime') WHERE user_id = ?",
            (user_id,))


def sample_student_username():
    row = query("SELECT username FROM app_user WHERE role = 'student'"
                " ORDER BY user_id LIMIT 1", one=True)
    return row["username"] if row else ""
