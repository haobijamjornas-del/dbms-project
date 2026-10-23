PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS v_place_confusion;
DROP VIEW IF EXISTS v_scenario_stats;
DROP VIEW IF EXISTS v_rescue_summary;
DROP TABLE IF EXISTS rescue_round;
DROP TABLE IF EXISTS rescue_game;
DROP TABLE IF EXISTS scenario;
DROP TABLE IF EXISTS place;

CREATE TABLE place (
    place_id      INTEGER      PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(20)  NOT NULL UNIQUE,
    name          VARCHAR(40)  NOT NULL UNIQUE,
    helps_with    VARCHAR(160) NOT NULL,
    color_hex     CHAR(7)      NOT NULL,
    display_order INTEGER      NOT NULL UNIQUE,
    CONSTRAINT chk_place_code CHECK (code = UPPER(code))
);

CREATE TABLE scenario (
    scenario_id      INTEGER      PRIMARY KEY AUTOINCREMENT,
    age_group_id     INTEGER      NOT NULL,
    correct_place_id INTEGER      NOT NULL,
    icon             VARCHAR(16)  NOT NULL,
    title            VARCHAR(60)  NOT NULL,
    story            VARCHAR(300) NOT NULL,
    explanation      VARCHAR(400) NOT NULL,
    urgency          INTEGER      NOT NULL DEFAULT 2,
    time_limit_sec   INTEGER      NOT NULL DEFAULT 20,
    is_opening       INTEGER      NOT NULL DEFAULT 0,
    is_active        INTEGER      NOT NULL DEFAULT 1,
    CONSTRAINT fk_scenario_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_scenario_place FOREIGN KEY (correct_place_id)
        REFERENCES place (place_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_scenario_title UNIQUE (age_group_id, title),
    CONSTRAINT chk_urgency       CHECK (urgency BETWEEN 1 AND 3),
    CONSTRAINT chk_scenario_time CHECK (time_limit_sec BETWEEN 5 AND 120),
    CONSTRAINT chk_opening       CHECK (is_opening IN (0,1)),
    CONSTRAINT chk_scenario_act  CHECK (is_active IN (0,1))
);

CREATE TABLE rescue_game (
    game_id         INTEGER     PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER     NOT NULL,
    age_group_id    INTEGER     NOT NULL,
    age_at_play     INTEGER,
    status          VARCHAR(12) NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      TIMESTAMP   NOT NULL DEFAULT (datetime('now','localtime')),
    completed_at    TIMESTAMP,
    rounds          INTEGER,
    correct_rounds  INTEGER,
    score           INTEGER,
    max_score       INTEGER,
    accuracy_pct    REAL,
    avg_response_ms INTEGER,
    stars           INTEGER,
    CONSTRAINT fk_game_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_game_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE,
    CONSTRAINT chk_game_status   CHECK (status IN ('IN_PROGRESS','COMPLETED','ABANDONED')),
    CONSTRAINT chk_game_stars    CHECK (stars IS NULL OR stars BETWEEN 0 AND 3),
    CONSTRAINT chk_game_accuracy CHECK (accuracy_pct IS NULL OR accuracy_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_game_score    CHECK (score IS NULL OR (score >= 0 AND score <= max_score)),
    CONSTRAINT chk_game_age      CHECK (age_at_play IS NULL OR age_at_play BETWEEN 0 AND 120)
);

CREATE TABLE rescue_round (
    game_id         INTEGER   NOT NULL,
    round_no        INTEGER   NOT NULL,
    scenario_id     INTEGER   NOT NULL,
    shown_at        TIMESTAMP,
    chosen_place_id INTEGER,
    is_correct      INTEGER,
    response_ms     INTEGER,
    points          INTEGER,
    answered_at     TIMESTAMP,
    PRIMARY KEY (game_id, round_no),
    CONSTRAINT uq_round_scenario UNIQUE (game_id, scenario_id),
    CONSTRAINT fk_round_game FOREIGN KEY (game_id)
        REFERENCES rescue_game (game_id) ON DELETE CASCADE,
    CONSTRAINT fk_round_scenario FOREIGN KEY (scenario_id)
        REFERENCES scenario (scenario_id) ON DELETE RESTRICT,
    CONSTRAINT fk_round_place FOREIGN KEY (chosen_place_id)
        REFERENCES place (place_id) ON DELETE RESTRICT,
    CONSTRAINT chk_round_no      CHECK (round_no > 0),
    CONSTRAINT chk_round_correct CHECK (is_correct IS NULL OR is_correct IN (0,1)),
    CONSTRAINT chk_round_ms      CHECK (response_ms IS NULL OR response_ms >= 0),
    CONSTRAINT chk_round_points  CHECK (points IS NULL OR points BETWEEN 0 AND 15)
);

CREATE UNIQUE INDEX uq_scenario_opening ON scenario (age_group_id) WHERE is_opening = 1;
CREATE INDEX idx_scenario_pick  ON scenario (age_group_id, is_active);
CREATE INDEX idx_game_student   ON rescue_game (student_id, started_at DESC);
CREATE INDEX idx_round_scenario ON rescue_round (scenario_id);
CREATE INDEX idx_round_place    ON rescue_round (chosen_place_id);

CREATE VIEW v_rescue_summary AS
SELECT  g.game_id,
        g.student_id,
        s.full_name     AS student_name,
        s.enrollment_no,
        d.dept_code,
        s.year_of_study,
        ag.age_group_id,
        ag.label        AS age_group,
        g.age_at_play,
        g.status,
        g.started_at,
        g.completed_at,
        g.rounds,
        g.correct_rounds,
        g.score,
        g.max_score,
        g.accuracy_pct,
        g.avg_response_ms,
        g.stars,
        ROUND((JULIANDAY(g.completed_at) - JULIANDAY(g.started_at)) * 1440, 1) AS minutes_taken,
        (SELECT COUNT(*) FROM rescue_round r WHERE r.game_id = g.game_id)          AS round_count,
        (SELECT COUNT(*) FROM rescue_round r
          WHERE r.game_id = g.game_id AND r.answered_at IS NOT NULL)               AS answered_count
FROM        rescue_game g
INNER JOIN  student     s  ON g.student_id   = s.student_id
INNER JOIN  department  d  ON s.dept_id      = d.dept_id
INNER JOIN  age_group   ag ON g.age_group_id = ag.age_group_id;

CREATE VIEW v_scenario_stats AS
SELECT  sc.scenario_id,
        ag.label        AS age_group,
        sc.icon,
        sc.title,
        p.name          AS correct_place,
        sc.urgency,
        COUNT(r.answered_at)                                      AS plays,
        SUM(CASE WHEN r.is_correct = 1 THEN 1 ELSE 0 END)         AS correct,
        ROUND(100.0 * SUM(CASE WHEN r.is_correct = 1 THEN 1 ELSE 0 END)
              / NULLIF(COUNT(r.answered_at), 0), 1)               AS pct_correct,
        CAST(AVG(r.response_ms) AS INTEGER)                       AS avg_response_ms,
        (SELECT wp.name
           FROM rescue_round w
           JOIN place wp ON wp.place_id = w.chosen_place_id
          WHERE w.scenario_id = sc.scenario_id AND w.is_correct = 0
          GROUP BY wp.place_id, wp.name
          ORDER BY COUNT(*) DESC, wp.name
          LIMIT 1)                                                AS most_common_mistake
FROM        scenario  sc
INNER JOIN  age_group ag ON sc.age_group_id     = ag.age_group_id
INNER JOIN  place     p  ON sc.correct_place_id = p.place_id
LEFT  JOIN  rescue_round r ON r.scenario_id     = sc.scenario_id
GROUP BY    sc.scenario_id, ag.label, sc.icon, sc.title, p.name, sc.urgency;

CREATE VIEW v_place_confusion AS
SELECT  right_place.place_id                        AS correct_place_id,
        right_place.name                            AS correct_place,
        right_place.display_order                   AS correct_order,
        COALESCE(chosen.name, 'Time ran out')       AS chosen_place,
        COALESCE(chosen.display_order, 99)          AS chosen_order,
        COUNT(*)                                    AS times
FROM        rescue_round r
INNER JOIN  scenario     sc          ON r.scenario_id       = sc.scenario_id
INNER JOIN  place        right_place ON sc.correct_place_id = right_place.place_id
LEFT  JOIN  place        chosen      ON r.chosen_place_id   = chosen.place_id
WHERE       r.answered_at IS NOT NULL
GROUP BY    right_place.place_id, right_place.name, right_place.display_order,
            chosen.name, chosen.display_order;

DROP TRIGGER IF EXISTS trg_rescue_round_locked;
DROP TRIGGER IF EXISTS trg_rescue_score_round;
DROP TRIGGER IF EXISTS trg_rescue_timeout;
DROP TRIGGER IF EXISTS trg_rescue_finish_game;

CREATE TRIGGER trg_rescue_round_locked
BEFORE UPDATE OF chosen_place_id ON rescue_round
FOR EACH ROW
WHEN OLD.answered_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'This emergency has already been answered.');
END;

CREATE TRIGGER trg_rescue_score_round
AFTER UPDATE OF chosen_place_id ON rescue_round
FOR EACH ROW
WHEN NEW.chosen_place_id IS NOT NULL
BEGIN
    UPDATE rescue_round
       SET answered_at = COALESCE(NEW.answered_at, strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
           response_ms = COALESCE(NEW.response_ms,
               CASE WHEN NEW.shown_at IS NULL THEN NULL
                    ELSE MAX(0, CAST(ROUND((JULIANDAY('now', 'localtime') - JULIANDAY(NEW.shown_at))
                                           * 86400000) AS INTEGER)) END)
     WHERE game_id = NEW.game_id AND round_no = NEW.round_no;

    UPDATE rescue_round
       SET is_correct = CASE
               WHEN response_ms IS NOT NULL
                AND response_ms > ((SELECT time_limit_sec FROM scenario WHERE scenario_id = NEW.scenario_id) + 5) * 1000
               THEN 0
               WHEN NEW.chosen_place_id = (SELECT correct_place_id FROM scenario WHERE scenario_id = NEW.scenario_id)
               THEN 1
               ELSE 0
           END
     WHERE game_id = NEW.game_id AND round_no = NEW.round_no;

    UPDATE rescue_round
       SET points = CASE
               WHEN is_correct = 0 THEN 0
               WHEN response_ms IS NULL THEN 10
               WHEN response_ms <= (SELECT time_limit_sec FROM scenario WHERE scenario_id = NEW.scenario_id) * 1000 / 3
               THEN 15
               WHEN response_ms <= (SELECT time_limit_sec FROM scenario WHERE scenario_id = NEW.scenario_id) * 2000 / 3
               THEN 12
               ELSE 10
           END
     WHERE game_id = NEW.game_id AND round_no = NEW.round_no;
END;

CREATE TRIGGER trg_rescue_timeout
AFTER UPDATE OF answered_at ON rescue_round
FOR EACH ROW
WHEN NEW.answered_at IS NOT NULL AND NEW.chosen_place_id IS NULL AND NEW.is_correct IS NULL
BEGIN
    UPDATE rescue_round
       SET is_correct  = 0,
           points      = 0,
           response_ms = COALESCE(NEW.response_ms,
               CASE WHEN NEW.shown_at IS NULL THEN NULL
                    ELSE MAX(0, CAST(ROUND((JULIANDAY(NEW.answered_at) - JULIANDAY(NEW.shown_at))
                                           * 86400000) AS INTEGER)) END)
     WHERE game_id = NEW.game_id AND round_no = NEW.round_no;
END;

CREATE TRIGGER trg_rescue_finish_game
AFTER UPDATE OF status ON rescue_game
FOR EACH ROW
WHEN NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED'
BEGIN
    UPDATE rescue_game
       SET completed_at    = COALESCE(NEW.completed_at, datetime('now', 'localtime')),
           rounds          = (SELECT COUNT(*) FROM rescue_round WHERE game_id = NEW.game_id),
           correct_rounds  = (SELECT COUNT(*) FROM rescue_round
                               WHERE game_id = NEW.game_id AND is_correct = 1),
           score           = (SELECT COALESCE(SUM(points), 0) FROM rescue_round WHERE game_id = NEW.game_id),
           max_score       = (SELECT COUNT(*) * 15 FROM rescue_round WHERE game_id = NEW.game_id),
           accuracy_pct    = (SELECT ROUND(100.0 * SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END)
                                           / NULLIF(COUNT(*), 0), 1)
                                FROM rescue_round WHERE game_id = NEW.game_id),
           avg_response_ms = (SELECT CAST(AVG(response_ms) AS INTEGER) FROM rescue_round
                               WHERE game_id = NEW.game_id AND chosen_place_id IS NOT NULL)
     WHERE game_id = NEW.game_id;

    UPDATE rescue_game
       SET stars = CASE
               WHEN accuracy_pct >= 85 THEN 3
               WHEN accuracy_pct >= 60 THEN 2
               WHEN accuracy_pct >= 35 THEN 1
               ELSE 0
           END
     WHERE game_id = NEW.game_id;
END;
