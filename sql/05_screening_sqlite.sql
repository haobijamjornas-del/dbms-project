PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS screening_score;
DROP TABLE IF EXISTS screening_response;
DROP TABLE IF EXISTS screening;
DROP TABLE IF EXISTS severity_band;
DROP TABLE IF EXISTS response_option;
DROP TABLE IF EXISTS instrument_item;
DROP TABLE IF EXISTS instrument;

CREATE TABLE instrument (
    instrument_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(15)  NOT NULL UNIQUE,
    name          VARCHAR(60)  NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    measures      VARCHAR(40)  NOT NULL,
    recall_period VARCHAR(40)  NOT NULL,
    item_count    INTEGER      NOT NULL,
    option_min    INTEGER      NOT NULL DEFAULT 0,
    option_max    INTEGER      NOT NULL,
    score_min     INTEGER      NOT NULL DEFAULT 0,
    score_max     INTEGER      NOT NULL,
    weight        REAL         NOT NULL DEFAULT 1.0,
    display_order INTEGER      NOT NULL,
    source_note   VARCHAR(200),
    is_active     INTEGER      NOT NULL DEFAULT 1,
    CONSTRAINT chk_instr_items  CHECK (item_count > 0),
    CONSTRAINT chk_instr_range  CHECK (option_max > option_min),
    CONSTRAINT chk_instr_score  CHECK (score_max > score_min),
    CONSTRAINT chk_instr_weight CHECK (weight BETWEEN 0 AND 1),
    CONSTRAINT chk_instr_active CHECK (is_active IN (0,1))
);

CREATE TABLE instrument_item (
    item_id        INTEGER      PRIMARY KEY AUTOINCREMENT,
    instrument_id  INTEGER      NOT NULL,
    item_no        INTEGER      NOT NULL,
    question_text  VARCHAR(300) NOT NULL,
    reverse_scored INTEGER      NOT NULL DEFAULT 0,
    is_critical    INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT fk_item_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT uq_item_no    UNIQUE (instrument_id, item_no),
    CONSTRAINT chk_item_no   CHECK (item_no > 0),
    CONSTRAINT chk_reverse   CHECK (reverse_scored IN (0,1)),
    CONSTRAINT chk_critical  CHECK (is_critical IN (0,1))
);

CREATE TABLE response_option (
    option_id     INTEGER      PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER      NOT NULL,
    option_value  INTEGER      NOT NULL,
    option_label  VARCHAR(40)  NOT NULL,
    CONSTRAINT fk_opt_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT uq_opt_value UNIQUE (instrument_id, option_value)
);

CREATE TABLE severity_band (
    band_id       INTEGER      PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER      NOT NULL,
    band_name     VARCHAR(30)  NOT NULL,
    min_score     INTEGER      NOT NULL,
    max_score     INTEGER      NOT NULL,
    severity_rank INTEGER      NOT NULL,
    color_hex     CHAR(7)      NOT NULL,
    guidance      VARCHAR(300),
    CONSTRAINT fk_band_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT uq_band_name  UNIQUE (instrument_id, band_name),
    CONSTRAINT chk_band_span CHECK (max_score >= min_score)
);

CREATE TABLE screening (
    screening_id    INTEGER      PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER      NOT NULL,
    status          VARCHAR(12)  NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    completed_at    TIMESTAMP,
    assessment_id   INTEGER      UNIQUE,
    composite_score REAL,
    composite_band  VARCHAR(20),
    is_baseline     INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT fk_scr_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_scr_asmt    FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE SET NULL,
    CONSTRAINT chk_scr_status CHECK (status IN ('IN_PROGRESS','COMPLETED','ABANDONED')),
    CONSTRAINT chk_scr_comp   CHECK (composite_score IS NULL
                                     OR composite_score BETWEEN 0 AND 100),
    CONSTRAINT chk_baseline   CHECK (is_baseline IN (0,1))
);

CREATE TABLE screening_response (
    screening_id INTEGER   NOT NULL,
    item_id      INTEGER   NOT NULL,
    option_value INTEGER   NOT NULL,
    answered_at  TIMESTAMP NOT NULL DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (screening_id, item_id),
    CONSTRAINT fk_resp_scr  FOREIGN KEY (screening_id)
        REFERENCES screening (screening_id) ON DELETE CASCADE,
    CONSTRAINT fk_resp_item FOREIGN KEY (item_id)
        REFERENCES instrument_item (item_id) ON DELETE CASCADE,
    CONSTRAINT chk_resp_val CHECK (option_value >= 0)
);

CREATE TABLE screening_score (
    screening_id   INTEGER NOT NULL,
    instrument_id  INTEGER NOT NULL,
    raw_score      INTEGER NOT NULL,
    band_id        INTEGER,
    items_answered INTEGER NOT NULL,
    normalised_pct REAL,
    PRIMARY KEY (screening_id, instrument_id),
    CONSTRAINT fk_score_scr   FOREIGN KEY (screening_id)
        REFERENCES screening (screening_id) ON DELETE CASCADE,
    CONSTRAINT fk_score_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT fk_score_band  FOREIGN KEY (band_id)
        REFERENCES severity_band (band_id) ON UPDATE CASCADE,
    CONSTRAINT chk_raw        CHECK (raw_score >= 0),
    CONSTRAINT chk_norm       CHECK (normalised_pct IS NULL
                                     OR normalised_pct BETWEEN 0 AND 100)
);

CREATE INDEX idx_scr_student      ON screening (student_id, started_at DESC);
CREATE INDEX idx_scr_status       ON screening (status);
CREATE INDEX idx_scr_band         ON screening (composite_band);
CREATE INDEX idx_resp_item        ON screening_response (item_id);
CREATE INDEX idx_sscore_instr     ON screening_score (instrument_id, raw_score);
CREATE INDEX idx_item_instrument  ON instrument_item (instrument_id, item_no);
CREATE INDEX idx_band_instrument  ON severity_band (instrument_id, min_score, max_score);

DROP VIEW IF EXISTS v_screening_summary;
DROP VIEW IF EXISTS v_screening_subscale;
DROP VIEW IF EXISTS v_item_response_stats;
DROP VIEW IF EXISTS v_student_screening_latest;

CREATE VIEW v_screening_summary AS
SELECT  sc.screening_id,
        sc.student_id,
        s.enrollment_no,
        s.full_name       AS student_name,
        d.dept_code,
        s.year_of_study,
        sc.status,
        sc.started_at,
        sc.completed_at,
        sc.is_baseline,
        ROUND(sc.composite_score, 2) AS composite_score,
        sc.composite_band,
        ROUND((JULIANDAY(sc.completed_at) - JULIANDAY(sc.started_at)) * 1440, 1)
                                     AS minutes_taken,
        sc.assessment_id,
        a.entry_text,
        sl.level_name     AS text_level,
        ROUND(a.confidence * 100, 1) AS text_confidence_pct,
        t.theme_name      AS text_theme,
        (SELECT COUNT(*) FROM screening_response r
          WHERE r.screening_id = sc.screening_id)          AS items_answered,
        (SELECT COUNT(*) FROM screening_response r
           JOIN instrument_item ii ON r.item_id = ii.item_id
          WHERE r.screening_id = sc.screening_id
            AND ii.is_critical = 1 AND r.option_value > 0)  AS critical_flags
FROM        screening    sc
INNER JOIN  student      s  ON sc.student_id    = s.student_id
INNER JOIN  department   d  ON s.dept_id        = d.dept_id
LEFT  JOIN  assessment   a  ON sc.assessment_id = a.assessment_id
LEFT  JOIN  stress_level sl ON a.predicted_level = sl.level_code
LEFT  JOIN  theme        t  ON a.predicted_theme = t.theme_id;

CREATE VIEW v_screening_subscale AS
SELECT  ss.screening_id,
        sc.student_id,
        sc.completed_at,
        i.instrument_id,
        i.code            AS instrument_code,
        i.name            AS instrument_name,
        i.measures,
        i.display_order,
        ss.raw_score,
        i.score_max,
        ss.items_answered,
        i.item_count,
        ROUND(ss.normalised_pct, 1) AS normalised_pct,
        b.band_name,
        b.severity_rank,
        b.color_hex,
        b.guidance
FROM        screening_score ss
INNER JOIN  screening       sc ON ss.screening_id  = sc.screening_id
INNER JOIN  instrument      i  ON ss.instrument_id = i.instrument_id
LEFT  JOIN  severity_band   b  ON ss.band_id       = b.band_id;

CREATE VIEW v_item_response_stats AS
SELECT  ii.item_id,
        i.code            AS instrument_code,
        ii.item_no,
        ii.question_text,
        ii.reverse_scored,
        ii.is_critical,
        i.option_max,
        COUNT(r.screening_id)                       AS times_answered,
        ROUND(AVG(r.option_value), 3)               AS avg_raw,
        ROUND(AVG(r.option_value) * 100.0 / i.option_max, 1) AS avg_pct_of_max,
        SUM(CASE WHEN r.option_value >= i.option_max - 1 THEN 1 ELSE 0 END)
                                                    AS high_answers
FROM        instrument_item    ii
INNER JOIN  instrument         i ON ii.instrument_id = i.instrument_id
LEFT  JOIN  screening_response r ON ii.item_id       = r.item_id
GROUP BY    ii.item_id, i.code, ii.item_no, ii.question_text,
            ii.reverse_scored, ii.is_critical, i.option_max;

CREATE VIEW v_student_screening_latest AS
SELECT  *
FROM   (SELECT sc.student_id,
               sc.screening_id,
               sc.completed_at,
               sc.composite_score,
               sc.composite_band,
               sc.critical_flags,
               ROW_NUMBER() OVER (PARTITION BY sc.student_id
                                  ORDER BY sc.completed_at DESC) AS rn,
               sc.composite_score
                 - LAG(sc.composite_score) OVER (PARTITION BY sc.student_id
                                                 ORDER BY sc.completed_at)
                                                                 AS change_since_last
          FROM v_screening_summary sc
         WHERE sc.status = 'COMPLETED')
WHERE  rn = 1;

DROP TRIGGER IF EXISTS trg_score_screening;
DROP TRIGGER IF EXISTS trg_critical_item_escalation;
DROP TRIGGER IF EXISTS trg_screening_completed_at;
DROP TRIGGER IF EXISTS trg_response_value_in_scale;

CREATE TRIGGER trg_score_screening
AFTER UPDATE OF status ON screening
FOR EACH ROW
WHEN NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED'
BEGIN
    INSERT OR REPLACE INTO screening_score
        (screening_id, instrument_id, raw_score, items_answered, normalised_pct)
    SELECT  NEW.screening_id,
            i.instrument_id,
            SUM(CASE WHEN ii.reverse_scored = 1
                     THEN i.option_max - r.option_value
                     ELSE r.option_value END),
            COUNT(*),
            ROUND(SUM(CASE WHEN ii.reverse_scored = 1
                           THEN i.option_max - r.option_value
                           ELSE r.option_value END) * 100.0 / i.score_max, 2)
    FROM        screening_response r
    INNER JOIN  instrument_item    ii ON r.item_id        = ii.item_id
    INNER JOIN  instrument         i  ON ii.instrument_id = i.instrument_id
    WHERE       r.screening_id = NEW.screening_id
    GROUP BY    i.instrument_id, i.option_max, i.score_max;

    UPDATE screening_score
       SET band_id = (SELECT b.band_id
                        FROM severity_band b
                       WHERE b.instrument_id = screening_score.instrument_id
                         AND screening_score.raw_score
                             BETWEEN b.min_score AND b.max_score
                       LIMIT 1)
     WHERE screening_id = NEW.screening_id;

    UPDATE screening
       SET completed_at = COALESCE(completed_at, datetime('now','localtime')),
           composite_score = (
               SELECT ROUND(
                        ( COALESCE(SUM(ss.normalised_pct * i.weight), 0)
                          + COALESCE((SELECT a.predicted_level * 50.0 * 0.20
                                        FROM assessment a
                                       WHERE a.assessment_id = NEW.assessment_id), 0) )
                        / NULLIF( COALESCE(SUM(i.weight), 0)
                                  + CASE WHEN NEW.assessment_id IS NULL
                                         THEN 0 ELSE 0.20 END, 0)
                      , 2)
                 FROM screening_score ss
                 JOIN instrument i ON ss.instrument_id = i.instrument_id
                WHERE ss.screening_id = NEW.screening_id)
     WHERE screening_id = NEW.screening_id;

    UPDATE screening
       SET composite_band = CASE
               WHEN composite_score IS NULL   THEN NULL
               WHEN composite_score >= 60     THEN 'High'
               WHEN composite_score >= 33     THEN 'Medium'
               ELSE 'Low' END
     WHERE screening_id = NEW.screening_id;
END;

CREATE TRIGGER trg_critical_item_escalation
AFTER UPDATE OF status ON screening
FOR EACH ROW
WHEN NEW.status = 'COMPLETED'
 AND NEW.assessment_id IS NOT NULL
 AND (SELECT COUNT(*)
        FROM screening_response r
        JOIN instrument_item ii ON r.item_id = ii.item_id
       WHERE r.screening_id = NEW.screening_id
         AND ii.is_critical = 1
         AND r.option_value > 0) > 0
BEGIN
    INSERT OR IGNORE INTO alert
        (assessment_id, alert_type, priority, status, raised_at, assigned_to)
    VALUES (NEW.assessment_id, 'CRITICAL_ITEM', 'CRITICAL', 'OPEN',
            datetime('now','localtime'),
            (SELECT c.counsellor_id FROM counsellor c
              WHERE c.is_active = 1
              ORDER BY (SELECT COUNT(*) FROM alert al
                         WHERE al.assigned_to = c.counsellor_id
                           AND al.status = 'OPEN') ASC, c.counsellor_id ASC
              LIMIT 1));

    UPDATE alert
       SET alert_type = 'CRITICAL_ITEM',
           priority   = 'CRITICAL',
           remarks    = 'Escalated by screening: non-zero response on a '
                        || 'critical self-harm item. Requires same-day contact.'
     WHERE assessment_id = NEW.assessment_id;
END;

CREATE TRIGGER trg_response_value_in_scale
BEFORE INSERT ON screening_response
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1
      FROM instrument_item ii
      JOIN response_option o ON o.instrument_id = ii.instrument_id
     WHERE ii.item_id      = NEW.item_id
       AND o.option_value  = NEW.option_value)
BEGIN
    SELECT RAISE(ABORT, 'Response value is not a valid option for this instrument.');
END;
