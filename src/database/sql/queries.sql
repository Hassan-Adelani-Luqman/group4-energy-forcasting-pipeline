-- Group 4 — Energy Forecasting Pipeline
-- Task 2 demonstration queries for the MySQL database.
-- Run against a database loaded with:  python -m src.database.sql.load_mysql
-- Each query below is self-contained; run them one at a time.

-- ==========================================================================
-- Q1 (required: LATEST RECORD)
-- Most recent reading for each region. A derived table finds each region's
-- max timestamp (two rows, resolved from the (region_id, reading_ts) index),
-- then joins back to pull that row's measures.
-- ==========================================================================
SELECT  r.region_code,
        er.reading_ts,
        er.mw,
        er.split
FROM    energy_readings er
JOIN    regions r ON r.region_id = er.region_id
JOIN    (
            SELECT region_id, MAX(reading_ts) AS max_ts
            FROM   energy_readings
            GROUP BY region_id
        ) latest
       ON latest.region_id = er.region_id
      AND latest.max_ts   = er.reading_ts
ORDER BY r.region_code;

-- ==========================================================================
-- Q2 (required: RECORDS BY DATE RANGE)
-- All PJME readings for the first week of July 2015, oldest first.
-- ==========================================================================
SELECT  er.reading_ts,
        er.mw,
        er.lag_24h,
        er.rolling_mean_24h
FROM    energy_readings er
JOIN    regions r ON r.region_id = er.region_id
WHERE   r.region_code = 'PJME'
  AND   er.reading_ts >= '2015-07-01 00:00:00'
  AND   er.reading_ts <  '2015-07-08 00:00:00'
ORDER BY er.reading_ts;

-- ==========================================================================
-- Q3 (analytical: JOIN + GROUP BY)
-- Average load by day-of-week for each region, joining the fact table to
-- calendar_features. Answers "which weekdays carry the highest demand?"
-- ==========================================================================
SELECT  r.region_code,
        cf.day_of_week,
        CASE cf.day_of_week
            WHEN 0 THEN 'Mon' WHEN 1 THEN 'Tue' WHEN 2 THEN 'Wed'
            WHEN 3 THEN 'Thu' WHEN 4 THEN 'Fri' WHEN 5 THEN 'Sat'
            WHEN 6 THEN 'Sun' END                       AS dow_label,
        ROUND(AVG(er.mw), 1)                            AS avg_mw,
        COUNT(*)                                        AS n_hours
FROM    energy_readings er
JOIN    calendar_features cf ON cf.reading_ts = er.reading_ts
JOIN    regions r            ON r.region_id   = er.region_id
GROUP BY r.region_code, cf.day_of_week
ORDER BY r.region_code, cf.day_of_week;

-- ==========================================================================
-- Q4 (analytical: WINDOW FUNCTION — 7-day rolling average)
-- Daily mean load for PJME with a trailing 7-day moving average computed via
-- a window function. Demonstrates a rolling window directly in SQL (distinct
-- from the precomputed rolling_mean_7d column carried from Phase 1).
-- ==========================================================================
WITH daily AS (
    SELECT  DATE(er.reading_ts)      AS reading_date,
            AVG(er.mw)               AS daily_avg_mw
    FROM    energy_readings er
    JOIN    regions r ON r.region_id = er.region_id
    WHERE   r.region_code = 'PJME'
    GROUP BY DATE(er.reading_ts)
)
SELECT  reading_date,
        ROUND(daily_avg_mw, 1)                                   AS daily_avg_mw,
        ROUND(AVG(daily_avg_mw) OVER (
                  ORDER BY reading_date
                  ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1)  AS rolling_7d_avg_mw
FROM    daily
ORDER BY reading_date
LIMIT 30;

-- ==========================================================================
-- Q5 (analytical: peak hour per region)
-- The single highest-demand hour on record for each region.
-- ==========================================================================
SELECT  r.region_code,
        er.reading_ts   AS peak_ts,
        er.mw           AS peak_mw
FROM    energy_readings er
JOIN    regions r ON r.region_id = er.region_id
WHERE   (er.region_id, er.mw) IN (
            SELECT region_id, MAX(mw)
            FROM   energy_readings
            GROUP BY region_id
        )
ORDER BY r.region_code;
