USE mindcare;

DROP VIEW IF EXISTS v_place_confusion;
DROP VIEW IF EXISTS v_scenario_stats;
DROP VIEW IF EXISTS v_rescue_summary;
DROP TABLE IF EXISTS rescue_round;
DROP TABLE IF EXISTS rescue_game;
DROP TABLE IF EXISTS scenario;
DROP TABLE IF EXISTS place;
DROP PROCEDURE IF EXISTS sp_rescue_report;

CREATE TABLE place (
    place_id      INT AUTO_INCREMENT PRIMARY KEY,
    code          VARCHAR(20)  NOT NULL UNIQUE,
    name          VARCHAR(40)  NOT NULL UNIQUE,
    helps_with    VARCHAR(160) NOT NULL,
    color_hex     CHAR(7)      NOT NULL,
    display_order INT          NOT NULL UNIQUE,
    CONSTRAINT chk_place_code CHECK (code = UPPER(code) COLLATE utf8mb4_bin)
) ENGINE=InnoDB;

CREATE TABLE scenario (
    scenario_id      INT AUTO_INCREMENT PRIMARY KEY,
    age_group_id     INT          NOT NULL,
    correct_place_id INT          NOT NULL,
    icon             VARCHAR(16)  NOT NULL,
    title            VARCHAR(60)  NOT NULL,
    story            VARCHAR(300) NOT NULL,
    explanation      VARCHAR(400) NOT NULL,
    urgency          INT          NOT NULL DEFAULT 2,
    time_limit_sec   INT          NOT NULL DEFAULT 20,
    is_opening       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    opening_group    INT GENERATED ALWAYS AS (IF(is_opening, age_group_id, NULL)) STORED,
    CONSTRAINT fk_scenario_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_scenario_place FOREIGN KEY (correct_place_id)
        REFERENCES place (place_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_scenario_title   UNIQUE (age_group_id, title),
    CONSTRAINT uq_scenario_opening UNIQUE (opening_group),
    CONSTRAINT chk_urgency         CHECK (urgency BETWEEN 1 AND 3),
    CONSTRAINT chk_scenario_time   CHECK (time_limit_sec BETWEEN 5 AND 120),
    INDEX idx_scenario_pick (age_group_id, is_active)
) ENGINE=InnoDB;

CREATE TABLE rescue_game (
    game_id         INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT          NOT NULL,
    age_group_id    INT          NOT NULL,
    age_at_play     INT,
    status          ENUM('IN_PROGRESS','COMPLETED','ABANDONED') NOT NULL DEFAULT 'IN_PROGRESS',
    started_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    rounds          INT,
    correct_rounds  INT,
    score           INT,
    max_score       INT,
    accuracy_pct    DECIMAL(5,1),
    avg_response_ms INT,
    stars           INT,
    CONSTRAINT fk_game_student FOREIGN KEY (student_id)
        REFERENCES student (student_id) ON DELETE CASCADE,
    CONSTRAINT fk_game_age FOREIGN KEY (age_group_id)
        REFERENCES age_group (age_group_id) ON UPDATE CASCADE,
    CONSTRAINT chk_game_stars    CHECK (stars IS NULL OR stars BETWEEN 0 AND 3),
    CONSTRAINT chk_game_accuracy CHECK (accuracy_pct IS NULL OR accuracy_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_game_score    CHECK (score IS NULL OR (score >= 0 AND score <= max_score)),
    CONSTRAINT chk_game_age      CHECK (age_at_play IS NULL OR age_at_play BETWEEN 0 AND 120),
    INDEX idx_game_student (student_id, started_at)
) ENGINE=InnoDB;

CREATE TABLE rescue_round (
    game_id         INT         NOT NULL,
    round_no        INT         NOT NULL,
    scenario_id     INT         NOT NULL,
    shown_at        DATETIME(3),
    chosen_place_id INT,
    is_correct      BOOLEAN,
    response_ms     INT,
    points          INT,
    answered_at     DATETIME(3),
    PRIMARY KEY (game_id, round_no),
    CONSTRAINT uq_round_scenario UNIQUE (game_id, scenario_id),
    CONSTRAINT fk_round_game FOREIGN KEY (game_id)
        REFERENCES rescue_game (game_id) ON DELETE CASCADE,
    CONSTRAINT fk_round_scenario FOREIGN KEY (scenario_id)
        REFERENCES scenario (scenario_id) ON DELETE RESTRICT,
    CONSTRAINT fk_round_place FOREIGN KEY (chosen_place_id)
        REFERENCES place (place_id) ON DELETE RESTRICT,
    CONSTRAINT chk_round_no     CHECK (round_no > 0),
    CONSTRAINT chk_round_ms     CHECK (response_ms IS NULL OR response_ms >= 0),
    CONSTRAINT chk_round_points CHECK (points IS NULL OR points BETWEEN 0 AND 15),
    INDEX idx_round_scenario (scenario_id),
    INDEX idx_round_place (chosen_place_id)
) ENGINE=InnoDB;

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
        ROUND(TIMESTAMPDIFF(SECOND, g.started_at, g.completed_at) / 60, 1) AS minutes_taken,
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
        CAST(AVG(r.response_ms) AS SIGNED)                        AS avg_response_ms,
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

DELIMITER $$

CREATE TRIGGER trg_rescue_round_locked
BEFORE UPDATE ON rescue_round
FOR EACH ROW
BEGIN
    IF OLD.answered_at IS NOT NULL
       AND NOT (NEW.chosen_place_id <=> OLD.chosen_place_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'This emergency has already been answered.';
    END IF;
END$$

CREATE TRIGGER trg_rescue_score_round
BEFORE UPDATE ON rescue_round
FOR EACH ROW
FOLLOWS trg_rescue_round_locked
BEGIN
    DECLARE v_limit   INT;
    DECLARE v_correct INT;

    IF NEW.chosen_place_id IS NOT NULL
       AND NOT (NEW.chosen_place_id <=> OLD.chosen_place_id) THEN
        SELECT time_limit_sec, correct_place_id INTO v_limit, v_correct
          FROM scenario WHERE scenario_id = NEW.scenario_id;

        SET NEW.answered_at = COALESCE(NEW.answered_at, NOW(3));
        IF NEW.response_ms IS NULL AND NEW.shown_at IS NOT NULL THEN
            SET NEW.response_ms = GREATEST(0,
                TIMESTAMPDIFF(MICROSECOND, NEW.shown_at, NEW.answered_at) DIV 1000);
        END IF;

        IF NEW.response_ms IS NOT NULL AND NEW.response_ms > (v_limit + 5) * 1000 THEN
            SET NEW.is_correct = FALSE;
        ELSE
            SET NEW.is_correct = (NEW.chosen_place_id = v_correct);
        END IF;

        SET NEW.points = CASE
                WHEN NEW.is_correct = FALSE THEN 0
                WHEN NEW.response_ms IS NULL THEN 10
                WHEN NEW.response_ms <= v_limit * 1000 DIV 3 THEN 15
                WHEN NEW.response_ms <= v_limit * 2000 DIV 3 THEN 12
                ELSE 10
            END;
    END IF;
END$$

CREATE TRIGGER trg_rescue_timeout
BEFORE UPDATE ON rescue_round
FOR EACH ROW
FOLLOWS trg_rescue_score_round
BEGIN
    IF NEW.answered_at IS NOT NULL AND OLD.answered_at IS NULL
       AND NEW.chosen_place_id IS NULL AND NEW.is_correct IS NULL THEN
        SET NEW.is_correct = FALSE;
        SET NEW.points = 0;
        IF NEW.response_ms IS NULL AND NEW.shown_at IS NOT NULL THEN
            SET NEW.response_ms = GREATEST(0,
                TIMESTAMPDIFF(MICROSECOND, NEW.shown_at, NEW.answered_at) DIV 1000);
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_rescue_finish_game
BEFORE UPDATE ON rescue_game
FOR EACH ROW
BEGIN
    DECLARE v_rounds  INT;
    DECLARE v_correct INT;
    DECLARE v_score   INT;
    DECLARE v_pct     DECIMAL(5,1);
    DECLARE v_ms      INT;

    IF NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED' THEN
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END), 0),
               COALESCE(SUM(points), 0),
               ROUND(100.0 * SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1)
          INTO v_rounds, v_correct, v_score, v_pct
          FROM rescue_round WHERE game_id = NEW.game_id;

        SELECT CAST(AVG(response_ms) AS SIGNED) INTO v_ms
          FROM rescue_round WHERE game_id = NEW.game_id AND chosen_place_id IS NOT NULL;

        SET NEW.completed_at    = COALESCE(NEW.completed_at, NOW());
        SET NEW.rounds          = v_rounds;
        SET NEW.correct_rounds  = v_correct;
        SET NEW.score           = v_score;
        SET NEW.max_score       = v_rounds * 15;
        SET NEW.accuracy_pct    = v_pct;
        SET NEW.avg_response_ms = v_ms;
        SET NEW.stars = CASE
                WHEN v_pct >= 85 THEN 3
                WHEN v_pct >= 60 THEN 2
                WHEN v_pct >= 35 THEN 1
                ELSE 0
            END;
    END IF;
END$$

CREATE PROCEDURE sp_rescue_report(IN p_student_id INT)
BEGIN
    SELECT game_id, age_group, completed_at, score, max_score, correct_rounds, rounds, stars
      FROM v_rescue_summary
     WHERE student_id = p_student_id AND status = 'COMPLETED'
     ORDER BY completed_at DESC;

    SELECT p.name AS right_place,
           SUM(CASE WHEN r.is_correct = 1 THEN 1 ELSE 0 END) AS right_answers,
           COUNT(*) AS emergencies
      FROM rescue_round r
      JOIN rescue_game g ON r.game_id = g.game_id
      JOIN scenario s    ON r.scenario_id = s.scenario_id
      JOIN place p       ON s.correct_place_id = p.place_id
     WHERE g.student_id = p_student_id AND r.answered_at IS NOT NULL
     GROUP BY p.place_id, p.name
     ORDER BY right_answers / COUNT(*);
END$$

DELIMITER ;
