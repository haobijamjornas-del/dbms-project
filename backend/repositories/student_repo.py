from backend.database import query, scalar

RISK_BANDS = {
    "high":   "risk_index >= 50",
    "medium": "risk_index >= 25 AND risk_index < 50",
    "low":    "risk_index < 25",
}


def _filters(q=None, dept=None, year=None, risk=None):
    where, params = ["1 = 1"], []
    if q:
        where.append("(full_name LIKE ? OR enrollment_no LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if dept:
        where.append("student_id IN (SELECT student_id FROM student WHERE dept_id = ?)")
        params.append(dept)
    if year:
        where.append("year_of_study = ?")
        params.append(year)
    if risk in RISK_BANDS:
        where.append(RISK_BANDS[risk])
    return " AND ".join(where), tuple(params)


SORTABLE = {
    "name":       "full_name",
    "risk":       "risk_index",
    "entries":    "total_assessments",
    "high":       "high_count",
    "avg":        "avg_stress_score",
    "year":       "year_of_study",
    "dept":       "dept_code",
    "last":       "last_assessed_at",
}


def search(q=None, dept=None, year=None, risk=None, page=1, per_page=15,
           sort="risk", direction="desc"):
    clause, params = _filters(q, dept, year, risk)
    total = scalar(f"SELECT COUNT(*) FROM v_student_risk_profile WHERE {clause}",
                   params)
    column = SORTABLE.get(sort, "risk_index")
    order = "ASC" if str(direction).lower() == "asc" else "DESC"
    rows = query(
        f"SELECT * FROM v_student_risk_profile WHERE {clause}"
        f" ORDER BY {column} {order}, full_name ASC LIMIT ? OFFSET ?",
        params + (per_page, (page - 1) * per_page))
    return rows, total


def get(student_id):
    return query(
        "SELECT s.*, d.dept_code, d.dept_name FROM student s"
        "  JOIN department d ON s.dept_id = d.dept_id"
        " WHERE s.student_id = ?", (student_id,), one=True)


def profile(student_id):
    return query("SELECT * FROM v_student_risk_profile WHERE student_id = ?",
                 (student_id,), one=True)


def at_risk(limit=8):
    return query("SELECT * FROM v_student_risk_profile WHERE total_assessments > 0"
                 " ORDER BY risk_index DESC, high_count DESC LIMIT ?", (limit,))


def options():
    return query("SELECT student_id, enrollment_no, full_name FROM student"
                 " WHERE is_active = 1 ORDER BY full_name")


def enrollment_taken(enrollment_no):
    return query("SELECT 1 FROM student WHERE LOWER(enrollment_no) = LOWER(?)",
                 (enrollment_no,), one=True) is not None


def email_taken(email):
    return query("SELECT 1 FROM student WHERE LOWER(email) = LOWER(?)",
                 (email,), one=True) is not None


def theme_breakdown(student_id, limit=8):
    return query(
        "SELECT t.theme_name, COUNT(*) AS n,"
        "       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high"
        "  FROM assessment a JOIN theme t ON a.predicted_theme = t.theme_id"
        " WHERE a.student_id = ? GROUP BY t.theme_name"
        " ORDER BY n DESC LIMIT ?", (student_id, limit))


def daily_trend(student_id, days=None):
    clause = " AND created_at >= DATE('now','localtime', ?)" if days else ""
    params = (student_id, f"-{days} days") if days else (student_id,)
    return query(
        f"SELECT DATE(created_at) AS d, ROUND(AVG(predicted_level),2) AS avg_lvl,"
        f"       COUNT(*) AS n FROM assessment WHERE student_id = ?{clause}"
        f" GROUP BY DATE(created_at) ORDER BY d", params)
