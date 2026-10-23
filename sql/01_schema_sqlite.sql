PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS counselling_session;
DROP TABLE IF EXISTS alert;
DROP TABLE IF EXISTS assessment_keyword;
DROP TABLE IF EXISTS assessment_score;
DROP TABLE IF EXISTS assessment;
DROP TABLE IF EXISTS wellness_log;
DROP TABLE IF EXISTS training_corpus;
DROP TABLE IF EXISTS keyword_lexicon;
DROP TABLE IF EXISTS ml_model;
DROP TABLE IF EXISTS app_user;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS counsellor;
DROP TABLE IF EXISTS theme;
DROP TABLE IF EXISTS stress_level;
DROP TABLE IF EXISTS department;

CREATE TABLE department (
    dept_id     INTEGER      PRIMARY KEY AUTOINCREMENT,
    dept_code   VARCHAR(10)  NOT NULL UNIQUE,
    dept_name   VARCHAR(80)  NOT NULL,
    hod_name    VARCHAR(80),
    CONSTRAINT chk_dept_code_upper CHECK (dept_code = UPPER(dept_code))
);

CREATE TABLE stress_level (
    level_code     INTEGER      PRIMARY KEY,
    level_name     VARCHAR(20)  NOT NULL UNIQUE,
    severity_rank  INTEGER      NOT NULL UNIQUE,
    color_hex      CHAR(7)      NOT NULL,
    description    VARCHAR(200),
    requires_alert INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT chk_level_code  CHECK (level_code BETWEEN 0 AND 2),
    CONSTRAINT chk_req_alert   CHECK (requires_alert IN (0,1))
);

CREATE TABLE theme (
    theme_id    INTEGER      PRIMARY KEY AUTOINCREMENT,
    theme_code  VARCHAR(30)  NOT NULL UNIQUE,
    theme_name  VARCHAR(60)  NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    description VARCHAR(200),
    CONSTRAINT chk_theme_cat CHECK (category IN
        ('Academic','Personal','Health','Financial','Social','Occupational'))
);

CREATE TABLE counsellor (
    counsellor_id   INTEGER      PRIMARY KEY AUTOINCREMENT,
    emp_code        VARCHAR(15)  NOT NULL UNIQUE,
    full_name       VARCHAR(80)  NOT NULL,
    email           VARCHAR(120) NOT NULL UNIQUE,
    phone           VARCHAR(15),
    specialization  VARCHAR(60),
    max_daily_slots INTEGER      NOT NULL DEFAULT 6,
    is_active       INTEGER      NOT NULL DEFAULT 1,
    CONSTRAINT chk_couns_email CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_slots       CHECK (max_daily_slots BETWEEN 1 AND 20),
    CONSTRAINT chk_couns_activ CHECK (is_active IN (0,1))
);

CREATE TABLE student (
    student_id     INTEGER      PRIMARY KEY AUTOINCREMENT,
    enrollment_no  VARCHAR(20)  NOT NULL UNIQUE,
    full_name      VARCHAR(80)  NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    phone          VARCHAR(15),
    gender         VARCHAR(10),
    dob            DATE,
    dept_id        INTEGER      NOT NULL,
    year_of_study  INTEGER      NOT NULL,
    hostel_status  VARCHAR(10)  NOT NULL DEFAULT 'Day Scholar',
    admission_year INTEGER,
    is_active      INTEGER      NOT NULL DEFAULT 1,
    created_at     TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    CONSTRAINT fk_student_dept FOREIGN KEY (dept_id)
        REFERENCES department (dept_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_gender    CHECK (gender IN ('Male','Female','Other')),
    CONSTRAINT chk_year      CHECK (year_of_study BETWEEN 1 AND 5),
    CONSTRAINT chk_hostel    CHECK (hostel_status IN ('Hosteller','Day Scholar')),
    CONSTRAINT chk_stu_email CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_stu_activ CHECK (is_active IN (0,1))
);

CREATE TABLE app_user (
    user_id       INTEGER      PRIMARY KEY AUTOINCREMENT,
    username      VARCHAR(40)  NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    role          VARCHAR(15)  NOT NULL,
    student_id    INTEGER      UNIQUE,
    counsellor_id INTEGER      UNIQUE,
    last_login    TIMESTAMP,
    is_active     INTEGER      NOT NULL DEFAULT 1,
    created_at    TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    CONSTRAINT fk_user_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_couns   FOREIGN KEY (counsellor_id)
        REFERENCES counsellor (counsellor_id) ON DELETE CASCADE,
    CONSTRAINT chk_role CHECK (role IN ('student','counsellor','admin')),
    CONSTRAINT chk_role_link CHECK (
        (role = 'student'    AND student_id IS NOT NULL AND counsellor_id IS NULL) OR
        (role = 'counsellor' AND counsellor_id IS NOT NULL AND student_id IS NULL) OR
        (role = 'admin'      AND student_id IS NULL AND counsellor_id IS NULL)
    )
);

CREATE TABLE ml_model (
    model_id        INTEGER      PRIMARY KEY AUTOINCREMENT,
    model_name      VARCHAR(60)  NOT NULL,
    algorithm       VARCHAR(60)  NOT NULL,
    version         VARCHAR(10)  NOT NULL,
    accuracy        REAL,
    precision_macro REAL,
    recall_macro    REAL,
    f1_macro        REAL,
    train_size      INTEGER,
    test_size       INTEGER,
    feature_count   INTEGER,
    artifact_path   VARCHAR(200),
    trained_at      TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    is_active       INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT uq_model_ver UNIQUE (model_name, algorithm, version),
    CONSTRAINT chk_acc      CHECK (accuracy IS NULL OR (accuracy BETWEEN 0 AND 1)),
    CONSTRAINT chk_f1       CHECK (f1_macro IS NULL OR (f1_macro BETWEEN 0 AND 1)),
    CONSTRAINT chk_mdl_act  CHECK (is_active IN (0,1))
);

CREATE TABLE training_corpus (
    corpus_id  INTEGER      PRIMARY KEY,
    text       VARCHAR(500) NOT NULL,
    label      INTEGER      NOT NULL,
    theme_id   INTEGER      NOT NULL,
    split      VARCHAR(5)   NOT NULL DEFAULT 'train',
    CONSTRAINT fk_corpus_level FOREIGN KEY (label)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE,
    CONSTRAINT fk_corpus_theme FOREIGN KEY (theme_id)
        REFERENCES theme (theme_id) ON UPDATE CASCADE,
    CONSTRAINT chk_split CHECK (split IN ('train','test'))
);

CREATE TABLE keyword_lexicon (
    keyword_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    word       VARCHAR(40)  NOT NULL UNIQUE,
    category   VARCHAR(30)  NOT NULL,
    weight     REAL         NOT NULL DEFAULT 1.0,
    polarity   VARCHAR(10)  NOT NULL DEFAULT 'negative',
    CONSTRAINT chk_polarity CHECK (polarity IN ('positive','negative','neutral')),
    CONSTRAINT chk_weight   CHECK (weight BETWEEN 0 AND 5)
);

CREATE TABLE assessment (
    assessment_id    INTEGER      PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER      NOT NULL,
    model_id         INTEGER      NOT NULL,
    entry_text       VARCHAR(1000) NOT NULL,
    char_count       INTEGER      NOT NULL,
    word_count       INTEGER      NOT NULL,
    predicted_level  INTEGER      NOT NULL,
    confidence       REAL         NOT NULL,
    predicted_theme  INTEGER,
    source           VARCHAR(15)  NOT NULL DEFAULT 'web',
    created_at       TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    CONSTRAINT fk_asmt_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_asmt_model   FOREIGN KEY (model_id)
        REFERENCES ml_model (model_id) ON DELETE RESTRICT,
    CONSTRAINT fk_asmt_level   FOREIGN KEY (predicted_level)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE,
    CONSTRAINT fk_asmt_theme   FOREIGN KEY (predicted_theme)
        REFERENCES theme (theme_id) ON UPDATE CASCADE,
    CONSTRAINT chk_conf   CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT chk_source CHECK (source IN ('web','mobile','chat','import')),
    CONSTRAINT chk_counts CHECK (char_count > 0 AND word_count > 0)
);

CREATE TABLE assessment_score (
    assessment_id INTEGER NOT NULL,
    level_code    INTEGER NOT NULL,
    probability   REAL    NOT NULL,
    PRIMARY KEY (assessment_id, level_code),
    CONSTRAINT fk_score_asmt  FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE CASCADE,
    CONSTRAINT fk_score_level FOREIGN KEY (level_code)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE,
    CONSTRAINT chk_prob CHECK (probability BETWEEN 0 AND 1)
);

CREATE TABLE assessment_keyword (
    assessment_id INTEGER NOT NULL,
    keyword_id    INTEGER NOT NULL,
    occurrences   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (assessment_id, keyword_id),
    CONSTRAINT fk_ak_asmt FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE CASCADE,
    CONSTRAINT fk_ak_kw   FOREIGN KEY (keyword_id)
        REFERENCES keyword_lexicon (keyword_id) ON DELETE CASCADE,
    CONSTRAINT chk_occ CHECK (occurrences > 0)
);

CREATE TABLE alert (
    alert_id        INTEGER      PRIMARY KEY AUTOINCREMENT,
    assessment_id   INTEGER      NOT NULL UNIQUE,
    alert_type      VARCHAR(30)  NOT NULL,
    priority        VARCHAR(10)  NOT NULL,
    status          VARCHAR(12)  NOT NULL DEFAULT 'OPEN',
    assigned_to     INTEGER,
    raised_at       TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    acknowledged_at TIMESTAMP,
    resolved_at     TIMESTAMP,
    remarks         VARCHAR(300),
    CONSTRAINT fk_alert_asmt  FOREIGN KEY (assessment_id)
        REFERENCES assessment (assessment_id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_couns FOREIGN KEY (assigned_to)
        REFERENCES counsellor (counsellor_id) ON DELETE SET NULL,
    CONSTRAINT chk_alert_type CHECK (alert_type IN
        ('HIGH_STRESS','REPEATED_HIGH','CRISIS_KEYWORD','SUSTAINED_DECLINE',
         'CRITICAL_ITEM')),
    CONSTRAINT chk_priority CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    CONSTRAINT chk_status   CHECK (status IN ('OPEN','ACKNOWLEDGED','RESOLVED','DISMISSED'))
);

CREATE TABLE counselling_session (
    session_id       INTEGER      PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER      NOT NULL,
    counsellor_id    INTEGER      NOT NULL,
    alert_id         INTEGER,
    scheduled_at     TIMESTAMP    NOT NULL,
    duration_min     INTEGER      NOT NULL DEFAULT 45,
    mode             VARCHAR(15)  NOT NULL DEFAULT 'In-Person',
    status           VARCHAR(12)  NOT NULL DEFAULT 'SCHEDULED',
    notes            VARCHAR(500),
    follow_up_needed INTEGER      NOT NULL DEFAULT 0,
    created_at       TIMESTAMP    NOT NULL DEFAULT (datetime('now','localtime')),
    CONSTRAINT fk_sess_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_sess_couns   FOREIGN KEY (counsellor_id)
        REFERENCES counsellor (counsellor_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sess_alert   FOREIGN KEY (alert_id)
        REFERENCES alert (alert_id) ON DELETE SET NULL,
    CONSTRAINT chk_mode     CHECK (mode IN ('In-Person','Video','Phone','Chat')),
    CONSTRAINT chk_sess_st  CHECK (status IN ('SCHEDULED','COMPLETED','CANCELLED','NO_SHOW')),
    CONSTRAINT chk_duration CHECK (duration_min BETWEEN 15 AND 180),
    CONSTRAINT chk_followup CHECK (follow_up_needed IN (0,1))
);

CREATE TABLE wellness_log (
    log_id           INTEGER   PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER   NOT NULL,
    log_date         DATE      NOT NULL,
    sleep_hours      REAL,
    exercise_min     INTEGER,
    mood_rating      INTEGER,
    screen_time_hrs  REAL,
    CONSTRAINT fk_wl_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT uq_wl_student_date UNIQUE (student_id, log_date),
    CONSTRAINT chk_sleep  CHECK (sleep_hours IS NULL OR sleep_hours BETWEEN 0 AND 24),
    CONSTRAINT chk_mood   CHECK (mood_rating IS NULL OR mood_rating BETWEEN 1 AND 10),
    CONSTRAINT chk_exer   CHECK (exercise_min IS NULL OR exercise_min BETWEEN 0 AND 600)
);

CREATE INDEX idx_student_dept      ON student (dept_id);
CREATE INDEX idx_student_year      ON student (year_of_study);
CREATE INDEX idx_asmt_student_date ON assessment (student_id, created_at DESC);
CREATE INDEX idx_asmt_level        ON assessment (predicted_level);
CREATE INDEX idx_asmt_theme        ON assessment (predicted_theme);
CREATE INDEX idx_asmt_created      ON assessment (created_at);
CREATE INDEX idx_alert_status      ON alert (status, priority);
CREATE INDEX idx_alert_assigned    ON alert (assigned_to);
CREATE INDEX idx_sess_couns_date   ON counselling_session (counsellor_id, scheduled_at);
CREATE INDEX idx_sess_student      ON counselling_session (student_id);
CREATE INDEX idx_wl_student_date   ON wellness_log (student_id, log_date DESC);
CREATE INDEX idx_corpus_label      ON training_corpus (label);
