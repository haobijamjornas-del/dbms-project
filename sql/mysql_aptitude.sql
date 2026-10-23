USE mindcare;

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
DROP PROCEDURE IF EXISTS sp_aptitude_report;

CREATE TABLE age_group (
    age_group_id INT AUTO_INCREMENT PRIMARY KEY,
    code         VARCHAR(20)  NOT NULL UNIQUE,
    label        VARCHAR(40)  NOT NULL,
    min_age      INT          NOT NULL,
    max_age      INT          NOT NULL,
    difficulty   INT          NOT NULL UNIQUE,
    description  VARCHAR(200),
    CONSTRAINT chk_age_span   CHECK (min_age >= 0 AND max_age >= min_age),
    CONSTRAINT chk_difficulty CHECK (difficulty BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE puzzle_category (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    code          VARCHAR(20)  NOT NULL UNIQUE,
    name          VARCHAR(60)  NOT NULL,
    skill         VARCHAR(60)  NOT NULL,
    instructions  VARCHAR(200) NOT NULL,
    display_order INT          NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE puzzle (
    puzzle_id      INT AUTO_INCREMENT PRIMARY KEY,
    category_id    INT          NOT NULL,
    age_group_id   INT          NOT NULL,
    prompt         VARCHAR(400) NOT NULL,
    explanation    VARCHAR(400),
    time_limit_sec INT          NOT NULL DEFAULT 45,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_puzzle_category FOREIGN KEY (category_id)
        REFERENCES puzzle_category (category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_puzzle_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_time_limit CHECK (time_limit_sec BETWEEN 5 AND 300),
    INDEX idx_puzzle_pick (category_id, age_group_id, is_active)
) ENGINE=InnoDB;

CREATE TABLE puzzle_option (
    option_id     INT AUTO_INCREMENT PRIMARY KEY,
    puzzle_id     INT         NOT NULL,
    label         VARCHAR(80) NOT NULL,
    color_key     ENUM('red','blue','green','orange','purple','pink'),
    is_correct    BOOLEAN     NOT NULL DEFAULT FALSE,
    display_order INT         NOT NULL,
    CONSTRAINT fk_option_puzzle FOREIGN KEY (puzzle_id)
        REFERENCES puzzle (puzzle_id) ON DELETE CASCADE,
    CONSTRAINT uq_option_order UNIQUE (puzzle_id, display_order),
    CONSTRAINT uq_option_label UNIQUE (puzzle_id, label)
) ENGINE=InnoDB;

CREATE TABLE puzzle_element (
    puzzle_id  INT         NOT NULL,
    role       ENUM('WORD','SEQUENCE','KEY') NOT NULL,
    position   INT         NOT NULL,
    color_key  ENUM('red','blue','green','orange','purple','pink'),
    text_value VARCHAR(40),
    PRIMARY KEY (puzzle_id, role, position),
    CONSTRAINT fk_element_puzzle FOREIGN KEY (puzzle_id)
        REFERENCES puzzle (puzzle_id) ON DELETE CASCADE,
    CONSTRAINT chk_element_content CHECK (color_key IS NOT NULL OR text_value IS NOT NULL)
) ENGINE=InnoDB;

CREATE TABLE aptitude_band (
    band_id   INT AUTO_INCREMENT PRIMARY KEY,
    label     VARCHAR(30)  NOT NULL UNIQUE,
    min_pct   DECIMAL(5,1) NOT NULL,
    max_pct   DECIMAL(5,1) NOT NULL,
    color_hex CHAR(7)      NOT NULL,
    message   VARCHAR(300) NOT NULL,
    CONSTRAINT chk_band_pct CHECK (min_pct >= 0 AND max_pct <= 100 AND max_pct >= min_pct)
) ENGINE=InnoDB;

CREATE TABLE aptitude_attempt (
    attempt_id      INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT          NOT NULL,
    age_group_id    INT          NOT NULL,
    age_at_attempt  INT,
    status          ENUM('IN_PROGRESS','COMPLETED','ABANDONED') NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    total_items     INT,
    correct_items   INT,
    accuracy_pct    DECIMAL(5,1),
    avg_response_ms INT,
    band_id         INT,
    CONSTRAINT fk_attempt_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_attempt_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE,
    CONSTRAINT fk_attempt_band FOREIGN KEY (band_id)
        REFERENCES aptitude_band (band_id) ON UPDATE CASCADE,
    CONSTRAINT chk_attempt_accuracy CHECK (accuracy_pct IS NULL OR accuracy_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_attempt_age      CHECK (age_at_attempt IS NULL OR age_at_attempt BETWEEN 0 AND 120),
    INDEX idx_attempt_student (student_id, started_at)
) ENGINE=InnoDB;

CREATE TABLE aptitude_item (
    attempt_id         INT         NOT NULL,
    position           INT         NOT NULL,
    puzzle_id          INT         NOT NULL,
    shown_at           DATETIME(3),
    selected_option_id INT,
    is_correct         BOOLEAN,
    response_ms        INT,
    answered_at        DATETIME(3),
    PRIMARY KEY (attempt_id, position),
    CONSTRAINT uq_item_puzzle UNIQUE (attempt_id, puzzle_id),
    CONSTRAINT fk_item_attempt FOREIGN KEY (attempt_id)
        REFERENCES aptitude_attempt (attempt_id) ON DELETE CASCADE,
    CONSTRAINT fk_item_puzzle FOREIGN KEY (puzzle_id)
        REFERENCES puzzle (puzzle_id) ON DELETE RESTRICT,
    CONSTRAINT fk_item_option FOREIGN KEY (selected_option_id)
        REFERENCES puzzle_option (option_id) ON DELETE SET NULL,
    CONSTRAINT chk_item_ms       CHECK (response_ms IS NULL OR response_ms >= 0),
    CONSTRAINT chk_item_position CHECK (position > 0),
    INDEX idx_item_puzzle (puzzle_id)
) ENGINE=InnoDB;

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
        ROUND(TIMESTAMPDIFF(SECOND, att.started_at, att.completed_at) / 60, 1) AS minutes_taken,
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
        CAST(AVG(i.response_ms) AS SIGNED)                      AS avg_response_ms
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
        CAST(AVG(i.response_ms) AS SIGNED)                      AS avg_response_ms
FROM        puzzle          p
INNER JOIN  puzzle_category c ON p.category_id  = c.category_id
INNER JOIN  age_group       g ON p.age_group_id = g.age_group_id
LEFT  JOIN  aptitude_item   i ON i.puzzle_id    = p.puzzle_id
GROUP BY    p.puzzle_id, c.name, g.label, p.prompt, p.time_limit_sec, p.is_active;

DELIMITER $$

CREATE TRIGGER trg_puzzle_answer_belongs
BEFORE UPDATE ON aptitude_item
FOR EACH ROW
BEGIN
    IF NEW.selected_option_id IS NOT NULL
       AND NOT (NEW.selected_option_id <=> OLD.selected_option_id)
       AND NOT EXISTS (SELECT 1 FROM puzzle_option o
                        WHERE o.option_id = NEW.selected_option_id
                          AND o.puzzle_id = NEW.puzzle_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'That answer does not belong to this puzzle.';
    END IF;
END$$

CREATE TRIGGER trg_puzzle_mark_answer
BEFORE UPDATE ON aptitude_item
FOR EACH ROW
FOLLOWS trg_puzzle_answer_belongs
BEGIN
    DECLARE v_limit INT;
    DECLARE v_right BOOLEAN;

    IF NEW.selected_option_id IS NOT NULL
       AND NOT (NEW.selected_option_id <=> OLD.selected_option_id) THEN
        SET NEW.answered_at = COALESCE(NEW.answered_at, NOW(3));
        IF NEW.response_ms IS NULL AND NEW.shown_at IS NOT NULL THEN
            SET NEW.response_ms = GREATEST(0,
                TIMESTAMPDIFF(MICROSECOND, NEW.shown_at, NEW.answered_at) DIV 1000);
        END IF;

        SELECT time_limit_sec INTO v_limit FROM puzzle WHERE puzzle_id = NEW.puzzle_id;
        SELECT is_correct INTO v_right FROM puzzle_option WHERE option_id = NEW.selected_option_id;

        IF NEW.response_ms IS NOT NULL AND NEW.response_ms > (v_limit + 5) * 1000 THEN
            SET NEW.is_correct = FALSE;
        ELSE
            SET NEW.is_correct = v_right;
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_puzzle_mark_skip
BEFORE UPDATE ON aptitude_item
FOR EACH ROW
FOLLOWS trg_puzzle_mark_answer
BEGIN
    IF NEW.answered_at IS NOT NULL AND OLD.answered_at IS NULL
       AND NEW.selected_option_id IS NULL AND NEW.is_correct IS NULL THEN
        SET NEW.is_correct = FALSE;
        IF NEW.response_ms IS NULL AND NEW.shown_at IS NOT NULL THEN
            SET NEW.response_ms = GREATEST(0,
                TIMESTAMPDIFF(MICROSECOND, NEW.shown_at, NEW.answered_at) DIV 1000);
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_score_aptitude_attempt
BEFORE UPDATE ON aptitude_attempt
FOR EACH ROW
BEGIN
    DECLARE v_total   INT;
    DECLARE v_correct INT;
    DECLARE v_pct     DECIMAL(5,1);
    DECLARE v_ms      INT;

    IF NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED' THEN
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END), 0),
               ROUND(100.0 * SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1),
               CAST(AVG(response_ms) AS SIGNED)
          INTO v_total, v_correct, v_pct, v_ms
          FROM aptitude_item
         WHERE attempt_id = NEW.attempt_id;

        SET NEW.completed_at    = COALESCE(NEW.completed_at, NOW());
        SET NEW.total_items     = v_total;
        SET NEW.correct_items   = v_correct;
        SET NEW.accuracy_pct    = v_pct;
        SET NEW.avg_response_ms = v_ms;
        SET NEW.band_id = (SELECT b.band_id FROM aptitude_band b
                            WHERE v_pct BETWEEN b.min_pct AND b.max_pct
                            ORDER BY b.min_pct DESC LIMIT 1);
    END IF;
END$$

CREATE PROCEDURE sp_aptitude_report(IN p_student_id INT)
BEGIN
    SELECT attempt_id, age_group, completed_at, correct_items, total_items,
           accuracy_pct, band
      FROM v_aptitude_summary
     WHERE student_id = p_student_id AND status = 'COMPLETED'
     ORDER BY completed_at DESC;

    SELECT s.category, SUM(s.correct) AS correct, SUM(s.puzzles) AS puzzles,
           ROUND(100.0 * SUM(s.correct) / SUM(s.puzzles), 1) AS accuracy_pct
      FROM v_aptitude_category_score s
      JOIN aptitude_attempt a ON s.attempt_id = a.attempt_id
     WHERE a.student_id = p_student_id AND a.status = 'COMPLETED'
     GROUP BY s.category_id, s.category
     ORDER BY accuracy_pct;
END$$

DELIMITER ;
