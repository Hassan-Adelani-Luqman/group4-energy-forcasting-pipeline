-- Group 4 — Energy Forecasting Pipeline
-- Relational schema for PJM hourly energy consumption (MySQL 8)
--
-- Design notes
-- ------------
-- The processed CSV (data/processed/{region}_hourly_processed.csv) is a single wide
-- table. We normalise it into four tables so the schema is in 3NF and the calendar
-- attributes (which depend only on the timestamp, not on the region or the reading)
-- are not repeated on every row:
--
--   regions            reference table, one row per PJM sub-region (PJME, AEP, ...)
--   calendar_features  one row per distinct hourly timestamp; hour/day-of-week/
--                      month/weekend/holiday flags are a pure function of the ts
--   energy_readings    the fact table: actual MW plus lag & rolling features,
--                      FK to region and to the calendar timestamp
--   predictions        model forecasts written back by the Phase 4 forecast script
--
-- Apply with:  mysql -h 127.0.0.1 -u root -p energy_pipeline < schema.sql

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS predictions;
DROP TABLE IF EXISTS energy_readings;
DROP TABLE IF EXISTS calendar_features;
DROP TABLE IF EXISTS regions;

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------------------------------------------------------
-- 1. regions — reference data, one row per PJM sub-region
-- --------------------------------------------------------------------------
CREATE TABLE regions (
    region_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_code  VARCHAR(16)  NOT NULL,          -- e.g. 'PJME', 'AEP'
    region_name  VARCHAR(128) NOT NULL,
    description  VARCHAR(255) NULL,
    PRIMARY KEY (region_id),
    UNIQUE KEY uq_regions_code (region_code)
) ENGINE = InnoDB;

-- --------------------------------------------------------------------------
-- 2. calendar_features — one row per distinct hourly timestamp
--    (calendar attributes are shared across regions for the same ts)
-- --------------------------------------------------------------------------
CREATE TABLE calendar_features (
    reading_ts   DATETIME     NOT NULL,
    hour         TINYINT      NOT NULL,          -- 0-23
    day_of_week  TINYINT      NOT NULL,          -- 0=Mon .. 6=Sun
    month        TINYINT      NOT NULL,          -- 1-12
    is_weekend   TINYINT(1)   NOT NULL DEFAULT 0,
    is_holiday   TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (reading_ts),
    KEY idx_calendar_dow (day_of_week),
    KEY idx_calendar_month (month)
) ENGINE = InnoDB;

-- --------------------------------------------------------------------------
-- 3. energy_readings — fact table: one row per (region, hour)
-- --------------------------------------------------------------------------
CREATE TABLE energy_readings (
    reading_id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id        INT UNSIGNED    NOT NULL,
    reading_ts       DATETIME        NOT NULL,
    mw               DECIMAL(10, 2)  NOT NULL,       -- observed load in megawatts
    lag_1h           DECIMAL(10, 2)  NULL,
    lag_24h          DECIMAL(10, 2)  NULL,
    lag_168h         DECIMAL(10, 2)  NULL,
    rolling_mean_24h DECIMAL(12, 4)  NULL,
    rolling_mean_7d  DECIMAL(12, 4)  NULL,
    rolling_std_24h  DECIMAL(12, 4)  NULL,
    split            ENUM('train', 'val', 'test') NOT NULL,
    PRIMARY KEY (reading_id),
    UNIQUE KEY uq_reading_region_ts (region_id, reading_ts),
    KEY idx_readings_ts (reading_ts),
    KEY idx_readings_split (split),
    CONSTRAINT fk_readings_region
        FOREIGN KEY (region_id) REFERENCES regions (region_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_readings_calendar
        FOREIGN KEY (reading_ts) REFERENCES calendar_features (reading_ts)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB;

-- --------------------------------------------------------------------------
-- 4. predictions — model forecasts (written back by the forecast script)
-- --------------------------------------------------------------------------
CREATE TABLE predictions (
    prediction_id  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id      INT UNSIGNED    NOT NULL,
    target_ts      DATETIME        NOT NULL,       -- timestamp being forecast
    predicted_mw   DECIMAL(10, 2)  NOT NULL,
    model_name     VARCHAR(64)     NOT NULL,       -- e.g. 'xgboost'
    generated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (prediction_id),
    UNIQUE KEY uq_pred_region_target_model (region_id, target_ts, model_name),
    KEY idx_pred_target_ts (target_ts),
    CONSTRAINT fk_pred_region
        FOREIGN KEY (region_id) REFERENCES regions (region_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;
