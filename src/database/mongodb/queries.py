"""Task 2 demonstration queries for the MongoDB database.

Run against collections loaded with:  python -m src.database.mongodb.setup
    python -m src.database.mongodb.queries

Each function returns plain Python results and prints a short summary so the
output can be captured for the report.
"""
from __future__ import annotations

from pymongo import DESCENDING, MongoClient

from src.database.config import mongo_db_name, mongo_uri

DAILY = "energy_daily"


def latest_day(db, region_code: str = "PJME"):
    """Q1 (required: LATEST RECORD) — most recent day-document for a region."""
    doc = db[DAILY].find_one(
        {"region_code": region_code},
        sort=[("date", DESCENDING)],
    )
    print(f"\n[Q1] latest day for {region_code}: {doc['date'].date()} "
          f"avg_mw={doc['daily_stats']['avg_mw']} peak_hour={doc['daily_stats']['peak_hour']}")
    return doc


def date_range(db, region_code: str, start: str, end: str):
    """Q2 (required: RECORDS BY DATE RANGE) — day-documents in [start, end)."""
    from datetime import datetime

    fmt = "%Y-%m-%d"
    cursor = db[DAILY].find(
        {
            "region_code": region_code,
            "date": {"$gte": datetime.strptime(start, fmt),
                     "$lt": datetime.strptime(end, fmt)},
        },
        {"date": 1, "daily_stats.avg_mw": 1, "daily_stats.max_mw": 1, "_id": 0},
    ).sort("date", 1)
    rows = list(cursor)
    print(f"\n[Q2] {region_code} days in [{start}, {end}): {len(rows)} documents")
    for r in rows:
        print(f"      {r['date'].date()}  avg={r['daily_stats']['avg_mw']:>9}  "
              f"max={r['daily_stats']['max_mw']:>9}")
    return rows


def monthly_average(db, region_code: str = "PJME"):
    """Q3 ($group) — average daily load per calendar month across all years."""
    pipeline = [
        {"$match": {"region_code": region_code}},
        {"$group": {
            "_id": {"$month": "$date"},
            "avg_daily_mw": {"$avg": "$daily_stats.avg_mw"},
            "n_days": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = list(db[DAILY].aggregate(pipeline))
    print(f"\n[Q3] {region_code} average load by month:")
    for r in rows:
        print(f"      month {r['_id']:>2}: avg_daily_mw={round(r['avg_daily_mw'], 1):>9}  "
              f"n_days={r['n_days']}")
    return rows


def peak_hour_distribution(db, region_code: str = "PJME"):
    """Q4 ($unwind) — which hour of day is the daily peak most often?"""
    pipeline = [
        {"$match": {"region_code": region_code}},
        {"$group": {"_id": "$daily_stats.peak_hour", "days": {"$sum": 1}}},
        {"$sort": {"days": DESCENDING}},
        {"$limit": 5},
    ]
    rows = list(db[DAILY].aggregate(pipeline))
    print(f"\n[Q4] {region_code} most common daily-peak hours:")
    for r in rows:
        print(f"      hour {r['_id']:>2}: peaked on {r['days']} days")

    # $unwind variant: the single highest hourly reading on record
    unwind = [
        {"$match": {"region_code": region_code}},
        {"$unwind": "$hourly_readings"},
        {"$sort": {"hourly_readings.mw": DESCENDING}},
        {"$limit": 1},
        {"$project": {"_id": 0, "ts": "$hourly_readings.ts", "mw": "$hourly_readings.mw"}},
    ]
    top = list(db[DAILY].aggregate(unwind))
    if top:
        print(f"      all-time peak hour: {top[0]['ts']}  mw={top[0]['mw']}")
    return rows, top


def main() -> None:
    client = MongoClient(mongo_uri())
    db = client[mongo_db_name()]
    latest_day(db, "PJME")
    date_range(db, "PJME", "2015-07-01", "2015-07-08")
    monthly_average(db, "PJME")
    peak_hour_distribution(db, "PJME")


if __name__ == "__main__":
    main()
