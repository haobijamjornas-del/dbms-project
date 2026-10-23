import os

from flask import current_app

from backend.database import execute, query, scalar


def models():
    return query("SELECT * FROM ml_model ORDER BY is_active DESC, f1_macro DESC")


def model_usage():
    return query(
        "SELECT m.model_id, m.algorithm, COUNT(a.assessment_id) AS predictions"
        "  FROM ml_model m LEFT JOIN assessment a ON m.model_id = a.model_id"
        " GROUP BY m.model_id ORDER BY predictions DESC")


def activate_model(model_id):
    execute("UPDATE ml_model SET is_active = 1 WHERE model_id = ?", (model_id,))


def corpus_stats():
    return query(
        "SELECT sl.level_name, tc.split, COUNT(*) AS n FROM training_corpus tc"
        "  JOIN stress_level sl ON tc.label = sl.level_code"
        " GROUP BY sl.level_name, tc.split ORDER BY sl.level_name, tc.split")


def schema_objects():
    tables = []
    for t in query("SELECT name, sql FROM sqlite_master WHERE type='table'"
                   " AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        tables.append({
            "name": t["name"],
            "sql": t["sql"],
            "rows": scalar(f"SELECT COUNT(*) FROM {t['name']}"),
            "columns": query(f"PRAGMA table_info({t['name']})"),
            "foreign_keys": query(f"PRAGMA foreign_key_list({t['name']})"),
            "indexes": query(f"PRAGMA index_list({t['name']})"),
        })
    return {
        "tables": tables,
        "views": query("SELECT name, sql FROM sqlite_master WHERE type='view'"
                       " ORDER BY name"),
        "triggers": query("SELECT name, tbl_name, sql FROM sqlite_master"
                          " WHERE type='trigger' ORDER BY name"),
        "db_size": round(
            os.path.getsize(current_app.config["DATABASE_PATH"]) / 1024 / 1024, 2),
    }
