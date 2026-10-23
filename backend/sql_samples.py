SAMPLE_QUERIES = [
    ("Top 10 students by weighted risk index",
     "SELECT enrollment_no, full_name, dept_code, total_assessments,\n"
     "       high_count, risk_index, latest_level\n"
     "FROM   v_student_risk_profile\n"
     "WHERE  total_assessments > 0\n"
     "ORDER  BY risk_index DESC\n"
     "LIMIT  10;"),
    ("Departments above the campus-wide average stress score (subquery)",
     "SELECT dept_code, dept_name, avg_stress_score, high_stress_pct\n"
     "FROM   v_dept_stress_summary\n"
     "WHERE  avg_stress_score > (SELECT AVG(predicted_level) FROM assessment)\n"
     "ORDER  BY avg_stress_score DESC;"),
    ("Theme x severity cross-tab with HAVING",
     "SELECT t.theme_name,\n"
     "       COUNT(*)                                                AS entries,\n"
     "       SUM(CASE WHEN a.predicted_level = 2 THEN 1 ELSE 0 END)  AS high,\n"
     "       ROUND(AVG(a.confidence) * 100, 1)                       AS avg_conf\n"
     "FROM   assessment a\n"
     "JOIN   theme t ON a.predicted_theme = t.theme_id\n"
     "GROUP  BY t.theme_name\n"
     "HAVING COUNT(*) >= 20\n"
     "ORDER  BY high DESC;"),
    ("Running 7-day average stress (window function)",
     "SELECT entry_date, total, high,\n"
     "       ROUND(AVG(avg_stress_score) OVER (\n"
     "           ORDER BY entry_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW\n"
     "       ), 3) AS rolling_7day\n"
     "FROM   v_daily_trend\n"
     "ORDER  BY entry_date DESC\n"
     "LIMIT  20;"),
    ("Rank students within each department (window + partition)",
     "SELECT dept_code, full_name, high_count, risk_index,\n"
     "       RANK() OVER (PARTITION BY dept_code ORDER BY risk_index DESC) AS dept_rank\n"
     "FROM   v_student_risk_profile\n"
     "WHERE  total_assessments > 0\n"
     "ORDER  BY dept_code, dept_rank\n"
     "LIMIT  30;"),
    ("Alert resolution time by priority (date arithmetic)",
     "SELECT priority,\n"
     "       COUNT(*)                                                       AS resolved,\n"
     "       ROUND(AVG(JULIANDAY(resolved_at) - JULIANDAY(raised_at)) * 24, 1)\n"
     "                                                                      AS avg_hours\n"
     "FROM   alert\n"
     "WHERE  resolved_at IS NOT NULL\n"
     "GROUP  BY priority\n"
     "ORDER  BY avg_hours;"),
    ("Students with a high entry but no counselling session yet (NOT EXISTS)",
     "SELECT DISTINCT s.enrollment_no, s.full_name, d.dept_code\n"
     "FROM   student s\n"
     "JOIN   department d  ON s.dept_id = d.dept_id\n"
     "JOIN   assessment a  ON s.student_id = a.student_id\n"
     "WHERE  a.predicted_level = 2\n"
     "  AND  NOT EXISTS (SELECT 1 FROM counselling_session cs\n"
     "                   WHERE cs.student_id = s.student_id)\n"
     "ORDER  BY s.full_name;"),
    ("Sleep vs. same-day stress (joining two fact tables) ",
     "SELECT CASE WHEN sleep_hours < 6 THEN 'under 6h'\n"
     "            WHEN sleep_hours < 7 THEN '6-7h'\n"
     "            WHEN sleep_hours < 8 THEN '7-8h'\n"
     "            ELSE '8h or more' END                AS sleep_band,\n"
     "       COUNT(*)                                  AS logged_days,\n"
     "       ROUND(AVG(mood_rating), 2)                AS avg_mood,\n"
     "       ROUND(AVG(avg_stress_that_day), 3)        AS avg_stress\n"
     "FROM   v_wellness_vs_stress\n"
     "WHERE  avg_stress_that_day IS NOT NULL\n"
     "GROUP  BY sleep_band\n"
     "ORDER  BY sleep_band;"),
    ("Model comparison from the registry",
     "SELECT algorithm, ROUND(accuracy*100, 2) AS accuracy_pct,\n"
     "       ROUND(f1_macro*100, 2) AS f1_pct, feature_count, is_active\n"
     "FROM   ml_model\n"
     "ORDER  BY f1_macro DESC;"),
    ("Corpus class balance by theme category (CTE)",
     "WITH labelled AS (\n"
     "    SELECT sl.level_name, t.category\n"
     "    FROM   training_corpus tc\n"
     "    JOIN   stress_level sl ON tc.label = sl.level_code\n"
     "    JOIN   theme t         ON tc.theme_id = t.theme_id\n"
     ")\n"
     "SELECT category, level_name, COUNT(*) AS n\n"
     "FROM   labelled\n"
     "GROUP  BY category, level_name\n"
     "ORDER  BY category, level_name;"),
    ("Screening: verify trigger T8's arithmetic against a hand calculation",
     "WITH manual AS (\n"
     "    SELECT r.screening_id, ii.instrument_id,\n"
     "           SUM(CASE WHEN ii.reverse_scored = 1\n"
     "                    THEN i.option_max - r.option_value\n"
     "                    ELSE r.option_value END) AS computed\n"
     "    FROM   screening_response r\n"
     "    JOIN   instrument_item ii ON r.item_id = ii.item_id\n"
     "    JOIN   instrument i ON ii.instrument_id = i.instrument_id\n"
     "    GROUP  BY r.screening_id, ii.instrument_id\n"
     ")\n"
     "SELECT COUNT(*) AS rows_checked,\n"
     "       SUM(CASE WHEN m.computed <> ss.raw_score THEN 1 ELSE 0 END) AS mismatches\n"
     "FROM   manual m\n"
     "JOIN   screening_score ss ON m.screening_id = ss.screening_id\n"
     "                        AND m.instrument_id = ss.instrument_id;"),
    ("Screening: cohort spread across severity bands",
     "SELECT i.code, b.band_name,\n"
     "       b.min_score || '-' || b.max_score AS score_range,\n"
     "       COUNT(ss.screening_id)            AS students,\n"
     "       ROUND(COUNT(ss.screening_id) * 100.0\n"
     "             / SUM(COUNT(ss.screening_id)) OVER (PARTITION BY i.code), 1) AS pct\n"
     "FROM   instrument i\n"
     "JOIN   severity_band b ON i.instrument_id = b.instrument_id\n"
     "LEFT   JOIN screening_score ss ON ss.band_id = b.band_id\n"
     "GROUP  BY i.code, b.band_id\n"
     "ORDER  BY i.display_order, b.severity_rank;"),
    ("Screening: students who flagged the critical self-harm item",
     "SELECT s.enrollment_no, s.full_name, d.dept_code, sc.completed_at,\n"
     "       sc.composite_score, sc.composite_band,\n"
     "       o.option_label AS answered, al.priority, al.status\n"
     "FROM   screening_response r\n"
     "JOIN   instrument_item ii ON r.item_id = ii.item_id\n"
     "JOIN   instrument i       ON ii.instrument_id = i.instrument_id\n"
     "JOIN   response_option o  ON o.instrument_id = i.instrument_id\n"
     "                        AND o.option_value  = r.option_value\n"
     "JOIN   screening sc       ON r.screening_id = sc.screening_id\n"
     "JOIN   student s          ON sc.student_id  = s.student_id\n"
     "JOIN   department d       ON s.dept_id      = d.dept_id\n"
     "LEFT   JOIN alert al      ON al.assessment_id = sc.assessment_id\n"
     "WHERE  ii.is_critical = 1 AND r.option_value > 0\n"
     "ORDER  BY r.option_value DESC;"),
    ("Screening: hardest individual questions across the cohort",
     "SELECT instrument_code, item_no, question_text, reverse_scored,\n"
     "       times_answered, avg_raw, avg_pct_of_max\n"
     "FROM   v_item_response_stats\n"
     "WHERE  times_answered > 0\n"
     "ORDER  BY avg_pct_of_max DESC\n"
     "LIMIT  12;"),
    ("EXPLAIN the query plan for an indexed lookup",
     "EXPLAIN QUERY PLAN\n"
     "SELECT * FROM assessment\n"
     "WHERE  student_id = 5\n"
     "ORDER  BY created_at DESC;"),
]
