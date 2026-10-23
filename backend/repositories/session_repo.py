from backend.database import execute, query, scalar

_SELECT = """
SELECT cs.*, s.full_name AS student_name, s.enrollment_no,
       c.full_name AS counsellor_name, d.dept_code
  FROM counselling_session cs
  JOIN student    s ON cs.student_id    = s.student_id
  JOIN counsellor c ON cs.counsellor_id = c.counsellor_id
  JOIN department d ON s.dept_id        = d.dept_id
"""


def search(status="SCHEDULED", page=1, per_page=50):
    clause, params = ("cs.status = ?", (status,)) if status != "ALL" else ("1 = 1", ())
    total = scalar(f"SELECT COUNT(*) FROM counselling_session cs WHERE {clause}",
                   params)
    rows = query(f"{_SELECT} WHERE {clause} ORDER BY cs.scheduled_at DESC"
                 f" LIMIT ? OFFSET ?", params + (per_page, (page - 1) * per_page))
    return rows, total


def get(session_id):
    return query(f"{_SELECT} WHERE cs.session_id = ?", (session_id,), one=True)


def for_student(student_id, limit=None):
    sql = (f"{_SELECT} WHERE cs.student_id = ? ORDER BY cs.scheduled_at DESC")
    if limit:
        return query(sql + " LIMIT ?", (student_id, limit))
    return query(sql, (student_id,))


def status_counts():
    return {r["status"]: r["n"] for r in query(
        "SELECT status, COUNT(*) AS n FROM counselling_session GROUP BY status")}


def workload():
    return query("SELECT * FROM v_counsellor_workload ORDER BY full_name")


def create(data):
    return execute(
        "INSERT INTO counselling_session (student_id, counsellor_id, alert_id,"
        " scheduled_at, duration_min, mode, notes) VALUES (?,?,?,?,?,?,?)",
        (data["student_id"], data["counsellor_id"], data.get("alert_id"),
         data["scheduled_at"], data["duration_min"], data["mode"],
         data.get("notes")))


def set_status(session_id, status):
    execute("UPDATE counselling_session SET status = ? WHERE session_id = ?",
            (status, session_id))


def set_notes(session_id, notes):
    execute("UPDATE counselling_session SET notes = ? WHERE session_id = ?",
            (notes, session_id))
