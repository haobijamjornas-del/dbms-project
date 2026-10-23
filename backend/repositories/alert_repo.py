from backend.database import execute, query, scalar

PRIORITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED")

_FULL_SELECT = """
SELECT al.alert_id, al.priority, al.status, al.alert_type, al.raised_at,
       al.acknowledged_at, al.resolved_at, al.remarks,
       s.student_id, s.enrollment_no, s.full_name AS student_name, s.phone,
       d.dept_code, a.assessment_id, a.entry_text,
       ROUND(a.confidence * 100, 1) AS confidence_pct, t.theme_name,
       c.full_name AS assigned_counsellor,
       CASE al.priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3 ELSE 4 END AS priority_rank
  FROM alert al
  JOIN assessment a  ON al.assessment_id  = a.assessment_id
  JOIN student    s  ON a.student_id      = s.student_id
  JOIN department d  ON s.dept_id         = d.dept_id
  LEFT JOIN theme      t ON a.predicted_theme = t.theme_id
  LEFT JOIN counsellor c ON al.assigned_to    = c.counsellor_id
"""


def search(status="OPEN", priority=None, counsellor_id=None, page=1, per_page=50):
    where, params = [], []
    if status and status != "ALL":
        where.append("al.status = ?")
        params.append(status)
    if priority:
        where.append("al.priority = ?")
        params.append(priority)
    if counsellor_id:
        where.append("al.assigned_to = ?")
        params.append(counsellor_id)
    clause = " AND ".join(where) if where else "1 = 1"

    total = scalar(f"SELECT COUNT(*) FROM alert al WHERE {clause}", tuple(params))
    rows = query(f"{_FULL_SELECT} WHERE {clause}"
                 f" ORDER BY priority_rank, al.raised_at DESC LIMIT ? OFFSET ?",
                 tuple(params) + (per_page, (page - 1) * per_page))
    return rows, total


def get(alert_id):
    return query(f"{_FULL_SELECT} WHERE al.alert_id = ?", (alert_id,), one=True)


def for_assessment(assessment_id):
    return query("SELECT al.*, c.full_name AS counsellor_name FROM alert al"
                 "  LEFT JOIN counsellor c ON al.assigned_to = c.counsellor_id"
                 " WHERE al.assessment_id = ?", (assessment_id,), one=True)


def for_student(student_id, limit=10):
    return query(
        "SELECT al.*, c.full_name AS counsellor_name FROM alert al"
        "  JOIN assessment a ON al.assessment_id = a.assessment_id"
        "  LEFT JOIN counsellor c ON al.assigned_to = c.counsellor_id"
        " WHERE a.student_id = ? ORDER BY al.raised_at DESC LIMIT ?",
        (student_id, limit))


def queue(limit=8):
    return query("SELECT * FROM v_high_risk_queue"
                 " ORDER BY priority_rank, raised_at DESC LIMIT ?", (limit,))


def status_counts():
    return {r["status"]: r["n"] for r in
            query("SELECT status, COUNT(*) AS n FROM alert GROUP BY status")}


def set_status(alert_id, status):
    execute("UPDATE alert SET status = ? WHERE alert_id = ?", (status, alert_id))


def assign(alert_id, counsellor_id):
    execute("UPDATE alert SET assigned_to = ? WHERE alert_id = ?",
            (counsellor_id, alert_id))


def set_remarks(alert_id, remarks):
    execute("UPDATE alert SET remarks = ? WHERE alert_id = ?", (remarks, alert_id))


def open_for_booking(limit=60):
    return query(
        "SELECT al.alert_id, s.full_name, s.enrollment_no FROM alert al"
        "  JOIN assessment a ON al.assessment_id = a.assessment_id"
        "  JOIN student s ON a.student_id = s.student_id"
        " WHERE al.status IN ('OPEN','ACKNOWLEDGED')"
        " ORDER BY al.raised_at DESC LIMIT ?", (limit,))
