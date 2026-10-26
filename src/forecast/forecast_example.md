# Phase 4 — Captured Forecast Run

Real terminal output from `python -m src.forecast.run_forecast`, run on 2026-10-26 against the live API
(`uvicorn src.api.main:app`) and live MySQL/MongoDB containers loaded with Task 2's data. The `date | INFO |` log
prefix is trimmed for readability; warnings keep their `WARNING` label. Reproduce with:

```bash
docker-compose up -d
python -m src.database.sql.load_mysql        # if not already loaded
python -m src.database.mongodb.setup         # if not already loaded
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &
python -m src.forecast.run_forecast
```

The API address defaults to `API_BASE_URL` from `.env` (falling back to `http://localhost:8000`); override it with
`--api-base`.

## Output — first run (both regions)

```
=== Forecasting next hour for PJME ===
Fetching PJME window from http://localhost:8000/api/sql/readings/range (2018-07-20 01:00:00 -> 2018-08-03 00:00:00)
Fetched 336 rows, 2018-07-20 01:00:00 -> 2018-08-03 00:00:00
--- BEFORE: last 3 hours of input for PJME ---
reading_ts
2018-08-02 22:00:00    41552.0
2018-08-02 23:00:00    38500.0
2018-08-03 00:00:00    35486.0
--- AFTER: PJME forecast for 2018-08-03 01:00:00 -> 32755.4 MW ---
SQL prediction stored: {'region_id': 1, 'target_ts': '2018-08-03T01:00:00', 'predicted_mw': 32755.44,
  'model_name': 'xgboost', 'prediction_id': 7, 'generated_at': '2026-10-26T12:58:59'}
Mongo prediction stored: {'region_code': 'PJME', 'target_ts': '2018-08-03T01:00:00', 'predicted_mw': 32755.443359375,
  'model_name': 'xgboost', 'generated_at': '2026-10-26T12:58:59.812266'}

=== Forecasting next hour for AEP ===
Fetching AEP window from http://localhost:8000/api/sql/readings/range (2018-07-20 01:00:00 -> 2018-08-03 00:00:00)
Fetched 336 rows, 2018-07-20 01:00:00 -> 2018-08-03 00:00:00
--- BEFORE: last 3 hours of input for AEP ---
reading_ts
2018-08-02 22:00:00    17001.0
2018-08-02 23:00:00    15964.0
2018-08-03 00:00:00    14809.0
--- AFTER: AEP forecast for 2018-08-03 01:00:00 -> 13660.5 MW ---
SQL prediction stored: {'region_id': 2, 'target_ts': '2018-08-03T01:00:00', 'predicted_mw': 13660.47,
  'model_name': 'xgboost', 'prediction_id': 8, 'generated_at': '2026-10-26T12:59:00'}
Mongo prediction stored: {'region_code': 'AEP', 'target_ts': '2018-08-03T01:00:00', 'predicted_mw': 13660.466796875,
  'model_name': 'xgboost', 'generated_at': '2026-10-26T12:59:00.238613'}
```

## Output — re-run (`--region PJME`)

Running the script again for the same frozen-dataset target hour:

```
--- AFTER: PJME forecast for 2018-08-03 01:00:00 -> 32755.4 MW ---
WARNING | SQL write for 2018-08-03T01:00:00 skipped: already predicted by a previous run (409 Conflict).
WARNING | Mongo write for 2018-08-03T01:00:00 skipped: already predicted by a previous run (409 Conflict).
```

## Notes for the report

- **First run** is the end-to-end loop: for each region the script fetched a 14-day window through the API,
  built features with Task 1's `build_feature_set`, predicted with the Task 1 XGBoost model, and wrote the result
  back to both `predictions` stores through Task 3's endpoints.
- **Re-run** shows the duplicate handling: both stores have a unique `(region, target_ts, model)` key, so the API
  answers the second insert with `409 Conflict` and the script logs a warning and carries on rather than crashing.
  Any other error status is logged as an error. The re-run also reproduces the same forecast (32,755.4 MW),
  confirming the pipeline is deterministic.
- Verified directly against the database afterward:

  ```sql
  SELECT * FROM predictions ORDER BY prediction_id;
  -- 1 | 1 (PJME) | 2018-08-03 02:00:00 | 33150.00 | xgboost | 2026-10-25 09:56:08   <- Task 3 API example
  -- 7 | 1 (PJME) | 2018-08-03 01:00:00 | 32755.44 | xgboost | 2026-10-26 12:58:59   <- this run
  -- 8 | 2 (AEP)  | 2018-08-03 01:00:00 | 13660.47 | xgboost | 2026-10-26 12:59:00   <- this run
  ```

  (The gap in `prediction_id` is expected: MySQL still consumes an auto-increment value when a duplicate insert is
  rejected, and earlier test runs were rejected that way.) The MongoDB `predictions` collection holds the same three
  forecasts.
- The forecasts (PJME 32,755.4 MW, AEP 13,660.5 MW) continue the overnight decline in each region's last few hours,
  which is the expected sanity check for a next-hour forecast.
