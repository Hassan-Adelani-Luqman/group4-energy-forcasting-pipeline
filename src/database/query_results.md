# Captured Query Results


```bash
docker-compose up -d
python -m src.database.sql.load_mysql
docker exec -i <mysql-container> mysql -uroot -prootpass energy_pipeline < src/database/sql/queries.sql
python -m src.database.mongodb.setup
python -m src.database.mongodb.queries
```

Load produced: MySQL — 145,224 PJME rows + 121,128 AEP rows in `energy_readings`. MongoDB — 6,052 PJME + 5,048 AEP
day-documents in `energy_daily`.

## MySQL (`src/database/sql/queries.sql`)

### Q1 (required: latest record per region)

| region_code | reading_ts | mw | split |
|---|---|---|---|
| AEP | 2018-08-03 00:00:00 | 14809.00 | test |
| PJME | 2018-08-03 00:00:00 | 35486.00 | test |

### Q2 (required: records by date range) — PJME, 2015-07-01 to 2015-07-08

168 hourly rows returned. First and last 5 shown (full output reproducible via the command above):

| reading_ts | mw | lag_24h | rolling_mean_24h |
|---|---|---|---|
| 2015-07-01 00:00:00 | 32040.00 | 29043.00 | 33739.8750 |
| 2015-07-01 01:00:00 | 29444.00 | 26634.00 | 33864.7500 |
| 2015-07-01 02:00:00 | 27546.00 | 25068.00 | 33981.8333 |
| 2015-07-01 03:00:00 | 26361.00 | 24110.00 | 34085.0833 |
| 2015-07-01 04:00:00 | 25686.00 | 23706.00 | 34178.8750 |
| ... | ... | ... | ... |
| 2015-07-07 19:00:00 | 48843.00 | 44687.00 | 39236.5417 |
| 2015-07-07 20:00:00 | 46988.00 | 42990.00 | 39409.7083 |
| 2015-07-07 21:00:00 | 45572.00 | 41665.00 | 39576.2917 |
| 2015-07-07 22:00:00 | 44255.00 | 40544.00 | 39739.0833 |
| 2015-07-07 23:00:00 | 40613.00 | 37623.00 | 39893.7083 |

### Q3 (analytical: average load by day-of-week, join)

| region_code | day_of_week | dow_label | avg_mw | n_hours |
|---|---|---|---|---|
| AEP | 0 | Mon | 15813.1 | 17304 |
| AEP | 1 | Tue | 16059.8 | 17304 |
| AEP | 2 | Wed | 16015.8 | 17304 |
| AEP | 3 | Thu | 16030.3 | 17304 |
| AEP | 4 | Fri | 15775.4 | 17304 |
| AEP | 5 | Sat | 14613.2 | 17304 |
| AEP | 6 | Sun | 14202.4 | 17304 |
| PJME | 0 | Mon | 32671.3 | 20736 |
| PJME | 1 | Tue | 33274.8 | 20759 |
| PJME | 2 | Wed | 33260.3 | 20760 |
| PJME | 3 | Thu | 33084.2 | 20760 |
| PJME | 4 | Fri | 32687.0 | 20737 |
| PJME | 5 | Sat | 30162.6 | 20736 |
| PJME | 6 | Sun | 29404.8 | 20736 |

Confirms the weekday/weekend effect already seen in Phase 1's Q3 (EDA notebook) at the database-query level.

### Q4 (analytical: 7-day rolling average, window function) — PJME, first 30 days

| reading_date | daily_avg_mw | rolling_7d_avg_mw |
|---|---|---|
| 2002-01-08 | 34501.0 | 34501.0 |
| 2002-01-09 | 33776.2 | 34138.6 |
| 2002-01-10 | 31471.5 | 33249.6 |
| 2002-01-11 | 30947.5 | 32674.1 |
| 2002-01-12 | 28466.9 | 31832.6 |
| 2002-01-13 | 28052.8 | 31202.7 |
| 2002-01-14 | 31603.0 | 31259.8 |
| 2002-01-15 | 31223.8 | 30791.7 |
| 2002-01-16 | 32009.8 | 30539.3 |
| 2002-01-17 | 31881.3 | 30597.9 |
| 2002-01-18 | 32043.1 | 30754.4 |
| 2002-01-19 | 31926.3 | 31248.6 |
| 2002-01-20 | 29482.9 | 31452.9 |
| 2002-01-21 | 32434.9 | 31571.7 |
| 2002-01-22 | 31539.6 | 31616.9 |
| 2002-01-23 | 31494.3 | 31543.2 |
| 2002-01-24 | 30615.8 | 31362.4 |
| 2002-01-25 | 30183.8 | 31096.8 |
| 2002-01-26 | 28076.7 | 30546.9 |
| 2002-01-27 | 26645.6 | 30141.5 |
| 2002-01-28 | 29487.8 | 29720.5 |
| 2002-01-29 | 29028.2 | 29361.7 |
| 2002-01-30 | 28574.8 | 28944.7 |
| 2002-01-31 | 30375.8 | 28910.4 |
| 2002-02-01 | 29662.9 | 28836.0 |
| 2002-02-02 | 28647.1 | 28917.5 |
| 2002-02-03 | 28598.8 | 29196.5 |
| 2002-02-04 | 32563.7 | 29635.9 |
| 2002-02-05 | 34954.2 | 30482.5 |
| 2002-02-06 | 32970.0 | 31110.4 |

### Q5 (analytical: peak hour on record per region)

| region_code | peak_ts | peak_mw |
|---|---|---|
| AEP | 2008-10-20 14:00:00 | 25695.00 |
| PJME | 2006-08-02 17:00:00 | 62009.00 |

## MongoDB (`src/database/mongodb/queries.py`)

### Q1 (required: latest record)
```
latest day for PJME: 2018-08-03  avg_mw=35486.0  peak_hour=0
```

### Q2 (required: records by date range) — PJME, 2015-07-01 to 2015-07-08

7 day-documents:

| date | avg_mw | max_mw |
|---|---|---|
| 2015-07-01 | 35255.46 | 43512.0 |
| 2015-07-02 | 31838.67 | 36172.0 |
| 2015-07-03 | 30024.88 | 36880.0 |
| 2015-07-04 | 28120.12 | 31315.0 |
| 2015-07-05 | 30047.0 | 38438.0 |
| 2015-07-06 | 36481.54 | 45701.0 |
| 2015-07-07 | 40018.29 | 50038.0 |

### Q3 (analytical: `$group` — average daily load by calendar month, PJME, all years)

| month | avg_daily_mw | n_days |
|---|---|---|
| 1 | 34367.8 | 520 |
| 2 | 33435.0 | 480 |
| 3 | 30510.0 | 527 |
| 4 | 27861.4 | 510 |
| 5 | 28695.4 | 527 |
| 6 | 33811.8 | 510 |
| 7 | 37882.0 | 527 |
| 8 | 36593.8 | 499 |
| 9 | 31484.1 | 480 |
| 10 | 28117.0 | 496 |
| 11 | 29327.7 | 480 |
| 12 | 32676.5 | 496 |

### Q4 (analytical: `$unwind` — daily-peak-hour distribution + all-time peak, PJME)

| peak hour | days it was the daily peak |
|---|---|
| 19 | 1312 |
| 18 | 1060 |
| 17 | 923 |
| 20 | 841 |
| 21 | 687 |

All-time peak hourly reading: **2006-08-02 17:00, 62,009 MW** — matches the SQL Q5 result exactly, as expected since
both query the same underlying data through different engines.
