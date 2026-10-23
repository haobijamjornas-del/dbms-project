PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS v_puzzle_difficulty;
DROP VIEW IF EXISTS v_aptitude_category_score;
DROP VIEW IF EXISTS v_aptitude_summary;
DROP TABLE IF EXISTS aptitude_item;
DROP TABLE IF EXISTS aptitude_attempt;
DROP TABLE IF EXISTS aptitude_band;
DROP TABLE IF EXISTS puzzle_element;
DROP TABLE IF EXISTS puzzle_option;
DROP TABLE IF EXISTS puzzle;
DROP TABLE IF EXISTS puzzle_category;
DROP TABLE IF EXISTS age_group;

CREATE TABLE age_group (
    age_group_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    code         VARCHAR(20)  NOT NULL UNIQUE,
    label        VARCHAR(40)  NOT NULL,
    min_age      INTEGER      NOT NULL,
    max_age      INTEGER      NOT NULL,
    difficulty   INTEGER      NOT NULL UNIQUE,
    description  VARCHAR(200),
    CONSTRAINT chk_age_span   CHECK (min_age >= 0 AND max_age >= min_age),
    CONSTRAINT chk_difficulty CHECK (difficulty BETWEEN 1 AND 5)
);

CREATE TABLE puzzle_category (
    category_id   INTEGER      PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(20)  NOT NULL UNIQUE,
    name          VARCHAR(60)  NOT NULL,
    skill         VARCHAR(60)  NOT NULL,
    instructions  VARCHAR(200) NOT NULL,
    display_order INTEGER      NOT NULL UNIQUE
);

CREATE TABLE puzzle (
    puzzle_id      INTEGER      PRIMARY KEY AUTOINCREMENT,
    category_id    INTEGER      NOT NULL,
    age_group_id   INTEGER      NOT NULL,
    prompt         VARCHAR(400) NOT NULL,
    explanation    VARCHAR(400),
    time_limit_sec INTEGER      NOT NULL DEFAULT 45,
    is_active      INTEGER      NOT NULL DEFAULT 1,
    CONSTRAINT fk_puzzle_category FOREIGN KEY (category_id)
        REFERENCES puzzle_category (category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_puzzle_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_time_limit    CHECK (time_limit_sec BETWEEN 5 AND 300),
    CONSTRAINT chk_puzzle_active CHECK (is_active IN (0,1))
);

CREATE TABLE puzzle_option (
    option_id     INTEGER     PRIMARY KEY AUTOINCREMENT,
    puzzle_id     INTEGER     NOT NULL,
    label         VARCHAR(80) NOT NULL,
    color_key     VARCHAR(10),
    is_correct    INTEGER     NOT NULL DEFAULT 0,
    display_order INTEGER     NOT NULL,
    CONSTRAINT fk_option_puzzle FOREIGN KEY (puzzle_id)
        REFERENCES puzzle (puzzle_id) ON DELETE CASCADE,
    CONSTRAINT uq_option_order UNIQUE (puzzle_id, display_order),
    CONSTRAINT uq_option_label UNIQUE (puzzle_id, label),
    CONSTRAINT chk_option_correct CHECK (is_correct IN (0,1)),
    CONSTRAINT chk_option_color CHECK (color_key IS NULL OR color_key IN
        ('red','blue','green','orange','purple','pink'))
);

CREATE TABLE puzzle_element (
    puzzle_id  INTEGER     NOT NULL,
    role       VARCHAR(10) NOT NULL,
    position   INTEGER     NOT NULL,
    color_key  VARCHAR(10),
    text_value VARCHAR(40),
    PRIMARY KEY (puzzle_id, role, position),
    CONSTRAINT fk_element_puzzle FOREIGN KEY (puzzle_id)
        REFERENCES puzzle (puzzle_id) ON DELETE CASCADE,
    CONSTRAINT chk_element_role CHECK (role IN ('WORD','SEQUENCE','KEY')),
    CONSTRAINT chk_element_color CHECK (color_key IS NULL OR color_key IN
        ('red','blue','green','orange','purple','pink')),
    CONSTRAINT chk_element_content CHECK (color_key IS NOT NULL OR text_value IS NOT NULL)
);

CREATE TABLE aptitude_band (
    band_id   INTEGER      PRIMARY KEY AUTOINCREMENT,
    label     VARCHAR(30)  NOT NULL UNIQUE,
    min_pct   REAL         NOT NULL,
    max_pct   REAL         NOT NULL,
    color_hex CHAR(7)      NOT NULL,
    message   VARCHAR(300) NOT NULL,
    CONSTRAINT chk_band_pct CHECK (min_pct >= 0 AND max_pct <= 100 AND max_pct >= min_pct)
);

CREATE TABLE aptitude_attempt (
    attempt_id      INTEGER     PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER     NOT NULL,
    age_group_id    INTEGER     NOT NULL,
    age_at_attempt  INTEGER,
    status          VARCHAR(12) NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      TIMESTAMP   NOT NULL DEFAULT (datetime('now','localtime')),
    completed_at    TIMESTAMP,
    total_items     INTEGER,
    correct_items   INTEGER,
    accuracy_pct    REAL,
    avg_response_ms INTEGER,
    band_id         INTEGER,
    CONSTRAINT fk_attempt_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_attempt_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE,
    CONSTRAINT fk_attempt_band FOREIGN KEY (band_id)
        REFERENCES aptitude_band (band_id) ON UPDATE CASCADE,
    CONSTRAINT chk_attempt_status   CHECK (status IN ('IN_PROGRESS','COMPLETED','ABANDONED')),
    CONSTRAINT chk_attempt_accuracy CHECK (accuracy_pct IS NULL OR accuracy_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_attempt_age      CHECK (age_at_attempt IS NULL OR age_at_attempt BETWEEN 0 AND 120)
);

CREATE TABLE aptitude_item (
    attempt_id         INTEGER   NOT NULL,
    position           INTEGER   NOT NULL,
    puzzle_id          INTEGER   NOT NULL,
    shown_at           TIMESTAMP,
    selected_option_id INTEGER,
    is_correct         INTEGER,
    response_ms        INTEGER,
    answered_at        TIMESTAMP,
    PRIMARY KEY (attempt_id, position),
    CONSTRAINT uq_item_puzzle UNIQUE (attempt_id, puzzle_id),
    CONSTRAINT fk_item_attempt FOREIGN KEY (attempt_id)
        REFERENCES aptitude_attempt (attempt_id) ON DELETE CASCADE,
    CONSTRAINT fk_item_puzzle FOREIGN KEY (puzzle_id)
        REFERENCES puzzle (puzzle_id) ON DELETE RESTRICT,
    CONSTRAINT fk_item_option FOREIGN KEY (selected_option_id)
        REFERENCES puzzle_option (option_id) ON DELETE SET NULL,
    CONSTRAINT chk_item_correct  CHECK (is_correct IS NULL OR is_correct IN (0,1)),
    CONSTRAINT chk_item_ms       CHECK (response_ms IS NULL OR response_ms >= 0),
    CONSTRAINT chk_item_position CHECK (position > 0)
);

CREATE INDEX idx_puzzle_pick     ON puzzle (category_id, age_group_id, is_active);
CREATE INDEX idx_option_puzzle   ON puzzle_option (puzzle_id);
CREATE INDEX idx_attempt_student ON aptitude_attempt (student_id, started_at DESC);
CREATE INDEX idx_item_puzzle     ON aptitude_item (puzzle_id);

CREATE VIEW v_aptitude_summary AS
SELECT  att.attempt_id,
        att.student_id,
        s.full_name       AS student_name,
        s.enrollment_no,
        d.dept_code,
        s.year_of_study,
        g.age_group_id,
        g.code            AS age_group_code,
        g.label           AS age_group,
        att.age_at_attempt,
        att.status,
        att.started_at,
        att.completed_at,
        att.total_items,
        att.correct_items,
        att.accuracy_pct,
        att.avg_response_ms,
        b.label           AS band,
        b.color_hex       AS band_color,
        b.message         AS band_message,
        ROUND((JULIANDAY(att.completed_at) - JULIANDAY(att.started_at)) * 1440, 1) AS minutes_taken,
        (SELECT COUNT(*) FROM aptitude_item i WHERE i.attempt_id = att.attempt_id) AS item_count,
        (SELECT COUNT(*) FROM aptitude_item i
          WHERE i.attempt_id = att.attempt_id AND i.answered_at IS NOT NULL)       AS answered_count
FROM        aptitude_attempt att
INNER JOIN  student       s ON att.student_id   = s.student_id
INNER JOIN  department    d ON s.dept_id        = d.dept_id
INNER JOIN  age_group     g ON att.age_group_id = g.age_group_id
LEFT  JOIN  aptitude_band b ON att.band_id      = b.band_id;

CREATE VIEW v_aptitude_category_score AS
SELECT  i.attempt_id,
        c.category_id,
        c.code          AS category_code,
        c.name          AS category,
        c.skill,
        c.display_order,
        COUNT(*)                                                AS puzzles,
        SUM(CASE WHEN i.is_correct = 1 THEN 1 ELSE 0 END)       AS correct,
        ROUND(100.0 * SUM(CASE WHEN i.is_correct = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS accuracy_pct,
        CAST(AVG(i.response_ms) AS INTEGER)                     AS avg_response_ms
FROM        aptitude_item   i
INNER JOIN  puzzle          p ON i.puzzle_id   = p.puzzle_id
INNER JOIN  puzzle_category c ON p.category_id = c.category_id
GROUP BY    i.attempt_id, c.category_id, c.code, c.name, c.skill, c.display_order;

CREATE VIEW v_puzzle_difficulty AS
SELECT  p.puzzle_id,
        c.name          AS category,
        g.label         AS age_group,
        p.prompt,
        p.time_limit_sec,
        p.is_active,
        COUNT(i.answered_at)                                    AS times_answered,
        SUM(CASE WHEN i.is_correct = 1 THEN 1 ELSE 0 END)       AS times_correct,
        ROUND(100.0 * SUM(CASE WHEN i.is_correct = 1 THEN 1 ELSE 0 END)
              / NULLIF(COUNT(i.answered_at), 0), 1)             AS pct_correct,
        CAST(AVG(i.response_ms) AS INTEGER)                     AS avg_response_ms
FROM        puzzle          p
INNER JOIN  puzzle_category c ON p.category_id  = c.category_id
INNER JOIN  age_group       g ON p.age_group_id = g.age_group_id
LEFT  JOIN  aptitude_item   i ON i.puzzle_id    = p.puzzle_id
GROUP BY    p.puzzle_id, c.name, g.label, p.prompt, p.time_limit_sec, p.is_active;

DROP TRIGGER IF EXISTS trg_puzzle_answer_belongs;
DROP TRIGGER IF EXISTS trg_puzzle_mark_answer;
DROP TRIGGER IF EXISTS trg_puzzle_mark_skip;
DROP TRIGGER IF EXISTS trg_score_aptitude_attempt;

CREATE TRIGGER trg_puzzle_answer_belongs
BEFORE UPDATE OF selected_option_id ON aptitude_item
FOR EACH ROW
WHEN NEW.selected_option_id IS NOT NULL
 AND NOT EXISTS (SELECT 1 FROM puzzle_option o
                  WHERE o.option_id = NEW.selected_option_id
                    AND o.puzzle_id = NEW.puzzle_id)
BEGIN
    SELECT RAISE(ABORT, 'That answer does not belong to this puzzle.');
END;

CREATE TRIGGER trg_puzzle_mark_answer
AFTER UPDATE OF selected_option_id ON aptitude_item
FOR EACH ROW
WHEN NEW.selected_option_id IS NOT NULL
BEGIN
    UPDATE aptitude_item
       SET answered_at = COALESCE(NEW.answered_at, strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
           response_ms = COALESCE(NEW.response_ms,
               CASE WHEN NEW.shown_at IS NULL THEN NULL
                    ELSE MAX(0, CAST(ROUND((JULIANDAY('now', 'localtime') - JULIANDAY(NEW.shown_at))
                                           * 86400000) AS INTEGER)) END)
     WHERE attempt_id = NEW.attempt_id AND position = NEW.position;

    UPDATE aptitude_item
       SET is_correct = CASE
               WHEN response_ms IS NOT NULL
                AND response_ms > ((SELECT time_limit_sec FROM puzzle WHERE puzzle_id = NEW.puzzle_id) + 5) * 1000
               THEN 0
               ELSE (SELECT o.is_correct FROM puzzle_option o WHERE o.option_id = NEW.selected_option_id)
           END
     WHERE attempt_id = NEW.attempt_id AND position = NEW.position;
END;

CREATE TRIGGER trg_puzzle_mark_skip
AFTER UPDATE OF answered_at ON aptitude_item
FOR EACH ROW
WHEN NEW.answered_at IS NOT NULL AND NEW.selected_option_id IS NULL AND NEW.is_correct IS NULL
BEGIN
    UPDATE aptitude_item
       SET is_correct  = 0,
           response_ms = COALESCE(NEW.response_ms,
               CASE WHEN NEW.shown_at IS NULL THEN NULL
                    ELSE MAX(0, CAST(ROUND((JULIANDAY(NEW.answered_at) - JULIANDAY(NEW.shown_at))
                                           * 86400000) AS INTEGER)) END)
     WHERE attempt_id = NEW.attempt_id AND position = NEW.position;
END;

CREATE TRIGGER trg_score_aptitude_attempt
AFTER UPDATE OF status ON aptitude_attempt
FOR EACH ROW
WHEN NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED'
BEGIN
    UPDATE aptitude_attempt
       SET completed_at    = COALESCE(NEW.completed_at, datetime('now', 'localtime')),
           total_items     = (SELECT COUNT(*) FROM aptitude_item WHERE attempt_id = NEW.attempt_id),
           correct_items   = (SELECT COUNT(*) FROM aptitude_item
                               WHERE attempt_id = NEW.attempt_id AND is_correct = 1),
           accuracy_pct    = (SELECT ROUND(100.0 * SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END)
                                           / NULLIF(COUNT(*), 0), 1)
                                FROM aptitude_item WHERE attempt_id = NEW.attempt_id),
           avg_response_ms = (SELECT CAST(AVG(response_ms) AS INTEGER) FROM aptitude_item
                               WHERE attempt_id = NEW.attempt_id AND response_ms IS NOT NULL)
     WHERE attempt_id = NEW.attempt_id;

    UPDATE aptitude_attempt
       SET band_id = (SELECT b.band_id FROM aptitude_band b
                       WHERE aptitude_attempt.accuracy_pct >= b.min_pct
                         AND aptitude_attempt.accuracy_pct <= b.max_pct
                       ORDER BY b.min_pct DESC LIMIT 1)
     WHERE attempt_id = NEW.attempt_id;
END;
