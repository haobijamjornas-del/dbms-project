import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "mindcare.db")
OUT_PATH = os.path.join(BASE_DIR, "sql", "mysql_data.sql")

TABLE_ORDER = [
    "department", "stress_level", "theme", "counsellor", "student", "app_user",
    "ml_model", "training_corpus", "keyword_lexicon", "assessment",
    "assessment_score", "assessment_keyword", "alert", "counselling_session",
    "wellness_log", "helpline", "support_tip",
    "instrument", "instrument_item", "response_option", "severity_band",
    "screening", "screening_response", "screening_score",
    "age_group", "puzzle_category", "aptitude_band", "puzzle", "puzzle_option",
    "puzzle_element", "aptitude_attempt", "aptitude_item",
    "place", "scenario", "rescue_game", "rescue_round",
]

BATCH = 200

PAUSED_TRIGGERS = {
    "mysql_schema.sql": ["trg_alert_on_high_stress", "trg_escalate_repeated_high"],
    "mysql_screening.sql": ["trg_score_screening", "trg_critical_item_escalation",
                            "trg_response_value_in_scale"],
}


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    s = str(value)
    s = s.replace("\\", "\\\\").replace("'", "''").replace("\r", " ").replace("\n", " ")
    return f"'{s}'"


def trigger_definitions():
    blocks = []
    for filename, names in PAUSED_TRIGGERS.items():
        text = open(os.path.join(BASE_DIR, "sql", filename)).read()
        for name in names:
            match = re.search(r"CREATE TRIGGER %s\b.*?END\$\$" % name, text, re.S)
            if not match:
                raise SystemExit(f"Trigger {name} was not found in sql/{filename}")
            blocks.append((name, match.group(0)))
    return blocks


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit("mindcare.db not found. Run: python init_db.py")

    triggers = trigger_definitions()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    total = 0

    with open(OUT_PATH, "w") as out:
        out.write("USE mindcare;\n")
        out.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        out.write("SET AUTOCOMMIT = 0;\n")
        for name, _ in triggers:
            out.write(f"DROP TRIGGER IF EXISTS {name};\n")
        out.write("START TRANSACTION;\n\n")

        for table in TABLE_ORDER:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue
            cols = rows[0].keys()
            quoted = ", ".join(f"`{c}`" for c in cols)
            for i in range(0, len(rows), BATCH):
                chunk = rows[i:i + BATCH]
                out.write(f"INSERT INTO `{table}` ({quoted}) VALUES\n")
                values = [
                    "  (" + ", ".join(literal(r[c]) for c in cols) + ")"
                    for r in chunk
                ]
                out.write(",\n".join(values) + ";\n")
            out.write("\n")
            total += len(rows)
            print(f"    {table:<24} {len(rows):>6} rows")

        out.write("COMMIT;\n")
        out.write("SET FOREIGN_KEY_CHECKS = 1;\n")
        out.write("SET AUTOCOMMIT = 1;\n\n")
        out.write("DELIMITER $$\n\n")
        for _, body in triggers:
            out.write(body + "\n\n")
        out.write("DELIMITER ;\n")

    conn.close()
    size = os.path.getsize(OUT_PATH) / 1024 / 1024
    print(f"\n    wrote sql/mysql_data.sql  -  {total} rows, {size:.2f} MB, "
          f"{len(triggers)} triggers paused during the load and restored after it")


if __name__ == "__main__":
    main()
