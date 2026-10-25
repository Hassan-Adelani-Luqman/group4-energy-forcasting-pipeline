# Task 2 — Database Design (Phase 2)

Relational (MySQL) and non-relational (MongoDB) designs over the same PJM
hourly energy dataset produced by Phase 1 (`data/processed/*.csv`).

## Prerequisites

```bash
docker compose up -d          # starts MySQL 8 (:3306) and MongoDB 7 (:27017)
pip install -r requirements.txt
```

Connection settings come from `.env` (see `.env.example`).

## Relational design (MySQL)

Normalised to **3NF** across four tables. The wide processed CSV is split so the
calendar attributes — which depend only on the timestamp, not on the region or
the measured load — live in their own table instead of repeating on every row.

| Table | Grain | Purpose |
|---|---|---|
| `regions` | one row per PJM sub-region | reference data (`PJME`, `AEP`) |
| `calendar_features` | one row per distinct hour | hour / day-of-week / month / weekend / holiday flags |
| `energy_readings` | one row per (region, hour) | fact table: `mw` + lag & rolling features + split label |
| `predictions` | one row per forecast | model outputs, written by the Phase 4 script |

Key constraints: `energy_readings` has a **unique `(region_id, reading_ts)`**
key, an FK to `regions`, and an FK to `calendar_features (reading_ts)`.
`predictions` has a unique `(region_id, target_ts, model_name)` key.

- Schema: [`sql/schema.sql`](sql/schema.sql)
- ERD: [`../../docs/erd.mmd`](../../docs/erd.mmd) (Mermaid — render at <https://mermaid.live>)

### Load & query

```bash
python -m src.database.sql.load_mysql        # applies schema.sql, then loads both regions
mysql -h 127.0.0.1 -u root -p energy_pipeline < src/database/sql/queries.sql
```

The five demonstration queries ([`sql/queries.sql`](sql/queries.sql)) cover the
two required time-series queries plus three analytical ones:

1. **Latest record** per region *(required)*
2. **Records by date range** *(required)*
3. Average load by day-of-week — JOIN + GROUP BY across `calendar_features`
4. 7-day rolling average — SQL **window function** over daily means
5. Peak hour on record per region

## Non-relational design (MongoDB)

**Document-per-region-per-day** in the `energy_daily` collection: each document
holds one calendar day for one region, with the 24 hourly observations embedded
as `hourly_readings[]` and a precomputed `daily_stats` sub-document. A full day's
load curve is retrieved in a single read — the natural time-series access
pattern — while the `region_code + date` index keeps range scans cheap.
`predictions` is a parallel one-document-per-forecast collection.

- Loader: [`mongodb/setup.py`](mongodb/setup.py)
- Sample documents: [`mongodb/sample_documents.json`](mongodb/sample_documents.json)
- Queries: [`mongodb/queries.py`](mongodb/queries.py)

### Load & query

```bash
python -m src.database.mongodb.setup         # drops & rebuilds energy_daily + predictions
python -m src.database.mongodb.queries       # prints the four demonstration queries
```

The four queries cover: **latest record** *(required)*, **date range**
*(required)*, monthly average via `$group`, and daily-peak-hour distribution
plus an all-time peak via `$unwind`.
