DROP DATABASE IF EXISTS mindcare;
CREATE DATABASE mindcare CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mindcare;

CREATE TABLE department (
    dept_id   INT AUTO_INCREMENT PRIMARY KEY,
    dept_code VARCHAR(10) NOT NULL UNIQUE,
    dept_name VARCHAR(80) NOT NULL,
    hod_name  VARCHAR(80),
    CONSTRAINT chk_dept_code_upper CHECK (dept_code = UPPER(dept_code) COLLATE utf8mb4_bin)
) ENGINE=InnoDB;

CREATE TABLE stress_level (
    level_code     TINYINT      PRIMARY KEY,
    level_name     VARCHAR(20)  NOT NULL UNIQUE,
    severity_rank  TINYINT      NOT NULL UNIQUE,
    color_hex      CHAR(7)      NOT NULL,
    description    VARCHAR(200),
    requires_alert BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_level_code CHECK (level_code BETWEEN 0 AND 2)
) ENGINE=InnoDB;

CREATE TABLE theme (
    theme_id    INT AUTO_INCREMENT PRIMARY KEY,
    theme_code  VARCHAR(30) NOT NULL UNIQUE,
    theme_name  VARCHAR(60) NOT NULL,
    category    ENUM('Academic','Personal','Health','Financial',
                     'Social','Occupational') NOT NULL,
    description VARCHAR(200)
) ENGINE=InnoDB;

CREATE TABLE counsellor (
    counsellor_id   INT AUTO_INCREMENT PRIMARY KEY,
    emp_code        VARCHAR(15)  NOT NULL UNIQUE,
    full_name       VARCHAR(80)  NOT NULL,
    email           VARCHAR(120) NOT NULL UNIQUE,
    phone           VARCHAR(15),
    specialization  VARCHAR(60),
    max_daily_slots TINYINT      NOT NULL DEFAULT 6,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_slots CHECK (max_daily_slots BETWEEN 1 AND 20)
) ENGINE=InnoDB;

CREATE TABLE student (
    student_id     INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_no  VARCHAR(20)  NOT NULL UNIQUE,
    full_name      VARCHAR(80)  NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    phone          VARCHAR(15),
    gender         ENUM('Male','Female','Other'),
    dob            DATE,
    dept_id        INT          NOT NULL,
    year_of_study  TINYINT      NOT NULL,
    hostel_status  ENUM('Hosteller','Day Scholar') NOT NULL DEFAULT 'Day Scholar',
    admission_year SMALLINT,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_student_dept FOREIGN KEY (dept_id) REFERENCES department (dept_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_year CHECK (year_of_study BETWEEN 1 AND 5),
    INDEX idx_student_dept (dept_id),
    INDEX idx_student_year (year_of_study)
) ENGINE=InnoDB;

CREATE TABLE app_user (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(40)  NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    role          ENUM('student','counsellor','admin') NOT NULL,
    student_id    INT UNIQUE,
    counsellor_id INT UNIQUE,
    last_login    TIMESTAMP NULL,
    is_active     BOOLEAN   NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_couns FOREIGN KEY (counsellor_id)
        REFERENCES counsellor (counsellor_id) ON DELETE CASCADE,
    CONSTRAINT chk_role_link CHECK (
        (role = 'student'    AND student_id IS NOT NULL AND counsellor_id IS NULL) OR
        (role = 'counsellor' AND counsellor_id IS NOT NULL AND student_id IS NULL) OR
        (role = 'admin'      AND student_id IS NULL AND counsellor_id IS NULL))
) ENGINE=InnoDB;

CREATE TABLE ml_model (
    model_id        INT AUTO_INCREMENT PRIMARY KEY,
    model_name      VARCHAR(60) NOT NULL,
    algorithm       VARCHAR(60) NOT NULL,
    version         VARCHAR(10) NOT NULL,
    accuracy        DECIMAL(6,5),
    precision_macro DECIMAL(6,5),
    recall_macro    DECIMAL(6,5),
    f1_macro        DECIMAL(6,5),
    train_size      INT,
    test_size       INT,
    feature_count   INT,
    artifact_path   VARCHAR(200),
    trained_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN   NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_model_ver UNIQUE (model_name, algorithm, version),
    CONSTRAINT chk_acc CHECK (accuracy IS NULL OR accuracy BETWEEN 0 AND 1)
) ENGINE=InnoDB;

CREATE TABLE training_corpus (
    corpus_id INT PRIMARY KEY,
    text      VARCHAR(500) NOT NULL,
    label     TINYINT      NOT NULL,
    theme_id  INT          NOT NULL,
    split     ENUM('train','test') NOT NULL DEFAULT 'train',
    CONSTRAINT fk_corpus_level FOREIGN KEY (label)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE,
    CONSTRAINT fk_corpus_theme FOREIGN KEY (theme_id)
        REFERENCES theme (theme_id) ON UPDATE CASCADE,
    INDEX idx_corpus_label (label)
) ENGINE=InnoDB;

CREATE TABLE keyword_lexicon (
    keyword_id INT AUTO_INCREMENT PRIMARY KEY,
    word       VARCHAR(40)  NOT NULL UNIQUE,
    category   VARCHAR(30)  NOT NULL,
    weight     DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    polarity   ENUM('positive','negative','neutral') NOT NULL DEFAULT 'negative',
    CONSTRAINT chk_weight CHECK (weight BETWEEN 0 AND 5)
) ENGINE=InnoDB;

CREATE TABLE assessment (
    assessment_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT           NOT NULL,
    model_id        INT           NOT NULL,
    entry_text      VARCHAR(1000) NOT NULL,
    char_count      INT           NOT NULL,
    word_count      INT           NOT NULL,
    predicted_level TINYINT       NOT NULL,
    confidence      DECIMAL(6,5)  NOT NULL,
    predicted_theme INT,
    source          ENUM('web','mobile','chat','import') NOT NULL DEFAULT 'web',
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asmt_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_asmt_model FOREIGN KEY (model_id)
        REFERENCES ml_model (model_id) ON DELETE RESTRICT,
    CONSTRAINT fk_asmt_level FOREIGN KEY (predicted_level)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE,
    CONSTRAINT fk_asmt_theme FOREIGN KEY (predicted_theme)
        REFERENCES theme (theme_id) ON UPDATE CASCADE,
    CONSTRAINT chk_conf CHECK (confidence BETWEEN 0 AND 1),
    INDEX idx_asmt_student_date (student_id, created_at DESC),
    INDEX idx_asmt_level (predicted_level),
    INDEX idx_asmt_theme (predicted_theme),
    INDEX idx_asmt_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE assessment_score (
    assessment_id INT          NOT NULL,
    level_code    TINYINT      NOT NULL,
    probability   DECIMAL(6,5) NOT NULL,
    PRIMARY KEY (assessment_id, level_code),
    CONSTRAINT fk_score_asmt FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE CASCADE,
    CONSTRAINT fk_score_level FOREIGN KEY (level_code)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE,
    CONSTRAINT chk_prob CHECK (probability BETWEEN 0 AND 1)
) ENGINE=InnoDB;

CREATE TABLE assessment_keyword (
    assessment_id INT NOT NULL,
    keyword_id    INT NOT NULL,
    occurrences   INT NOT NULL DEFAULT 1,
    PRIMARY KEY (assessment_id, keyword_id),
    CONSTRAINT fk_ak_asmt FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE CASCADE,
    CONSTRAINT fk_ak_kw FOREIGN KEY (keyword_id)
        REFERENCES keyword_lexicon (keyword_id) ON DELETE CASCADE,
    CONSTRAINT chk_occ CHECK (occurrences > 0)
) ENGINE=InnoDB;

CREATE TABLE alert (
    alert_id        INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id   INT NOT NULL UNIQUE,
    alert_type      ENUM('HIGH_STRESS','REPEATED_HIGH','CRISIS_KEYWORD',
                         'SUSTAINED_DECLINE') NOT NULL,
    priority        ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL,
    status          ENUM('OPEN','ACKNOWLEDGED','RESOLVED','DISMISSED')
                    NOT NULL DEFAULT 'OPEN',
    assigned_to     INT,
    raised_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP NULL,
    resolved_at     TIMESTAMP NULL,
    remarks         VARCHAR(300),
    CONSTRAINT fk_alert_asmt FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_couns FOREIGN KEY (assigned_to)
        REFERENCES counsellor (counsellor_id) ON DELETE SET NULL,
    INDEX idx_alert_status (status, priority),
    INDEX idx_alert_assigned (assigned_to)
) ENGINE=InnoDB;

CREATE TABLE counselling_session (
    session_id       INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT       NOT NULL,
    counsellor_id    INT       NOT NULL,
    alert_id         INT,
    scheduled_at     DATETIME  NOT NULL,
    duration_min     INT       NOT NULL DEFAULT 45,
    mode             ENUM('In-Person','Video','Phone','Chat')
                     NOT NULL DEFAULT 'In-Person',
    status           ENUM('SCHEDULED','COMPLETED','CANCELLED','NO_SHOW')
                     NOT NULL DEFAULT 'SCHEDULED',
    notes            VARCHAR(500),
    follow_up_needed BOOLEAN   NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sess_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_sess_couns FOREIGN KEY (counsellor_id)
        REFERENCES counsellor (counsellor_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sess_alert FOREIGN KEY (alert_id)
        REFERENCES alert (alert_id) ON DELETE SET NULL,
    CONSTRAINT chk_duration CHECK (duration_min BETWEEN 15 AND 180),
    INDEX idx_sess_couns_date (counsellor_id, scheduled_at),
    INDEX idx_sess_student (student_id)
) ENGINE=InnoDB;

CREATE TABLE wellness_log (
    log_id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT     NOT NULL,
    log_date        DATE    NOT NULL,
    sleep_hours     DECIMAL(4,1),
    exercise_min    INT,
    mood_rating     TINYINT,
    screen_time_hrs DECIMAL(4,1),
    CONSTRAINT fk_wl_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT uq_wl_student_date UNIQUE (student_id, log_date),
    CONSTRAINT chk_sleep CHECK (sleep_hours IS NULL OR sleep_hours BETWEEN 0 AND 24),
    CONSTRAINT chk_mood  CHECK (mood_rating IS NULL OR mood_rating BETWEEN 1 AND 10),
    INDEX idx_wl_student_date (student_id, log_date DESC)
) ENGINE=InnoDB;

CREATE TABLE helpline (
    helpline_id   INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(80)  NOT NULL,
    phone         VARCHAR(60)  NOT NULL,
    dial          VARCHAR(20)  NOT NULL,
    region        ENUM('Emergency','National','Delhi NCR','Noida') NOT NULL,
    hours         VARCHAR(60)  NOT NULL,
    service       VARCHAR(160) NOT NULL,
    is_crisis     BOOLEAN      NOT NULL DEFAULT FALSE,
    display_order INT          NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_helpline UNIQUE (name, dial),
    INDEX idx_helpline_region (region, display_order)
) ENGINE=InnoDB;

CREATE TABLE support_tip (
    tip_id        INT AUTO_INCREMENT PRIMARY KEY,
    level_code    TINYINT      NOT NULL,
    tip_type      ENUM('COPING','ADVICE') NOT NULL,
    title         VARCHAR(80)  NOT NULL,
    body          VARCHAR(400) NOT NULL,
    display_order INT          NOT NULL,
    CONSTRAINT fk_tip_level FOREIGN KEY (level_code)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_tip UNIQUE (level_code, tip_type, title),
    INDEX idx_tip_level (level_code, tip_type, display_order)
) ENGINE=InnoDB;

CREATE VIEW v_assessment_detail AS
SELECT a.assessment_id, a.created_at, s.student_id, s.enrollment_no,
       s.full_name AS student_name, d.dept_code, d.dept_name, s.year_of_study,
       a.entry_text, a.word_count, sl.level_code, sl.level_name AS stress_level,
       sl.color_hex, sl.severity_rank, ROUND(a.confidence * 100, 2) AS confidence_pct,
       t.theme_name, t.category AS theme_category, m.model_name, m.algorithm, a.source
FROM       assessment  a
JOIN       student      s  ON a.student_id      = s.student_id
JOIN       department   d  ON s.dept_id         = d.dept_id
JOIN       stress_level sl ON a.predicted_level = sl.level_code
JOIN       ml_model     m  ON a.model_id        = m.model_id
LEFT JOIN  theme        t  ON a.predicted_theme = t.theme_id;

CREATE VIEW v_student_risk_profile AS
SELECT s.student_id, s.enrollment_no, s.full_name, d.dept_code, s.year_of_study,
       COUNT(a.assessment_id)                                  AS total_assessments,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)  AS high_count,
       SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END)  AS moderate_count,
       SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END)  AS low_count,
       ROUND(AVG(a.predicted_level), 3)                        AS avg_stress_score,
       ROUND(AVG(a.confidence) * 100, 2)                       AS avg_confidence_pct,
       MAX(a.created_at)                                       AS last_assessed_at,
       (SELECT sl.level_name FROM assessment a2
          JOIN stress_level sl ON a2.predicted_level = sl.level_code
         WHERE a2.student_id = s.student_id
         ORDER BY a2.created_at DESC, a2.assessment_id DESC LIMIT 1) AS latest_level,
       ROUND(CASE WHEN COUNT(a.assessment_id) = 0 THEN 0 ELSE
             (SUM(CASE WHEN a.predicted_level = 2 THEN 3
                       WHEN a.predicted_level = 1 THEN 2 ELSE 0 END) * 100.0)
             / (COUNT(a.assessment_id) * 3.0) END, 2)           AS risk_index
FROM       student    s
JOIN       department d ON s.dept_id = d.dept_id
LEFT JOIN  assessment a ON s.student_id = a.student_id
GROUP BY   s.student_id, s.enrollment_no, s.full_name, d.dept_code, s.year_of_study;

CREATE VIEW v_high_risk_queue AS
SELECT al.alert_id, al.priority, al.status, al.alert_type, al.raised_at,
       s.student_id, s.enrollment_no, s.full_name AS student_name, s.phone,
       d.dept_code, a.assessment_id, a.entry_text,
       ROUND(a.confidence * 100, 1) AS confidence_pct, t.theme_name,
       c.full_name AS assigned_counsellor,
       CASE al.priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3 ELSE 4 END AS priority_rank
FROM       alert      al
JOIN       assessment a ON al.assessment_id  = a.assessment_id
JOIN       student    s ON a.student_id      = s.student_id
JOIN       department d ON s.dept_id         = d.dept_id
LEFT JOIN  theme      t ON a.predicted_theme = t.theme_id
LEFT JOIN  counsellor c ON al.assigned_to    = c.counsellor_id
WHERE      al.status IN ('OPEN','ACKNOWLEDGED');

CREATE VIEW v_theme_distribution AS
SELECT t.theme_id, t.theme_name, t.category, COUNT(a.assessment_id) AS total,
       SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END) AS low,
       SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END) AS moderate,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high,
       ROUND(SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) * 100.0
             / NULLIF(COUNT(a.assessment_id), 0), 2)          AS high_pct
FROM       theme      t
LEFT JOIN  assessment a ON t.theme_id = a.predicted_theme
GROUP BY   t.theme_id, t.theme_name, t.category;

CREATE VIEW v_counsellor_workload AS
SELECT c.counsellor_id, c.emp_code, c.full_name, c.specialization, c.max_daily_slots,
       COUNT(DISTINCT cs.session_id)                            AS total_sessions,
       SUM(CASE WHEN cs.status = 'SCHEDULED' THEN 1 ELSE 0 END) AS upcoming,
       SUM(CASE WHEN cs.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
       SUM(CASE WHEN cs.status = 'NO_SHOW'   THEN 1 ELSE 0 END) AS no_shows,
       (SELECT COUNT(*) FROM alert al WHERE al.assigned_to = c.counsellor_id
          AND al.status = 'OPEN')                               AS open_alerts,
       COUNT(DISTINCT cs.student_id)                            AS distinct_students
FROM       counsellor c
LEFT JOIN  counselling_session cs ON c.counsellor_id = cs.counsellor_id
WHERE      c.is_active = TRUE
GROUP BY   c.counsellor_id, c.emp_code, c.full_name, c.specialization, c.max_daily_slots;

CREATE VIEW v_dept_stress_summary AS
SELECT d.dept_id, d.dept_code, d.dept_name,
       COUNT(DISTINCT s.student_id)                            AS enrolled_students,
       COUNT(DISTINCT a.student_id)                            AS students_assessed,
       COUNT(a.assessment_id)                                  AS total_assessments,
       ROUND(AVG(a.predicted_level), 3)                        AS avg_stress_score,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)  AS high_stress_entries,
       ROUND(SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) * 100.0
             / NULLIF(COUNT(a.assessment_id), 0), 2)           AS high_stress_pct
FROM       department d
LEFT JOIN  student    s ON d.dept_id    = s.dept_id
LEFT JOIN  assessment a ON s.student_id = a.student_id
GROUP BY   d.dept_id, d.dept_code, d.dept_name;

CREATE VIEW v_daily_trend AS
SELECT DATE(a.created_at)                                     AS entry_date,
       COUNT(*)                                               AS total,
       SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END) AS low,
       SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END) AS moderate,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high,
       ROUND(AVG(a.predicted_level), 3)                       AS avg_stress_score
FROM   assessment a
GROUP  BY DATE(a.created_at);

CREATE VIEW v_wellness_vs_stress AS
SELECT w.student_id, s.full_name, w.log_date, w.sleep_hours, w.exercise_min,
       w.mood_rating, w.screen_time_hrs,
       COUNT(a.assessment_id)           AS entries_that_day,
       ROUND(AVG(a.predicted_level), 2) AS avg_stress_that_day
FROM       wellness_log w
JOIN       student      s ON w.student_id = s.student_id
LEFT JOIN  assessment   a ON a.student_id = w.student_id
                         AND DATE(a.created_at) = w.log_date
GROUP BY   w.student_id, s.full_name, w.log_date, w.sleep_hours,
           w.exercise_min, w.mood_rating, w.screen_time_hrs;

DELIMITER $$

CREATE TRIGGER trg_alert_on_high_stress
AFTER INSERT ON assessment
FOR EACH ROW
BEGIN
    DECLARE v_counsellor INT;
    IF NEW.predicted_level = 2 THEN
        SELECT c.counsellor_id INTO v_counsellor
          FROM counsellor c
         WHERE c.is_active = TRUE
         ORDER BY (SELECT COUNT(*) FROM alert al
                    WHERE al.assigned_to = c.counsellor_id AND al.status = 'OPEN') ASC,
                  c.counsellor_id ASC
         LIMIT 1;

        INSERT INTO alert (assessment_id, alert_type, priority, status,
                           raised_at, assigned_to)
        VALUES (NEW.assessment_id, 'HIGH_STRESS',
                IF(NEW.confidence >= 0.90, 'HIGH', 'MEDIUM'),
                'OPEN', NEW.created_at, v_counsellor);
    END IF;
END$$

CREATE TRIGGER trg_escalate_repeated_high
BEFORE INSERT ON alert
FOR EACH ROW
BEGIN
    DECLARE v_student INT;
    DECLARE v_at DATETIME;
    DECLARE v_count INT DEFAULT 0;

    SELECT student_id, created_at INTO v_student, v_at
      FROM assessment WHERE assessment_id = NEW.assessment_id;

    SELECT COUNT(*) INTO v_count
      FROM assessment
     WHERE student_id = v_student
       AND predicted_level = 2
       AND created_at BETWEEN DATE_SUB(v_at, INTERVAL 7 DAY) AND v_at;

    IF v_count >= 3 AND NEW.alert_type = 'HIGH_STRESS' THEN
        SET NEW.alert_type = 'REPEATED_HIGH',
            NEW.priority   = 'CRITICAL',
            NEW.remarks    = 'Auto-escalated: 3 or more high-stress entries in 7 days.';
    END IF;
END$$

CREATE TRIGGER trg_alert_timestamps
BEFORE UPDATE ON alert
FOR EACH ROW
BEGIN
    IF NEW.status = 'ACKNOWLEDGED' AND OLD.status = 'OPEN' THEN
        SET NEW.acknowledged_at = CURRENT_TIMESTAMP;
    END IF;
    IF NEW.status IN ('RESOLVED','DISMISSED') AND NEW.resolved_at IS NULL THEN
        SET NEW.resolved_at = CURRENT_TIMESTAMP;
    END IF;
END$$

CREATE TRIGGER trg_session_completed_resolves_alert
AFTER UPDATE ON counselling_session
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' AND NEW.alert_id IS NOT NULL THEN
        UPDATE alert
           SET status = 'RESOLVED',
               remarks = CONCAT('Closed by counselling session #', NEW.session_id)
         WHERE alert_id = NEW.alert_id AND status <> 'RESOLVED';
    END IF;
END$$

CREATE TRIGGER trg_prevent_double_booking
BEFORE INSERT ON counselling_session
FOR EACH ROW
BEGIN
    DECLARE v_clash INT;
    SELECT COUNT(*) INTO v_clash
      FROM counselling_session
     WHERE counsellor_id = NEW.counsellor_id
       AND scheduled_at  = NEW.scheduled_at
       AND status        = 'SCHEDULED';
    IF v_clash > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Counsellor already has a session booked at this time slot.';
    END IF;
END$$

CREATE TRIGGER trg_single_active_model
BEFORE UPDATE ON ml_model
FOR EACH ROW
BEGIN
    IF NEW.is_active = TRUE AND OLD.is_active = FALSE
       AND EXISTS (SELECT 1 FROM ml_model
                    WHERE model_id <> NEW.model_id AND is_active = TRUE) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Another model is already active. Use CALL sp_activate_model(model_id) to switch.';
    END IF;
END$$

CREATE PROCEDURE sp_activate_model(IN p_model_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF NOT EXISTS (SELECT 1 FROM ml_model WHERE model_id = p_model_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No such model.';
    END IF;

    START TRANSACTION;
      UPDATE ml_model SET is_active = FALSE
       WHERE is_active = TRUE AND model_id <> p_model_id;
      UPDATE ml_model SET is_active = TRUE
       WHERE model_id = p_model_id;
    COMMIT;
END$$

CREATE FUNCTION fn_student_risk_index(p_student_id INT)
RETURNS DECIMAL(5,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_score INT DEFAULT 0;

    SELECT COUNT(*),
           SUM(CASE WHEN predicted_level = 2 THEN 3
                    WHEN predicted_level = 1 THEN 2 ELSE 0 END)
      INTO v_total, v_score
      FROM assessment WHERE student_id = p_student_id;

    IF v_total = 0 THEN
        RETURN 0.00;
    END IF;
    RETURN ROUND(v_score * 100.0 / (v_total * 3.0), 2);
END$$

CREATE PROCEDURE sp_record_assessment(
    IN  p_student_id INT,
    IN  p_model_id   INT,
    IN  p_text       VARCHAR(1000),
    IN  p_level      TINYINT,
    IN  p_confidence DECIMAL(6,5),
    IN  p_theme_id   INT,
    IN  p_prob_low   DECIMAL(6,5),
    IN  p_prob_mod   DECIMAL(6,5),
    IN  p_prob_high  DECIMAL(6,5),
    OUT p_assessment_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
      INSERT INTO assessment (student_id, model_id, entry_text, char_count,
                              word_count, predicted_level, confidence, predicted_theme)
      VALUES (p_student_id, p_model_id, p_text, CHAR_LENGTH(p_text),
              CHAR_LENGTH(p_text) - CHAR_LENGTH(REPLACE(p_text,' ','')) + 1,
              p_level, p_confidence, p_theme_id);

      SET p_assessment_id = LAST_INSERT_ID();

      INSERT INTO assessment_score (assessment_id, level_code, probability) VALUES
        (p_assessment_id, 0, p_prob_low),
        (p_assessment_id, 1, p_prob_mod),
        (p_assessment_id, 2, p_prob_high);
    COMMIT;
END$$

CREATE PROCEDURE sp_update_alert_status(
    IN p_alert_id INT,
    IN p_status   VARCHAR(15),
    IN p_remarks  VARCHAR(300))
BEGIN
    DECLARE v_exists INT;
    SELECT COUNT(*) INTO v_exists FROM alert WHERE alert_id = p_alert_id;
    IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No such alert.';
    END IF;
    UPDATE alert
       SET status  = p_status,
           remarks = COALESCE(p_remarks, remarks)
     WHERE alert_id = p_alert_id;
END$$

CREATE PROCEDURE sp_flag_at_risk_students(IN p_threshold DECIMAL(5,2))
BEGIN
    DECLARE v_done    INT DEFAULT FALSE;
    DECLARE v_id      INT;
    DECLARE v_name    VARCHAR(80);
    DECLARE v_risk    DECIMAL(5,2);
    DECLARE v_flagged INT DEFAULT 0;

    DECLARE cur_students CURSOR FOR
        SELECT student_id, full_name FROM student WHERE is_active = TRUE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    DROP TEMPORARY TABLE IF EXISTS tmp_at_risk;
    CREATE TEMPORARY TABLE tmp_at_risk (
        student_id INT, full_name VARCHAR(80), risk_index DECIMAL(5,2));

    OPEN cur_students;
    read_loop: LOOP
        FETCH cur_students INTO v_id, v_name;
        IF v_done THEN
            LEAVE read_loop;
        END IF;

        SET v_risk = fn_student_risk_index(v_id);
        IF v_risk >= p_threshold THEN
            INSERT INTO tmp_at_risk VALUES (v_id, v_name, v_risk);
            SET v_flagged = v_flagged + 1;
        END IF;
    END LOOP;
    CLOSE cur_students;

    SELECT * FROM tmp_at_risk ORDER BY risk_index DESC;
    SELECT v_flagged AS students_flagged, p_threshold AS threshold_used;
    DROP TEMPORARY TABLE IF EXISTS tmp_at_risk;
END$$

CREATE PROCEDURE sp_department_report(
    IN  p_dept_code VARCHAR(10),
    OUT p_high_pct  DECIMAL(5,2))
BEGIN
    SELECT high_stress_pct INTO p_high_pct
      FROM v_dept_stress_summary WHERE dept_code = p_dept_code;

    SELECT s.enrollment_no, s.full_name, s.year_of_study,
           fn_student_risk_index(s.student_id) AS risk_index
      FROM student s
      JOIN department d ON s.dept_id = d.dept_id
     WHERE d.dept_code = p_dept_code
     ORDER BY risk_index DESC;
END$$

DELIMITER ;
