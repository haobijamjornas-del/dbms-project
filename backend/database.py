import re
import sqlite3
from contextlib import contextmanager

from flask import current_app, g


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transaction():
    db = get_db()
    try:
        db.execute("BEGIN")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def scalar(sql, params=(), default=0):
    row = query(sql, params, one=True)
    if row is None or row[0] is None:
        return default
    return row[0]


def exists(sql, params=()):
    return query(sql, params, one=True) is not None


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    last = cur.lastrowid
    cur.close()
    return last


def execute_many(sql, seq):
    db = get_db()
    db.executemany(sql, seq)
    db.commit()


FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|"
    r"vacuum|reindex|truncate)\b", re.IGNORECASE)


def run_readonly_sql(sql, limit=None):
    limit = limit or current_app.config["SQL_CONSOLE_ROW_LIMIT"]
    stmt = sql.strip().rstrip(";")
    if not stmt:
        raise ValueError("Empty statement.")
    if ";" in stmt:
        raise ValueError("Only one statement may be run at a time.")
    if not re.match(r"^\s*(select|with|explain)\b", stmt, re.IGNORECASE):
        raise ValueError("Only SELECT / WITH / EXPLAIN statements are allowed here.")
    if FORBIDDEN.search(stmt):
        raise ValueError("Data-modifying keywords are blocked in this console.")

    uri = f"file:{current_app.config['DATABASE_PATH']}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(stmt)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(limit)
        truncated = cur.fetchone() is not None
        return cols, [list(r) for r in rows], truncated
    finally:
        conn.close()
