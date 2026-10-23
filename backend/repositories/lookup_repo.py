from backend.database import query


def departments():
    return query("SELECT dept_id, dept_code, dept_name, hod_name FROM department"
                 " ORDER BY dept_code")


def stress_levels():
    return query("SELECT * FROM stress_level ORDER BY severity_rank")


def level_mix():
    return query(
        "SELECT sl.level_code, sl.level_name, sl.color_hex,"
        "       COUNT(a.assessment_id) AS n"
        "  FROM stress_level sl"
        "  LEFT JOIN assessment a ON sl.level_code = a.predicted_level"
        " GROUP BY sl.level_code ORDER BY sl.severity_rank")


def theme_by_code(code):
    return query("SELECT theme_id FROM theme WHERE theme_code = ?", (code,), one=True)


def theme_code_by_name(name):
    return query("SELECT theme_code FROM theme WHERE theme_name = ?",
                 (name,), one=True)


def level_guidance(level_code):
    return query("SELECT description FROM stress_level WHERE level_code = ?",
                 (level_code,), one=True)


def counsellors(active_only=True):
    clause = " WHERE is_active = 1" if active_only else ""
    return query(f"SELECT counsellor_id, emp_code, full_name, specialization"
                 f"  FROM counsellor{clause} ORDER BY full_name")


def active_model():
    return query("SELECT * FROM ml_model WHERE is_active = 1", one=True)


def instruments():
    return query("SELECT * FROM instrument WHERE is_active = 1"
                 " ORDER BY display_order")


def total_instrument_items():
    from backend.database import scalar
    return scalar("SELECT COUNT(*) FROM instrument_item ii"
                  "  JOIN instrument i ON ii.instrument_id = i.instrument_id"
                  " WHERE i.is_active = 1")
