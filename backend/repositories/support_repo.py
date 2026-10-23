from backend.database import query

REGION_ORDER = ("CASE region WHEN 'Emergency' THEN 0 WHEN 'National' THEN 1"
                " WHEN 'Delhi NCR' THEN 2 ELSE 3 END")


def tips_for(level_code, tip_type):
    return query("SELECT title, body FROM support_tip"
                 " WHERE level_code = ? AND tip_type = ? ORDER BY display_order",
                 (level_code, tip_type))


def helplines():
    return query(f"SELECT * FROM helpline WHERE is_active = 1"
                 f" ORDER BY {REGION_ORDER}, display_order")
