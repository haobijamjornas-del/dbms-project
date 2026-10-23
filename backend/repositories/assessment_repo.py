from backend.database import query, transaction


def detail(assessment_id):
    return query("SELECT * FROM v_assessment_detail WHERE assessment_id = ?",
                 (assessment_id,), one=True)


def for_student(student_id, limit=25):
    return query("SELECT * FROM v_assessment_detail WHERE student_id = ?"
                 " ORDER BY created_at DESC LIMIT ?", (student_id, limit))


def history(student_id, limit=6):
    return query(
        "SELECT assessment_id, created_at, stress_level AS level_name,"
        "       confidence_pct FROM v_assessment_detail WHERE student_id = ?"
        " ORDER BY created_at DESC LIMIT ?", (student_id, limit))


def scores(assessment_id):
    return query(
        "SELECT sc.level_code, sl.level_name, sl.color_hex, sc.probability"
        "  FROM assessment_score sc"
        "  JOIN stress_level sl ON sc.level_code = sl.level_code"
        " WHERE sc.assessment_id = ? ORDER BY sl.severity_rank", (assessment_id,))


def keywords(assessment_id):
    return query(
        "SELECT k.word, k.category, k.weight, k.polarity, ak.occurrences"
        "  FROM assessment_keyword ak"
        "  JOIN keyword_lexicon k ON ak.keyword_id = k.keyword_id"
        " WHERE ak.assessment_id = ? ORDER BY k.weight DESC", (assessment_id,))


def create(student_id, model_id, text, result, theme_id, source="web"):
    with transaction() as tx:
        cur = tx.execute(
            "INSERT INTO assessment (student_id, model_id, entry_text, char_count,"
            " word_count, predicted_level, confidence, predicted_theme, source)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (student_id, model_id, text, len(text), len(text.split()),
             result["level"], result["confidence"], theme_id, source))
        assessment_id = cur.lastrowid

        tx.executemany(
            "INSERT INTO assessment_score (assessment_id, level_code, probability)"
            " VALUES (?,?,?)",
            [(assessment_id, lvl, p)
             for lvl, p in enumerate(result["probabilities"])])

        words = set(result["keywords"])
        if words:
            placeholders = ",".join("?" * len(words))
            hits = tx.execute(
                f"SELECT keyword_id, word FROM keyword_lexicon"
                f" WHERE word IN ({placeholders})", tuple(words)).fetchall()
            if hits:
                tx.executemany(
                    "INSERT INTO assessment_keyword (assessment_id, keyword_id,"
                    " occurrences) VALUES (?,?,?)",
                    [(assessment_id, h["keyword_id"],
                      result["keywords"].count(h["word"])) for h in hits])

        if result.get("crisis_flagged"):
            tx.execute(
                "UPDATE alert SET alert_type = 'CRISIS_KEYWORD',"
                " priority = 'CRITICAL',"
                " remarks = 'Explicit crisis language detected by rule-based override.'"
                " WHERE assessment_id = ?", (assessment_id,))
        return assessment_id
