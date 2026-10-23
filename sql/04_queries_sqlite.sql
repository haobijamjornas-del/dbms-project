SELECT enrollment_no                  AS roll_no,
       full_name                      AS student,
       year_of_study                  AS yr,
       (2026 - admission_year)        AS years_on_campus
FROM   student
ORDER  BY full_name
LIMIT  10;

SELECT full_name, year_of_study, hostel_status
FROM   student
WHERE  year_of_study BETWEEN 2 AND 3
  AND  hostel_status = 'Hosteller'
  AND  (full_name LIKE 'A%' OR full_name LIKE 'S%')
ORDER  BY year_of_study, full_name;

SELECT DISTINCT category FROM theme ORDER BY category;

SELECT alert_id, priority, status,
       COALESCE(resolved_at, 'still open')            AS resolved,
       COALESCE(remarks, 'no remarks recorded')       AS remarks,
       CASE WHEN resolved_at IS NULL THEN 'pending'
            ELSE 'closed' END                         AS outcome
FROM   alert
ORDER  BY (resolved_at IS NOT NULL), alert_id
LIMIT  10;

SELECT s.enrollment_no, s.full_name, d.dept_name, sl.level_name, a.created_at
FROM        assessment   a
INNER JOIN  student      s  ON a.student_id      = s.student_id
INNER JOIN  department   d  ON s.dept_id         = d.dept_id
INNER JOIN  stress_level sl ON a.predicted_level = sl.level_code
ORDER  BY a.created_at DESC
LIMIT  15;

SELECT s.full_name, d.dept_code, COUNT(a.assessment_id) AS entries
FROM        student    s
INNER JOIN  department d ON s.dept_id = d.dept_id
LEFT  JOIN  assessment a ON s.student_id = a.student_id
GROUP  BY s.student_id, s.full_name, d.dept_code
ORDER  BY entries ASC, s.full_name
LIMIT  15;

SELECT a.assessment_id, s.full_name, d.dept_code, sl.level_name,
       t.theme_name, m.algorithm
FROM        assessment   a
INNER JOIN  student      s  ON a.student_id      = s.student_id
INNER JOIN  department   d  ON s.dept_id         = d.dept_id
INNER JOIN  stress_level sl ON a.predicted_level = sl.level_code
INNER JOIN  ml_model     m  ON a.model_id        = m.model_id
LEFT  JOIN  theme        t  ON a.predicted_theme = t.theme_id
LIMIT  10;

SELECT a.full_name AS student_1, b.full_name AS student_2,
       d.dept_code, a.year_of_study
FROM        student    a
INNER JOIN  student    b ON a.dept_id       = b.dept_id
                        AND a.year_of_study = b.year_of_study
                        AND a.student_id    < b.student_id
INNER JOIN  department d ON a.dept_id = d.dept_id
ORDER  BY d.dept_code, a.year_of_study
LIMIT  12;

SELECT d.dept_code, sl.level_name,
       COUNT(a.assessment_id) AS entries
FROM        department   d
CROSS JOIN  stress_level sl
LEFT  JOIN  student      s ON s.dept_id = d.dept_id
LEFT  JOIN  assessment   a ON a.student_id = s.student_id
                          AND a.predicted_level = sl.level_code
GROUP  BY d.dept_code, sl.level_name, sl.severity_rank
ORDER  BY d.dept_code, sl.severity_rank;

SELECT k.word, k.category, COUNT(DISTINCT ak.assessment_id) AS appearances,
       COUNT(DISTINCT a.student_id)                          AS distinct_students
FROM        keyword_lexicon    k
INNER JOIN  assessment_keyword ak ON k.keyword_id    = ak.keyword_id
INNER JOIN  assessment         a  ON ak.assessment_id = a.assessment_id
GROUP  BY k.keyword_id, k.word, k.category
ORDER  BY appearances DESC
LIMIT  15;

SELECT COUNT(*)                     AS total_entries,
       COUNT(DISTINCT student_id)   AS distinct_students,
       ROUND(AVG(confidence), 4)    AS avg_confidence,
       MIN(confidence)              AS min_confidence,
       MAX(confidence)              AS max_confidence,
       SUM(word_count)              AS total_words
FROM   assessment;

SELECT t.theme_name,
       COUNT(*)                                               AS entries,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high,
       ROUND(AVG(a.confidence) * 100, 2)                      AS avg_conf_pct
FROM        assessment a
INNER JOIN  theme      t ON a.predicted_theme = t.theme_id
GROUP  BY t.theme_id, t.theme_name
HAVING COUNT(*) >= 30
ORDER  BY high DESC;

SELECT d.dept_code,
       SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END) AS low,
       SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END) AS moderate,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high,
       COUNT(*)                                               AS total
FROM        assessment a
INNER JOIN  student    s ON a.student_id = s.student_id
INNER JOIN  department d ON s.dept_id    = d.dept_id
GROUP  BY d.dept_code
ORDER  BY high DESC;

SELECT CASE WHEN sleep_hours <  6 THEN 'under 6h'
            WHEN sleep_hours <  7 THEN '6-7h'
            WHEN sleep_hours <  8 THEN '7-8h'
            ELSE                       '8h or more' END AS sleep_band,
       COUNT(*)                    AS logged_days,
       ROUND(AVG(mood_rating), 2)  AS avg_mood,
       ROUND(AVG(screen_time_hrs), 1) AS avg_screen_hrs
FROM   wellness_log
WHERE  sleep_hours IS NOT NULL
GROUP  BY sleep_band
ORDER  BY avg_mood DESC;

SELECT full_name, dept_code, avg_stress_score
FROM   v_student_risk_profile
WHERE  avg_stress_score > (SELECT AVG(predicted_level) FROM assessment)
ORDER  BY avg_stress_score DESC
LIMIT  15;

SELECT s.full_name,
       (SELECT COUNT(*) FROM assessment a
         WHERE a.student_id = s.student_id)                        AS entries,
       (SELECT MAX(created_at) FROM assessment a
         WHERE a.student_id = s.student_id)                        AS last_entry,
       (SELECT COUNT(*) FROM counselling_session cs
         WHERE cs.student_id = s.student_id AND cs.status = 'COMPLETED')
                                                                   AS sessions_done
FROM   student s
ORDER  BY entries DESC
LIMIT  12;

SELECT full_name, enrollment_no
FROM   student
WHERE  student_id IN (SELECT a.student_id
                        FROM alert al
                        JOIN assessment a ON al.assessment_id = a.assessment_id
                       WHERE al.priority = 'CRITICAL')
ORDER  BY full_name;

SELECT s.full_name, d.dept_code
FROM        student    s
INNER JOIN  department d ON s.dept_id = d.dept_id
WHERE  EXISTS (SELECT 1
                 FROM alert al
                 JOIN assessment a ON al.assessment_id = a.assessment_id
                WHERE a.student_id = s.student_id AND al.status = 'OPEN')
ORDER  BY s.full_name
LIMIT  15;

SELECT DISTINCT s.enrollment_no, s.full_name, d.dept_code
FROM        student    s
INNER JOIN  department d ON s.dept_id = d.dept_id
INNER JOIN  assessment a ON s.student_id = a.student_id
WHERE  a.predicted_level = 2
  AND  NOT EXISTS (SELECT 1 FROM counselling_session cs
                    WHERE cs.student_id = s.student_id)
ORDER  BY s.full_name;

SELECT s.full_name, DATE(a.created_at) AS worst_day,
       ROUND(AVG(a.predicted_level), 2) AS day_score
FROM        assessment a
INNER JOIN  student    s ON a.student_id = s.student_id
GROUP  BY s.student_id, s.full_name, DATE(a.created_at)
HAVING AVG(a.predicted_level) >= (
        SELECT MAX(day_avg)
          FROM (SELECT AVG(a2.predicted_level) AS day_avg
                  FROM assessment a2
                 WHERE a2.student_id = a.student_id
                 GROUP BY DATE(a2.created_at)))
ORDER  BY day_score DESC, s.full_name
LIMIT  10;

SELECT band, COUNT(*) AS students
FROM  (SELECT student_id,
              CASE WHEN risk_index >= 50 THEN 'High risk'
                   WHEN risk_index >= 25 THEN 'Watch'
                   ELSE                       'Stable' END AS band
         FROM v_student_risk_profile
        WHERE total_assessments > 0) AS banded
GROUP  BY band
ORDER  BY students DESC;

SELECT 'Student'    AS person_type, full_name, email FROM student    WHERE is_active = 1
UNION ALL
SELECT 'Counsellor' AS person_type, full_name, email FROM counsellor WHERE is_active = 1
ORDER  BY person_type, full_name
LIMIT  20;

SELECT student_id FROM v_student_risk_profile WHERE risk_index >= 50
INTERSECT
SELECT student_id FROM counselling_session WHERE status = 'COMPLETED';

SELECT student_id FROM v_student_risk_profile WHERE risk_index >= 50
EXCEPT
SELECT student_id FROM counselling_session WHERE status = 'COMPLETED';

SELECT dept_code, full_name, high_count, risk_index,
       RANK()       OVER (PARTITION BY dept_code ORDER BY risk_index DESC) AS dept_rank,
       ROW_NUMBER() OVER (ORDER BY risk_index DESC)                        AS overall_rank
FROM   v_student_risk_profile
WHERE  total_assessments > 0
ORDER  BY dept_code, dept_rank
LIMIT  25;

SELECT entry_date, total, high, avg_stress_score,
       ROUND(AVG(avg_stress_score) OVER (
             ORDER BY entry_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 3)
       AS rolling_7day
FROM   v_daily_trend
ORDER  BY entry_date DESC
LIMIT  20;

SELECT s.full_name, a.created_at, sl.level_name,
       LAG(sl.level_name) OVER (PARTITION BY a.student_id ORDER BY a.created_at)
           AS previous_level,
       a.predicted_level
       - LAG(a.predicted_level) OVER (PARTITION BY a.student_id ORDER BY a.created_at)
           AS change
FROM        assessment   a
INNER JOIN  student      s  ON a.student_id      = s.student_id
INNER JOIN  stress_level sl ON a.predicted_level = sl.level_code
ORDER  BY s.full_name, a.created_at
LIMIT  25;

SELECT full_name, dept_code, risk_index,
       NTILE(4) OVER (ORDER BY risk_index DESC) AS quartile
FROM   v_student_risk_profile
WHERE  total_assessments > 0
ORDER  BY risk_index DESC
LIMIT  20;

SELECT d.dept_code, t.theme_name, COUNT(*) AS entries,
       ROUND(COUNT(*) * 100.0
             / SUM(COUNT(*)) OVER (PARTITION BY d.dept_code), 1) AS pct_of_dept
FROM        assessment a
INNER JOIN  student    s ON a.student_id      = s.student_id
INNER JOIN  department d ON s.dept_id         = d.dept_id
INNER JOIN  theme      t ON a.predicted_theme = t.theme_id
GROUP  BY d.dept_code, t.theme_name
ORDER  BY d.dept_code, entries DESC
LIMIT  25;

WITH high_entries AS (
    SELECT a.student_id, COUNT(*) AS high_count
      FROM assessment a
     WHERE a.predicted_level = 2
     GROUP BY a.student_id
),
session_counts AS (
    SELECT student_id, COUNT(*) AS sessions
      FROM counselling_session
     GROUP BY student_id
)
SELECT s.full_name, d.dept_code,
       h.high_count,
       COALESCE(sc.sessions, 0)                  AS sessions,
       ROUND(h.high_count * 1.0
             / NULLIF(COALESCE(sc.sessions, 0), 0), 2) AS high_per_session
FROM        high_entries   h
INNER JOIN  student        s  ON h.student_id = s.student_id
INNER JOIN  department     d  ON s.dept_id    = d.dept_id
LEFT  JOIN  session_counts sc ON sc.student_id = s.student_id
ORDER  BY h.high_count DESC
LIMIT  15;

WITH RECURSIVE calendar(day) AS (
    SELECT DATE('now','localtime', '-29 days')
    UNION ALL
    SELECT DATE(day, '+1 day') FROM calendar WHERE day < DATE('now','localtime')
)
SELECT c.day,
       COUNT(a.assessment_id)                                 AS entries,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS high
FROM        calendar   c
LEFT  JOIN  assessment a ON DATE(a.created_at) = c.day
GROUP  BY c.day
ORDER  BY c.day;

SELECT UPPER(SUBSTR(full_name, 1, 1)) || LOWER(SUBSTR(full_name, 2)) AS name,
       LENGTH(full_name)                                             AS name_len,
       REPLACE(email, '@student.mindcare.edu', '')                   AS handle,
       SUBSTR(enrollment_no, 1, 5)                                   AS batch_prefix
FROM   student
LIMIT  10;

SELECT full_name, dob,
       CAST((JULIANDAY('now','localtime') - JULIANDAY(dob)) / 365.25 AS INTEGER) AS age,
       STRFTIME('%Y', dob)                                           AS birth_year,
       CASE CAST(STRFTIME('%w', dob) AS INTEGER)
            WHEN 0 THEN 'Sunday'  WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
            WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday'
            WHEN 5 THEN 'Friday'  ELSE 'Saturday' END                AS born_on
FROM   student
WHERE  dob IS NOT NULL
LIMIT  10;

SELECT CASE WHEN CAST(STRFTIME('%H', created_at) AS INTEGER) BETWEEN  0 AND  5
              THEN '00:00-05:59 (late night)'
            WHEN CAST(STRFTIME('%H', created_at) AS INTEGER) BETWEEN  6 AND 11
              THEN '06:00-11:59 (morning)'
            WHEN CAST(STRFTIME('%H', created_at) AS INTEGER) BETWEEN 12 AND 17
              THEN '12:00-17:59 (afternoon)'
            ELSE '18:00-23:59 (evening)' END AS time_band,
       COUNT(*)                              AS entries,
       ROUND(AVG(predicted_level), 3)        AS avg_stress,
       ROUND(100.0 * SUM(CASE WHEN predicted_level = 2 THEN 1 ELSE 0 END)
             / COUNT(*), 1)                  AS high_pct
FROM   assessment
GROUP  BY time_band
ORDER  BY avg_stress DESC;

SELECT priority,
       COUNT(*)                                                          AS resolved,
       ROUND(AVG(JULIANDAY(resolved_at) - JULIANDAY(raised_at)) * 24, 1) AS avg_hours,
       ROUND(MIN(JULIANDAY(resolved_at) - JULIANDAY(raised_at)) * 24, 1) AS fastest_hours,
       ROUND(MAX(JULIANDAY(resolved_at) - JULIANDAY(raised_at)) * 24, 1) AS slowest_hours
FROM   alert
WHERE  resolved_at IS NOT NULL
GROUP  BY priority
ORDER  BY avg_hours;

SELECT (SELECT COUNT(*) FROM assessment a
          LEFT JOIN student s ON a.student_id = s.student_id
         WHERE s.student_id IS NULL)                       AS orphan_assessments,
       (SELECT COUNT(*) FROM alert al
          LEFT JOIN assessment a ON al.assessment_id = a.assessment_id
         WHERE a.assessment_id IS NULL)                    AS orphan_alerts,
       (SELECT COUNT(*) FROM assessment_score sc
          LEFT JOIN assessment a ON sc.assessment_id = a.assessment_id
         WHERE a.assessment_id IS NULL)                    AS orphan_scores;

SELECT COUNT(*)                                   AS assessments_checked,
       SUM(CASE WHEN n <> 3 THEN 1 ELSE 0 END)    AS wrong_row_count,
       SUM(CASE WHEN ABS(s - 1.0) > 0.001
                THEN 1 ELSE 0 END)                AS probabilities_not_summing_to_one
FROM  (SELECT assessment_id, COUNT(*) AS n, SUM(probability) AS s
         FROM assessment_score
        GROUP BY assessment_id);

SELECT type, COUNT(*) AS objects
FROM   sqlite_master
WHERE  name NOT LIKE 'sqlite_%'
GROUP  BY type
ORDER  BY type;

EXPLAIN QUERY PLAN
SELECT * FROM assessment WHERE student_id = 5 ORDER BY created_at DESC;

SELECT i.code,
       COUNT(*)                                                   AS items,
       SUM(r.option_value)                                        AS naive_sum,
       SUM(CASE WHEN ii.reverse_scored = 1
                THEN i.option_max - r.option_value
                ELSE r.option_value END)                          AS correct_score,
       i.score_max
FROM        screening_response r
INNER JOIN  instrument_item    ii ON r.item_id        = ii.item_id
INNER JOIN  instrument         i  ON ii.instrument_id = i.instrument_id
WHERE       r.screening_id = (SELECT MIN(screening_id) FROM screening
                               WHERE status = 'COMPLETED')
GROUP  BY   i.instrument_id, i.code, i.option_max, i.score_max;

WITH manual AS (
    SELECT r.screening_id,
           ii.instrument_id,
           SUM(CASE WHEN ii.reverse_scored = 1
                    THEN i.option_max - r.option_value
                    ELSE r.option_value END) AS computed
      FROM screening_response r
      JOIN instrument_item    ii ON r.item_id        = ii.item_id
      JOIN instrument         i  ON ii.instrument_id = i.instrument_id
     GROUP BY r.screening_id, ii.instrument_id
)
SELECT COUNT(*)                                                        AS rows_checked,
       SUM(CASE WHEN m.computed <> ss.raw_score THEN 1 ELSE 0 END)     AS mismatches
FROM        manual          m
INNER JOIN  screening_score ss ON m.screening_id  = ss.screening_id
                              AND m.instrument_id = ss.instrument_id;

SELECT i.code,
       b.band_name,
       b.min_score || '-' || b.max_score                       AS score_range,
       COUNT(ss.screening_id)                                  AS students,
       ROUND(COUNT(ss.screening_id) * 100.0
             / SUM(COUNT(ss.screening_id)) OVER (PARTITION BY i.code), 1)
                                                               AS pct_of_instrument
FROM        instrument      i
INNER JOIN  severity_band   b  ON i.instrument_id = b.instrument_id
LEFT  JOIN  screening_score ss ON ss.band_id      = b.band_id
GROUP  BY   i.code, b.band_id, b.band_name, b.min_score, b.max_score, b.severity_rank
ORDER  BY   i.display_order, b.severity_rank;

SELECT instrument_code, item_no, question_text, reverse_scored, is_critical,
       times_answered, avg_raw, avg_pct_of_max
FROM   v_item_response_stats
WHERE  times_answered > 0
ORDER  BY avg_pct_of_max DESC
LIMIT  12;

SELECT sc.composite_band,
       SUM(CASE WHEN a.predicted_level = 0 THEN 1 ELSE 0 END) AS text_low,
       SUM(CASE WHEN a.predicted_level = 1 THEN 1 ELSE 0 END) AS text_moderate,
       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END) AS text_high,
       COUNT(*)                                               AS total,
       ROUND(AVG(sc.composite_score), 1)                      AS avg_composite
FROM        screening  sc
INNER JOIN  assessment a ON sc.assessment_id = a.assessment_id
WHERE       sc.status = 'COMPLETED'
GROUP  BY   sc.composite_band
ORDER  BY   avg_composite;

SELECT ROUND(AVG(phq.raw_score), 2)  AS avg_phq9,
       ROUND(AVG(gad.raw_score), 2)  AS avg_gad7,
       COUNT(*)                      AS screenings,
       SUM(CASE WHEN phq.raw_score >= 10 AND gad.raw_score >= 10 THEN 1 ELSE 0 END)
                                     AS both_moderate_or_worse,
       SUM(CASE WHEN phq.raw_score >= 10 AND gad.raw_score <  10 THEN 1 ELSE 0 END)
                                     AS depression_only,
       SUM(CASE WHEN phq.raw_score <  10 AND gad.raw_score >= 10 THEN 1 ELSE 0 END)
                                     AS anxiety_only
FROM        screening_score phq
INNER JOIN  screening_score gad ON phq.screening_id = gad.screening_id
INNER JOIN  instrument      ip  ON phq.instrument_id = ip.instrument_id
INNER JOIN  instrument      ig  ON gad.instrument_id = ig.instrument_id
WHERE       ip.code = 'PHQ-9' AND ig.code = 'GAD-7';

SELECT s.enrollment_no, s.full_name, d.dept_code,
       sc.completed_at, sc.composite_score, sc.composite_band,
       r.option_value                       AS critical_answer,
       o.option_label,
       al.priority                          AS alert_priority,
       al.status                            AS alert_status
FROM        screening_response r
INNER JOIN  instrument_item    ii ON r.item_id        = ii.item_id
INNER JOIN  instrument         i  ON ii.instrument_id = i.instrument_id
INNER JOIN  response_option    o  ON o.instrument_id  = i.instrument_id
                                 AND o.option_value   = r.option_value
INNER JOIN  screening          sc ON r.screening_id   = sc.screening_id
INNER JOIN  student            s  ON sc.student_id    = s.student_id
INNER JOIN  department         d  ON s.dept_id        = d.dept_id
LEFT  JOIN  alert              al ON al.assessment_id = sc.assessment_id
WHERE       ii.is_critical = 1
  AND       r.option_value > 0
ORDER  BY   r.option_value DESC, sc.composite_score DESC;

WITH ordered AS (
    SELECT student_id, screening_id, completed_at, composite_score,
           ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY completed_at)      AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY completed_at DESC) AS rn_last,
           COUNT(*)     OVER (PARTITION BY student_id)                            AS taken
      FROM screening
     WHERE status = 'COMPLETED'
)
SELECT s.full_name, d.dept_code, f.taken AS screenings_taken,
       ROUND(f.composite_score, 1)                    AS first_score,
       ROUND(l.composite_score, 1)                    AS latest_score,
       ROUND(l.composite_score - f.composite_score, 1) AS change,
       CASE WHEN l.composite_score - f.composite_score >  5 THEN 'worse'
            WHEN l.composite_score - f.composite_score < -5 THEN 'better'
            ELSE 'stable' END                          AS direction
FROM        ordered    f
INNER JOIN  ordered    l ON f.student_id = l.student_id
INNER JOIN  student    s ON f.student_id = s.student_id
INNER JOIN  department d ON s.dept_id    = d.dept_id
WHERE       f.rn_first = 1 AND l.rn_last = 1 AND f.taken > 1
ORDER  BY   change DESC
LIMIT  20;

SELECT d.dept_code,
       COUNT(sc.screening_id)                  AS screenings,
       ROUND(AVG(sc.composite_score), 1)       AS avg_composite,
       SUM(CASE WHEN sc.composite_band = 'High' THEN 1 ELSE 0 END) AS high_band,
       ROUND(AVG(CASE WHEN i.code = 'PHQ-9' THEN ss.raw_score END), 1) AS avg_phq9,
       ROUND(AVG(CASE WHEN i.code = 'GAD-7' THEN ss.raw_score END), 1) AS avg_gad7,
       ROUND(AVG(CASE WHEN i.code = 'PSS-10' THEN ss.raw_score END), 1) AS avg_pss10
FROM        screening       sc
INNER JOIN  student         s  ON sc.student_id    = s.student_id
INNER JOIN  department      d  ON s.dept_id        = d.dept_id
LEFT  JOIN  screening_score ss ON sc.screening_id  = ss.screening_id
LEFT  JOIN  instrument      i  ON ss.instrument_id = i.instrument_id
WHERE       sc.status = 'COMPLETED'
GROUP  BY   d.dept_code
ORDER  BY   avg_composite DESC;

SELECT CASE WHEN w.sleep_hours < 6 THEN 'under 6h'
            WHEN w.sleep_hours < 7 THEN '6-7h'
            WHEN w.sleep_hours < 8 THEN '7-8h'
            ELSE '8h or more' END        AS sleep_band,
       COUNT(*)                          AS screenings,
       ROUND(AVG(ss.raw_score), 2)       AS avg_phq9,
       ROUND(AVG(sc.composite_score), 1) AS avg_composite
FROM        screening       sc
INNER JOIN  screening_score ss ON sc.screening_id  = ss.screening_id
INNER JOIN  instrument      i  ON ss.instrument_id = i.instrument_id
INNER JOIN  wellness_log    w  ON w.student_id     = sc.student_id
                              AND w.log_date       = DATE(sc.completed_at)
WHERE       i.code = 'PHQ-9' AND sc.status = 'COMPLETED'
  AND       w.sleep_hours IS NOT NULL
GROUP  BY   sleep_band
ORDER  BY   avg_phq9 DESC;

SELECT 'instrument'      AS table_name, COUNT(*) AS rows_per_instrument FROM instrument
UNION ALL SELECT 'instrument_item', COUNT(*) FROM instrument_item
UNION ALL SELECT 'response_option', COUNT(*) FROM response_option
UNION ALL SELECT 'severity_band',   COUNT(*) FROM severity_band;
