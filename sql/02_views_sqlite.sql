DROP VIEW IF EXISTS v_assessment_detail;
DROP VIEW IF EXISTS v_student_risk_profile;
DROP VIEW IF EXISTS v_high_risk_queue;
DROP VIEW IF EXISTS v_theme_distribution;
DROP VIEW IF EXISTS v_counsellor_workload;
DROP VIEW IF EXISTS v_dept_stress_summary;
DROP VIEW IF EXISTS v_daily_trend;
DROP VIEW IF EXISTS v_wellness_vs_stress;

CREATE VIEW v_assessment_detail AS
SELECT  a.assessment_id,
        a.created_at,
        s.student_id,
        s.enrollment_no,
        s.full_name          AS student_name,
        d.dept_code,
        d.dept_name,
        s.year_of_study,
        a.entry_text,
        a.word_count,
        sl.level_code,
        sl.level_name        AS stress_level,
        sl.color_hex,
        sl.severity_rank,
        ROUND(a.confidence * 100, 2) AS confidence_pct,
        t.theme_name,
        t.category           AS theme_category,
        m.model_name,
        m.algorithm,
        a.source
FROM        assessment  a
INNER JOIN  student      s  ON a.student_id      = s.student_id
INNER JOIN  department   d  ON s.dept_id         = d.dept_id
INNER JOIN  stress_level sl ON a.predicted_level = sl.level_code
INNER JOIN  ml_model     m  ON a.model_id        = m.model_id
LEFT  JOIN  theme        t  ON a.predicted_theme = t.theme_id;

CREATE VIEW v_student_risk_profile AS
SELECT  s.student_id,
        s.enrollment_no,
        s.full_name,
        d.dept_code,
        s.year_of_study,
        COUNT(a.assessment_id)                                       AS total_assessments,
        SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)       AS high_count,
        SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END)       AS moderate_count,
        SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END)       AS low_count,
        ROUND(AVG(a.predicted_level), 3)                             AS avg_stress_score,
        ROUND(AVG(a.confidence) * 100, 2)                            AS avg_confidence_pct,
        MAX(a.created_at)                                            AS last_assessed_at,
        (SELECT sl.level_name
           FROM assessment a2
           JOIN stress_level sl ON a2.predicted_level = sl.level_code
          WHERE a2.student_id = s.student_id
          ORDER BY a2.created_at DESC, a2.assessment_id DESC
          LIMIT 1)                                                   AS latest_level,
        ROUND( CASE WHEN COUNT(a.assessment_id) = 0 THEN 0 ELSE
               ( SUM(CASE WHEN a.predicted_level = 2 THEN 3
                          WHEN a.predicted_level = 1 THEN 2 ELSE 0 END) * 100.0 )
               / (COUNT(a.assessment_id) * 3.0) END , 2)             AS risk_index
FROM        student     s
INNER JOIN  department  d ON s.dept_id = d.dept_id
LEFT  JOIN  assessment  a ON s.student_id = a.student_id
GROUP BY    s.student_id, s.enrollment_no, s.full_name, d.dept_code, s.year_of_study;

CREATE VIEW v_high_risk_queue AS
SELECT  al.alert_id,
        al.priority,
        al.status,
        al.alert_type,
        al.raised_at,
        s.student_id,
        s.enrollment_no,
        s.full_name        AS student_name,
        s.phone,
        d.dept_code,
        a.assessment_id,
        a.entry_text,
        ROUND(a.confidence * 100, 1) AS confidence_pct,
        t.theme_name,
        c.full_name        AS assigned_counsellor,
        CASE al.priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                         WHEN 'MEDIUM'   THEN 3 ELSE 4 END AS priority_rank
FROM        alert       al
INNER JOIN  assessment  a  ON al.assessment_id  = a.assessment_id
INNER JOIN  student     s  ON a.student_id      = s.student_id
INNER JOIN  department  d  ON s.dept_id         = d.dept_id
LEFT  JOIN  theme       t  ON a.predicted_theme = t.theme_id
LEFT  JOIN  counsellor  c  ON al.assigned_to    = c.counsellor_id
WHERE       al.status IN ('OPEN','ACKNOWLEDGED');

CREATE VIEW v_theme_distribution AS
SELECT  t.theme_id,
        t.theme_name,
        t.category,
        COUNT(a.assessment_id)                                  AS total,
        SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END)  AS low,
        SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END)  AS moderate,
        SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)  AS high,
        ROUND( SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) * 100.0
               / NULLIF(COUNT(a.assessment_id), 0), 2)          AS high_pct
FROM        theme      t
LEFT  JOIN  assessment a ON t.theme_id = a.predicted_theme
GROUP BY    t.theme_id, t.theme_name, t.category;

CREATE VIEW v_counsellor_workload AS
SELECT  c.counsellor_id,
        c.emp_code,
        c.full_name,
        c.specialization,
        c.max_daily_slots,
        COUNT(DISTINCT cs.session_id)                                        AS total_sessions,
        SUM(CASE WHEN cs.status = 'SCHEDULED' THEN 1 ELSE 0 END)             AS upcoming,
        SUM(CASE WHEN cs.status = 'COMPLETED' THEN 1 ELSE 0 END)             AS completed,
        SUM(CASE WHEN cs.status = 'NO_SHOW'   THEN 1 ELSE 0 END)             AS no_shows,
        (SELECT COUNT(*) FROM alert al
          WHERE al.assigned_to = c.counsellor_id AND al.status = 'OPEN')     AS open_alerts,
        COUNT(DISTINCT cs.student_id)                                        AS distinct_students
FROM        counsellor c
LEFT  JOIN  counselling_session cs ON c.counsellor_id = cs.counsellor_id
WHERE       c.is_active = 1
GROUP BY    c.counsellor_id, c.emp_code, c.full_name, c.specialization, c.max_daily_slots;

CREATE VIEW v_dept_stress_summary AS
SELECT  d.dept_id,
        d.dept_code,
        d.dept_name,
        COUNT(DISTINCT s.student_id)                            AS enrolled_students,
        COUNT(DISTINCT a.student_id)                            AS students_assessed,
        COUNT(a.assessment_id)                                  AS total_assessments,
        ROUND(AVG(a.predicted_level), 3)                        AS avg_stress_score,
        SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)  AS high_stress_entries,
        ROUND( SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) * 100.0
               / NULLIF(COUNT(a.assessment_id), 0), 2)          AS high_stress_pct
FROM        department d
LEFT  JOIN  student    s ON d.dept_id    = s.dept_id
LEFT  JOIN  assessment a ON s.student_id = a.student_id
GROUP BY    d.dept_id, d.dept_code, d.dept_name;

CREATE VIEW v_daily_trend AS
SELECT  DATE(a.created_at)                                      AS entry_date,
        COUNT(*)                                                AS total,
        SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END)  AS low,
        SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END)  AS moderate,
        SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)  AS high,
        ROUND(AVG(a.predicted_level), 3)                        AS avg_stress_score
FROM        assessment a
GROUP BY    DATE(a.created_at);

CREATE VIEW v_wellness_vs_stress AS
SELECT  w.student_id,
        s.full_name,
        w.log_date,
        w.sleep_hours,
        w.exercise_min,
        w.mood_rating,
        w.screen_time_hrs,
        COUNT(a.assessment_id)             AS entries_that_day,
        ROUND(AVG(a.predicted_level), 2)   AS avg_stress_that_day
FROM        wellness_log w
INNER JOIN  student      s ON w.student_id = s.student_id
LEFT  JOIN  assessment   a ON a.student_id = w.student_id
                          AND DATE(a.created_at) = w.log_date
GROUP BY    w.student_id, s.full_name, w.log_date, w.sleep_hours,
            w.exercise_min, w.mood_rating, w.screen_time_hrs;
