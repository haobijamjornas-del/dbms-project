USE mindcare;

ALTER TABLE alert MODIFY COLUMN alert_type
    ENUM('HIGH_STRESS','REPEATED_HIGH','CRISIS_KEYWORD','SUSTAINED_DECLINE',
         'CRITICAL_ITEM') NOT NULL;

CREATE TABLE instrument (
    instrument_id INT AUTO_INCREMENT PRIMARY KEY,
    code          VARCHAR(15)  NOT NULL UNIQUE,
    name          VARCHAR(60)  NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    measures      VARCHAR(40)  NOT NULL,
    recall_period VARCHAR(40)  NOT NULL,
    item_count    INT          NOT NULL,
    option_min    INT          NOT NULL DEFAULT 0,
    option_max    INT          NOT NULL,
    score_min     INT          NOT NULL DEFAULT 0,
    score_max     INT          NOT NULL,
    weight        DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    display_order INT          NOT NULL,
    source_note   VARCHAR(200),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_instr_range  CHECK (option_max > option_min),
    CONSTRAINT chk_instr_weight CHECK (weight BETWEEN 0 AND 1)
) ENGINE=InnoDB;

CREATE TABLE instrument_item (
    item_id        INT AUTO_INCREMENT PRIMARY KEY,
    instrument_id  INT          NOT NULL,
    item_no        INT          NOT NULL,
    question_text  VARCHAR(300) NOT NULL,
    reverse_scored BOOLEAN      NOT NULL DEFAULT FALSE,
    is_critical    BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_item_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT uq_item_no UNIQUE (instrument_id, item_no),
    INDEX idx_item_instrument (instrument_id, item_no)
) ENGINE=InnoDB;

CREATE TABLE response_option (
    option_id     INT AUTO_INCREMENT PRIMARY KEY,
    instrument_id INT         NOT NULL,
    option_value  INT         NOT NULL,
    option_label  VARCHAR(40) NOT NULL,
    CONSTRAINT fk_opt_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT uq_opt_value UNIQUE (instrument_id, option_value)
) ENGINE=InnoDB;

CREATE TABLE severity_band (
    band_id       INT AUTO_INCREMENT PRIMARY KEY,
    instrument_id INT         NOT NULL,
    band_name     VARCHAR(30) NOT NULL,
    min_score     INT         NOT NULL,
    max_score     INT         NOT NULL,
    severity_rank INT         NOT NULL,
    color_hex     CHAR(7)     NOT NULL,
    guidance      VARCHAR(300),
    CONSTRAINT fk_band_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT uq_band_name  UNIQUE (instrument_id, band_name),
    CONSTRAINT chk_band_span CHECK (max_score >= min_score),
    INDEX idx_band_instrument (instrument_id, min_score, max_score)
) ENGINE=InnoDB;

CREATE TABLE screening (
    screening_id    INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT       NOT NULL,
    status          ENUM('IN_PROGRESS','COMPLETED','ABANDONED')
                    NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP NULL,
    assessment_id   INT UNIQUE,
    composite_score DECIMAL(5,2),
    composite_band  VARCHAR(20),
    is_baseline     BOOLEAN   NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_scr_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_scr_asmt FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE SET NULL,
    CONSTRAINT chk_scr_comp CHECK (composite_score IS NULL
                                   OR composite_score BETWEEN 0 AND 100),
    INDEX idx_scr_student (student_id, started_at DESC),
    INDEX idx_scr_status (status),
    INDEX idx_scr_band (composite_band)
) ENGINE=InnoDB;

CREATE TABLE screening_response (
    screening_id INT       NOT NULL,
    item_id      INT       NOT NULL,
    option_value INT       NOT NULL,
    answered_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (screening_id, item_id),
    CONSTRAINT fk_resp_scr FOREIGN KEY (screening_id)
        REFERENCES screening (screening_id) ON DELETE CASCADE,
    CONSTRAINT fk_resp_item FOREIGN KEY (item_id)
        REFERENCES instrument_item (item_id) ON DELETE CASCADE,
    CONSTRAINT chk_resp_val CHECK (option_value >= 0),
    INDEX idx_resp_item (item_id)
) ENGINE=InnoDB;

CREATE TABLE screening_score (
    screening_id   INT NOT NULL,
    instrument_id  INT NOT NULL,
    raw_score      INT NOT NULL,
    band_id        INT,
    items_answered INT NOT NULL,
    normalised_pct DECIMAL(5,2),
    PRIMARY KEY (screening_id, instrument_id),
    CONSTRAINT fk_sscore_scr FOREIGN KEY (screening_id)
        REFERENCES screening (screening_id) ON DELETE CASCADE,
    CONSTRAINT fk_sscore_instr FOREIGN KEY (instrument_id)
        REFERENCES instrument (instrument_id) ON DELETE CASCADE,
    CONSTRAINT fk_sscore_band FOREIGN KEY (band_id)
        REFERENCES severity_band (band_id) ON UPDATE CASCADE,
    INDEX idx_sscore_instr (instrument_id, raw_score)
) ENGINE=InnoDB;

CREATE VIEW v_screening_summary AS
SELECT sc.screening_id, sc.student_id, s.enrollment_no,
       s.full_name AS student_name, d.dept_code, s.year_of_study,
       sc.status, sc.started_at, sc.completed_at, sc.is_baseline,
       ROUND(sc.composite_score, 2) AS composite_score, sc.composite_band,
       ROUND(TIMESTAMPDIFF(SECOND, sc.started_at, sc.completed_at) / 60.0, 1)
                                    AS minutes_taken,
       sc.assessment_id, a.entry_text, sl.level_name AS text_level,
       ROUND(a.confidence * 100, 1) AS text_confidence_pct,
       t.theme_name AS text_theme,
       (SELECT COUNT(*) FROM screening_response r
         WHERE r.screening_id = sc.screening_id)          AS items_answered,
       (SELECT COUNT(*) FROM screening_response r
          JOIN instrument_item ii ON r.item_id = ii.item_id
         WHERE r.screening_id = sc.screening_id
           AND ii.is_critical = TRUE AND r.option_value > 0) AS critical_flags
FROM       screening    sc
JOIN       student      s  ON sc.student_id    = s.student_id
JOIN       department   d  ON s.dept_id        = d.dept_id
LEFT JOIN  assessment   a  ON sc.assessment_id = a.assessment_id
LEFT JOIN  stress_level sl ON a.predicted_level = sl.level_code
LEFT JOIN  theme        t  ON a.predicted_theme = t.theme_id;

CREATE VIEW v_screening_subscale AS
SELECT ss.screening_id, sc.student_id, sc.completed_at, i.instrument_id,
       i.code AS instrument_code, i.name AS instrument_name, i.measures,
       i.display_order, ss.raw_score, i.score_max, ss.items_answered,
       i.item_count, ROUND(ss.normalised_pct, 1) AS normalised_pct,
       b.band_name, b.severity_rank, b.color_hex, b.guidance
FROM       screening_score ss
JOIN       screening       sc ON ss.screening_id  = sc.screening_id
JOIN       instrument      i  ON ss.instrument_id = i.instrument_id
LEFT JOIN  severity_band   b  ON ss.band_id       = b.band_id;

CREATE VIEW v_item_response_stats AS
SELECT ii.item_id, i.code AS instrument_code, ii.item_no, ii.question_text,
       ii.reverse_scored, ii.is_critical, i.option_max,
       COUNT(r.screening_id)                                AS times_answered,
       ROUND(AVG(r.option_value), 3)                        AS avg_raw,
       ROUND(AVG(r.option_value) * 100.0 / i.option_max, 1) AS avg_pct_of_max,
       SUM(CASE WHEN r.option_value >= i.option_max - 1 THEN 1 ELSE 0 END)
                                                            AS high_answers
FROM       instrument_item    ii
JOIN       instrument         i ON ii.instrument_id = i.instrument_id
LEFT JOIN  screening_response r ON ii.item_id       = r.item_id
GROUP BY   ii.item_id, i.code, ii.item_no, ii.question_text,
           ii.reverse_scored, ii.is_critical, i.option_max;

CREATE VIEW v_student_screening_latest AS
SELECT * FROM (
    SELECT sc.student_id, sc.screening_id, sc.completed_at, sc.composite_score,
           sc.composite_band, sc.critical_flags,
           ROW_NUMBER() OVER (PARTITION BY sc.student_id
                              ORDER BY sc.completed_at DESC) AS rn,
           sc.composite_score
             - LAG(sc.composite_score) OVER (PARTITION BY sc.student_id
                                             ORDER BY sc.completed_at)
                                                             AS change_since_last
      FROM v_screening_summary sc
     WHERE sc.status = 'COMPLETED') ranked
WHERE rn = 1;

DELIMITER $$

CREATE TRIGGER trg_score_screening
BEFORE UPDATE ON screening
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED' THEN

        REPLACE INTO screening_score
            (screening_id, instrument_id, raw_score, items_answered, normalised_pct)
        SELECT NEW.screening_id, i.instrument_id,
               SUM(CASE WHEN ii.reverse_scored = TRUE
                        THEN i.option_max - r.option_value
                        ELSE r.option_value END),
               COUNT(*),
               ROUND(SUM(CASE WHEN ii.reverse_scored = TRUE
                              THEN i.option_max - r.option_value
                              ELSE r.option_value END) * 100.0 / i.score_max, 2)
          FROM screening_response r
          JOIN instrument_item    ii ON r.item_id        = ii.item_id
          JOIN instrument         i  ON ii.instrument_id = i.instrument_id
         WHERE r.screening_id = NEW.screening_id
         GROUP BY i.instrument_id, i.option_max, i.score_max;

        UPDATE screening_score ss
           SET ss.band_id = (SELECT b.band_id FROM severity_band b
                              WHERE b.instrument_id = ss.instrument_id
                                AND ss.raw_score BETWEEN b.min_score AND b.max_score
                              LIMIT 1)
         WHERE ss.screening_id = NEW.screening_id;

        SET NEW.completed_at = COALESCE(NEW.completed_at, CURRENT_TIMESTAMP);

        SET NEW.composite_score = (
                SELECT ROUND(
                         ( COALESCE(SUM(ss.normalised_pct * i.weight), 0)
                           + COALESCE((SELECT a.predicted_level * 50.0 * 0.20
                                         FROM assessment a
                                        WHERE a.assessment_id = NEW.assessment_id), 0) )
                         / NULLIF(COALESCE(SUM(i.weight), 0)
                                  + IF(NEW.assessment_id IS NULL, 0, 0.20), 0)
                       , 2)
                  FROM screening_score ss
                  JOIN instrument i ON ss.instrument_id = i.instrument_id
                 WHERE ss.screening_id = NEW.screening_id);

        SET NEW.composite_band = CASE
                WHEN NEW.composite_score IS NULL THEN NULL
                WHEN NEW.composite_score >= 60   THEN 'High'
                WHEN NEW.composite_score >= 33   THEN 'Medium'
                ELSE 'Low' END;
    END IF;
END$$

CREATE TRIGGER trg_critical_item_escalation
AFTER UPDATE ON screening
FOR EACH ROW
BEGIN
    DECLARE v_flags INT DEFAULT 0;
    DECLARE v_counsellor INT;

    IF NEW.status = 'COMPLETED' AND NEW.assessment_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_flags
          FROM screening_response r
          JOIN instrument_item ii ON r.item_id = ii.item_id
         WHERE r.screening_id = NEW.screening_id
           AND ii.is_critical = TRUE AND r.option_value > 0;

        IF v_flags > 0 THEN
            SELECT c.counsellor_id INTO v_counsellor
              FROM counsellor c WHERE c.is_active = TRUE
             ORDER BY (SELECT COUNT(*) FROM alert al
                        WHERE al.assigned_to = c.counsellor_id
                          AND al.status = 'OPEN') ASC, c.counsellor_id ASC
             LIMIT 1;

            INSERT IGNORE INTO alert
                (assessment_id, alert_type, priority, status, raised_at, assigned_to)
            VALUES (NEW.assessment_id, 'CRITICAL_ITEM', 'CRITICAL', 'OPEN',
                    CURRENT_TIMESTAMP, v_counsellor);

            UPDATE alert
               SET alert_type = 'CRITICAL_ITEM', priority = 'CRITICAL',
                   remarks = CONCAT('Escalated by screening: non-zero response on a ',
                                    'critical self-harm item. Requires same-day contact.')
             WHERE assessment_id = NEW.assessment_id;
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_response_value_in_scale
BEFORE INSERT ON screening_response
FOR EACH ROW
BEGIN
    DECLARE v_valid INT DEFAULT 0;
    SELECT COUNT(*) INTO v_valid
      FROM instrument_item ii
      JOIN response_option o ON o.instrument_id = ii.instrument_id
     WHERE ii.item_id = NEW.item_id AND o.option_value = NEW.option_value;
    IF v_valid = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Response value is not a valid option for this instrument.';
    END IF;
END$$

CREATE FUNCTION fn_subscale_score(p_screening_id INT, p_code VARCHAR(15))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_score INT DEFAULT 0;
    SELECT COALESCE(SUM(CASE WHEN ii.reverse_scored = TRUE
                             THEN i.option_max - r.option_value
                             ELSE r.option_value END), 0)
      INTO v_score
      FROM screening_response r
      JOIN instrument_item ii ON r.item_id = ii.item_id
      JOIN instrument i ON ii.instrument_id = i.instrument_id
     WHERE r.screening_id = p_screening_id AND i.code = p_code;
    RETURN v_score;
END$$

CREATE PROCEDURE sp_screening_report(
    IN  p_screening_id INT,
    OUT p_composite    DECIMAL(5,2))
BEGIN
    SELECT composite_score INTO p_composite
      FROM screening WHERE screening_id = p_screening_id;

    SELECT i.code, i.measures, ss.raw_score, i.score_max,
           ss.normalised_pct, b.band_name, b.guidance
      FROM screening_score ss
      JOIN instrument i ON ss.instrument_id = i.instrument_id
      LEFT JOIN severity_band b ON ss.band_id = b.band_id
     WHERE ss.screening_id = p_screening_id
     ORDER BY i.display_order;
END$$

CREATE PROCEDURE sp_review_screenings(IN p_min_composite DECIMAL(5,2))
BEGIN
    DECLARE v_done    BOOLEAN DEFAULT FALSE;
    DECLARE v_id      INT;
    DECLARE v_student INT;
    DECLARE v_score   DECIMAL(5,2);
    DECLARE v_flags   INT;
    DECLARE v_found   INT DEFAULT 0;

    DECLARE cur_scr CURSOR FOR
        SELECT screening_id, student_id, composite_score
          FROM screening WHERE status = 'COMPLETED';
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    DROP TEMPORARY TABLE IF EXISTS tmp_review;
    CREATE TEMPORARY TABLE tmp_review (
        screening_id INT, student_id INT,
        composite_score DECIMAL(5,2), critical_flags INT);

    OPEN cur_scr;
    scan: LOOP
        FETCH cur_scr INTO v_id, v_student, v_score;
        IF v_done THEN LEAVE scan; END IF;

        SELECT COUNT(*) INTO v_flags
          FROM screening_response r
          JOIN instrument_item ii ON r.item_id = ii.item_id
         WHERE r.screening_id = v_id
           AND ii.is_critical = TRUE AND r.option_value > 0;

        IF v_score >= p_min_composite OR v_flags > 0 THEN
            INSERT INTO tmp_review VALUES (v_id, v_student, v_score, v_flags);
            SET v_found = v_found + 1;
        END IF;
    END LOOP;
    CLOSE cur_scr;

    SELECT * FROM tmp_review ORDER BY critical_flags DESC, composite_score DESC;
    SELECT v_found AS screenings_flagged, p_min_composite AS threshold_used;
    DROP TEMPORARY TABLE IF EXISTS tmp_review;
END$$

DELIMITER ;
