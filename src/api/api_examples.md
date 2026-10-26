# Phase 3 API Examples

Real request/response pairs captured by actually running the API against the live, fully-loaded MySQL and MongoDB
containers from Task 2 (`docker-compose up -d`, `python -m src.database.sql.load_mysql`,
`python -m src.database.mongodb.setup`, then `uvicorn src.api.main:app`). Every value below is copied verbatim from
an actual response, not hand-written.

## MySQL Endpoints

### 1. Get latest reading (required) — `GET /api/sql/readings/latest?region_id=1`

**Response (200 OK):**
```json
{
  "region_id": 1,
  "reading_ts": "2018-08-03T00:00:00",
  "mw": 35486.0,
  "lag_1h": 38500.0,
  "lag_24h": 37158.0,
  "lag_168h": 35742.0,
  "rolling_mean_24h": 39593.0417,
  "rolling_mean_7d": 35881.5,
  "rolling_std_24h": 6225.263,
  "split": "test",
  "reading_id": 145224
}
```

### 2. Get records by date range (required) — `GET /api/sql/readings/range?region_id=1&start_date=2018-08-02T22:00:00&end_date=2018-08-03T00:00:00`

**Response (200 OK):** 3 rows

```json
[
  {"region_id": 1, "reading_ts": "2018-08-02T22:00:00", "mw": 41552.0, "reading_id": 145222, "...": "..."},
  {"region_id": 1, "reading_ts": "2018-08-02T23:00:00", "mw": 38500.0, "reading_id": 145223, "...": "..."},
  {"region_id": 1, "reading_ts": "2018-08-03T00:00:00", "mw": 35486.0, "reading_id": 145224, "...": "..."}
]
```

### 3. Get one reading — `GET /api/sql/readings/145224`

**Response (200 OK):** identical to the latest-record response above (`reading_id` 145224 is in fact PJME's latest row).

### 4. Create — `POST /api/sql/readings`

**Request:**
```json
{
  "region_id": 2,
  "reading_ts": "2002-01-15T12:00:00",
  "mw": 11111.0,
  "lag_1h": null, "lag_24h": null, "lag_168h": null,
  "rolling_mean_24h": null, "rolling_mean_7d": null, "rolling_std_24h": null,
  "split": "train"
}
```

**Response (200 OK):**
```json
{
  "region_id": 2, "reading_ts": "2002-01-15T12:00:00", "mw": 11111.0,
  "lag_1h": null, "lag_24h": null, "lag_168h": null,
  "rolling_mean_24h": null, "rolling_mean_7d": null, "rolling_std_24h": null,
  "split": "train", "reading_id": 266353
}
```

Note: `reading_ts` must already exist in `calendar_features` (the FK constraint enforces this) — the region/timestamp
combination above was chosen because AEP (region 2) has no reading yet for that early-2002 timestamp (AEP's own data
only starts in Oct 2004), so this is a genuinely new row, not an overwrite.

### 5. Update — `PUT /api/sql/readings/266353`

**Request:** `{"mw": 22222.0}`

**Response (200 OK):** same object as above with `"mw": 22222.0`.

### 6. Delete — `DELETE /api/sql/readings/266353`

**Response (200 OK):** `{"message": "Reading deleted"}` — a follow-up `GET /api/sql/readings/266353` correctly returns `404 {"detail": "Reading not found"}`.

### 7. Create prediction — `POST /api/sql/predictions`

**Request:**
```json
{
  "region_id": 1,
  "target_ts": "2018-08-03T02:00:00",
  "predicted_mw": 33150.0,
  "model_name": "xgboost"
}
```

**Response (200 OK):**
```json
{
  "region_id": 1,
  "target_ts": "2018-08-03T02:00:00",
  "predicted_mw": 33150.0,
  "model_name": "xgboost",
  "prediction_id": 1,
  "generated_at": "2026-10-25T09:56:08"
}
```

## MongoDB Endpoints

### 1. Get latest reading (required) — `GET /api/mongo/readings/latest?region_code=PJME`

**Response (200 OK):**
```json
{
  "region_code": "PJME",
  "region_name": "PJM East",
  "date": "2018-08-03T00:00:00",
  "day_of_week": 4,
  "is_weekend": 0,
  "is_holiday": 0,
  "daily_stats": {"avg_mw": 35486.0, "min_mw": 35486.0, "max_mw": 35486.0, "peak_hour": 0, "n_hours": 1},
  "hourly_readings": [
    {"hour": 0, "ts": "2018-08-03T00:00:00", "mw": 35486.0, "lag_1h": 38500.0, "lag_24h": 37158.0,
     "lag_168h": 35742.0, "rolling_mean_24h": 39593.041666666664, "rolling_mean_7d": 35881.5,
     "rolling_std_24h": 6225.26295920377, "split": "test"}
  ]
}
```
`n_hours: 1` is correct, not a bug — 2018-08-03 is the last (partial) day in the dataset, so only hour 0 exists.

### 2. Get records by date range (required) — `GET /api/mongo/readings/range?region_code=PJME&start_date=2015-07-01T00:00:00&end_date=2015-07-03T00:00:00`

**Response (200 OK):** 3 day-documents, `daily_stats` shown (each document's `hourly_readings` has the full 24 embedded
hours, omitted here for brevity — see `src/database/mongodb/sample_documents.json` for a complete example):

```json
[
  {"region_code": "PJME", "date": "2015-07-01T00:00:00", "day_of_week": 2, "is_weekend": 0, "is_holiday": 0,
   "daily_stats": {"avg_mw": 35255.46, "min_mw": 25657.0, "max_mw": 43512.0, "peak_hour": 17, "n_hours": 24}},
  {"region_code": "PJME", "date": "2015-07-02T00:00:00", "day_of_week": 3, "is_weekend": 0, "is_holiday": 0,
   "daily_stats": {"avg_mw": 31838.67, "min_mw": 24859.0, "max_mw": 36172.0, "peak_hour": 15, "n_hours": 24}},
  {"region_code": "PJME", "date": "2015-07-03T00:00:00", "day_of_week": 4, "is_weekend": 0, "is_holiday": 1,
   "daily_stats": {"avg_mw": 30024.88, "min_mw": 22588.0, "max_mw": 36880.0, "peak_hour": 17, "n_hours": 24}}
]
```

### 3. Get one document — `GET /api/mongo/readings/PJME/2018-08-03T00:00:00`

**Response (200 OK):** identical to the latest-reading response above.

### 4. Create (append an hour to an existing day) — `POST /api/mongo/readings?region_code=PJME&date=2018-08-03T00:00:00`

**Request:**
```json
{
  "hour": 1, "ts": "2018-08-03T01:00:00", "mw": 30000.0,
  "lag_1h": null, "lag_24h": null, "lag_168h": null,
  "rolling_mean_24h": null, "rolling_mean_7d": null, "rolling_std_24h": null,
  "split": "test"
}
```

**Response (200 OK):** `{"message": "Reading added"}` — confirmed via a follow-up GET that the day-document's
`hourly_readings` grew from 1 to 2 entries (`[0, 1]`).

Note: this endpoint requires the `region_code`+`date` day-document to already exist — `POST` for a date with no
existing document correctly returns `404 {"detail": "Day document not found for this region and date"}`. Creating a
brand-new day from scratch isn't supported via the API; only hours within a pre-seeded day (from the Task 2 loader)
can be added, updated, or removed.

### 5. Update — `PUT /api/mongo/readings/PJME/2018-08-03T00:00:00/1`

**Request:** `{"mw": 31000.0}`

**Response (200 OK):** `{"message": "Reading updated"}` — a follow-up GET shows hour 1's `mw` changed from 30000.0 to
31000.0.

### 6. Delete — `DELETE /api/mongo/readings/PJME/2018-08-03T00:00:00/1`

**Response (200 OK):** `{"message": "Reading deleted"}` — a follow-up GET confirms `hourly_readings` is back to 1
entry, restoring the document to its original state.

### 7. Create prediction — `POST /api/mongo/predictions`

**Request:**
```json
{
  "region_code": "PJME",
  "target_ts": "2018-08-03T02:00:00",
  "predicted_mw": 33150.0,
  "model_name": "xgboost"
}
```

**Response (200 OK):**
```json
{
  "region_code": "PJME",
  "target_ts": "2018-08-03T02:00:00",
  "predicted_mw": 33150.0,
  "model_name": "xgboost",
  "generated_at": "2026-10-25T09:56:08.765167"
}
```

## Duplicate predictions — `409 Conflict`

Both `predictions` stores have a unique `(region, target_ts, model_name)` key. Posting the exact same prediction a
second time to either `POST /api/sql/predictions` or `POST /api/mongo/predictions` is rejected:

**Response (409 Conflict):**
```json
{"detail": "Prediction already exists for this region, target_ts and model"}
```

The forecast script (Task 4) treats 409 as "already predicted by a previous run" and carries on.
