DROP TRIGGER IF EXISTS trg_alert_on_high_stress;
DROP TRIGGER IF EXISTS trg_escalate_repeated_high;
DROP TRIGGER IF EXISTS trg_alert_acknowledge_time;
DROP TRIGGER IF EXISTS trg_alert_resolve_time;
DROP TRIGGER IF EXISTS trg_session_completed_resolves_alert;
DROP TRIGGER IF EXISTS trg_prevent_double_booking;
DROP TRIGGER IF EXISTS trg_single_active_model;

CREATE TRIGGER trg_alert_on_high_stress
AFTER INSERT ON assessment
FOR EACH ROW
WHEN NEW.predicted_level = 2
BEGIN
    INSERT INTO alert (assessment_id, alert_type, priority, status, raised_at, assigned_to)
    VALUES (
        NEW.assessment_id,
        'HIGH_STRESS',
        CASE WHEN NEW.confidence >= 0.90 THEN 'HIGH' ELSE 'MEDIUM' END,
        'OPEN',
        NEW.created_at,
        (SELECT c.counsellor_id
           FROM counsellor c
          WHERE c.is_active = 1
          ORDER BY (SELECT COUNT(*) FROM alert al
                     WHERE al.assigned_to = c.counsellor_id
                       AND al.status = 'OPEN') ASC,
                   c.counsellor_id ASC
          LIMIT 1)
    );
END;

CREATE TRIGGER trg_escalate_repeated_high
AFTER INSERT ON alert
FOR EACH ROW
WHEN (
    SELECT COUNT(*)
      FROM assessment a
     WHERE a.student_id = (SELECT student_id FROM assessment
                            WHERE assessment_id = NEW.assessment_id)
       AND a.predicted_level = 2
       AND a.created_at >= DATETIME((SELECT created_at FROM assessment
                                      WHERE assessment_id = NEW.assessment_id), '-7 days')
       AND a.created_at <= (SELECT created_at FROM assessment
                             WHERE assessment_id = NEW.assessment_id)
) >= 3
BEGIN
    UPDATE alert
       SET alert_type = 'REPEATED_HIGH',
           priority   = 'CRITICAL',
           remarks    = 'Auto-escalated: 3 or more high-stress entries in 7 days.'
     WHERE alert_id = NEW.alert_id;
END;

CREATE TRIGGER trg_alert_acknowledge_time
AFTER UPDATE OF status ON alert
FOR EACH ROW
WHEN NEW.status = 'ACKNOWLEDGED' AND OLD.status = 'OPEN'
BEGIN
    UPDATE alert SET acknowledged_at = datetime('now','localtime') WHERE alert_id = NEW.alert_id;
END;

CREATE TRIGGER trg_alert_resolve_time
AFTER UPDATE OF status ON alert
FOR EACH ROW
WHEN NEW.status IN ('RESOLVED','DISMISSED') AND NEW.resolved_at IS NULL
BEGIN
    UPDATE alert SET resolved_at = datetime('now','localtime') WHERE alert_id = NEW.alert_id;
END;

CREATE TRIGGER trg_session_completed_resolves_alert
AFTER UPDATE OF status ON counselling_session
FOR EACH ROW
WHEN NEW.status = 'COMPLETED' AND NEW.alert_id IS NOT NULL
BEGIN
    UPDATE alert
       SET status  = 'RESOLVED',
           remarks = 'Closed by counselling session #' || NEW.session_id
     WHERE alert_id = NEW.alert_id
       AND status  <> 'RESOLVED';
END;

CREATE TRIGGER trg_prevent_double_booking
BEFORE INSERT ON counselling_session
FOR EACH ROW
WHEN EXISTS (
    SELECT 1 FROM counselling_session cs
     WHERE cs.counsellor_id = NEW.counsellor_id
       AND cs.scheduled_at  = NEW.scheduled_at
       AND cs.status        = 'SCHEDULED'
)
BEGIN
    SELECT RAISE(ABORT, 'Counsellor already has a session booked at this time slot.');
END;

CREATE TRIGGER trg_single_active_model
AFTER UPDATE OF is_active ON ml_model
FOR EACH ROW
WHEN NEW.is_active = 1
BEGIN
    UPDATE ml_model SET is_active = 0
     WHERE model_id <> NEW.model_id AND is_active = 1;
END;
