PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS support_tip;
DROP TABLE IF EXISTS helpline;

CREATE TABLE helpline (
    helpline_id   INTEGER      PRIMARY KEY AUTOINCREMENT,
    name          VARCHAR(80)  NOT NULL,
    phone         VARCHAR(60)  NOT NULL,
    dial          VARCHAR(20)  NOT NULL,
    region        VARCHAR(20)  NOT NULL,
    hours         VARCHAR(60)  NOT NULL,
    service       VARCHAR(160) NOT NULL,
    is_crisis     INTEGER      NOT NULL DEFAULT 0,
    display_order INTEGER      NOT NULL,
    is_active     INTEGER      NOT NULL DEFAULT 1,
    CONSTRAINT uq_helpline    UNIQUE (name, dial),
    CONSTRAINT chk_hl_region  CHECK (region IN ('Emergency','National','Delhi NCR','Noida')),
    CONSTRAINT chk_hl_crisis  CHECK (is_crisis IN (0,1)),
    CONSTRAINT chk_hl_active  CHECK (is_active IN (0,1))
);

CREATE TABLE support_tip (
    tip_id        INTEGER      PRIMARY KEY AUTOINCREMENT,
    level_code    INTEGER      NOT NULL,
    tip_type      VARCHAR(10)  NOT NULL,
    title         VARCHAR(80)  NOT NULL,
    body          VARCHAR(400) NOT NULL,
    display_order INTEGER      NOT NULL,
    CONSTRAINT fk_tip_level FOREIGN KEY (level_code)
        REFERENCES stress_level (level_code) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_tip_type CHECK (tip_type IN ('COPING','ADVICE')),
    CONSTRAINT uq_tip UNIQUE (level_code, tip_type, title)
);

CREATE INDEX idx_tip_level       ON support_tip (level_code, tip_type, display_order);
CREATE INDEX idx_helpline_region ON helpline (region, display_order);
