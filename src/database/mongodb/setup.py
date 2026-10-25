"""Build the MongoDB collections from Phase 1's processed CSVs.

Document model
--------------
``energy_daily`` uses a document-per-region-per-day design: each document holds
one calendar day for one region, with the 24 hourly observations embedded as an
array plus a precomputed ``daily_stats`` sub-document. This keeps a full day's
load curve in a single read — the natural access pattern for time-series review.

``predictions`` is a parallel collection (one document per forecast), left empty
here and written to by the Phase 4 forecast script.

Usage
-----
    docker compose up -d
    python -m src.database.mongodb.setup                 # load all regions
    python -m src.database.mongodb.setup --sample-out sample_documents.json
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
from pymongo import ASCENDING, MongoClient

from src.database.config import PROCESSED_DIR, REGIONS, mongo_db_name, mongo_uri

DAILY_COLLECTION = "energy_daily"
PRED_COLLECTION = "predictions"


def _num(value):
    """NaN -> None; keep plain python floats/ints for BSON."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _build_day_doc(region_code: str, region_name: str, day, group: pd.DataFrame) -> dict:
    """One document = one region for one calendar day."""
    hourly = []
    for r in group.sort_values("datetime").itertuples(index=False):
        hourly.append(
            {
                "hour": int(r.hour),
                "ts": r.datetime.to_pydatetime(),
                "mw": _num(r.mw),
                "lag_1h": _num(r.lag_1h),
                "lag_24h": _num(r.lag_24h),
                "lag_168h": _num(r.lag_168h),
                "rolling_mean_24h": _num(r.rolling_mean_24h),
                "rolling_mean_7d": _num(r.rolling_mean_7d),
                "rolling_std_24h": _num(r.rolling_std_24h),
                "split": r.split,
            }
        )

    mw = group["mw"]
    peak_row = group.loc[mw.idxmax()]
    return {
        "region_code": region_code,
        "region_name": region_name,
        "date": pd.Timestamp(day).to_pydatetime(),
        "day_of_week": int(group["day_of_week"].iloc[0]),
        "is_weekend": int(group["is_weekend"].iloc[0]),
        "is_holiday": int(group["is_holiday"].iloc[0]),
        "daily_stats": {
            "avg_mw": round(float(mw.mean()), 2),
            "min_mw": float(mw.min()),
            "max_mw": float(mw.max()),
            "peak_hour": int(peak_row["hour"]),
            "n_hours": int(len(group)),
        },
        "hourly_readings": hourly,
    }


def _region_docs(region_code: str):
    meta = REGIONS[region_code]
    csv_path = PROCESSED_DIR / meta["processed_file"]
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing {csv_path}. Run the Phase 1 notebook to regenerate "
            "data/processed/ from data/raw/ first."
        )
    df = pd.read_csv(csv_path, parse_dates=["datetime"])
    df["date"] = df["datetime"].dt.normalize()
    for day, group in df.groupby("date"):
        yield _build_day_doc(region_code, meta["region_name"], day, group)


def _json_default(obj):
    """Serialize datetimes for the sample-doc dump."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"not serializable: {type(obj)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load processed CSVs into MongoDB.")
    parser.add_argument(
        "--sample-out",
        metavar="PATH",
        help="also write the first 2 daily docs (+ a mock prediction) as pretty JSON",
    )
    args = parser.parse_args()

    client = MongoClient(mongo_uri())
    db = client[mongo_db_name()]

    db[DAILY_COLLECTION].drop()
    db[PRED_COLLECTION].drop()

    sample_docs = []
    total = 0
    for code in REGIONS:
        docs = list(_region_docs(code))
        db[DAILY_COLLECTION].insert_many(docs)
        total += len(docs)
        print(f"[{code}] energy_daily: {len(docs)} day-documents")
        if args.sample_out and code == "PJME":
            # first two complete (24-hour) days; insert_many adds an ObjectId _id to
            # each doc in place, so drop it to keep the dump plain JSON
            full_days = [d for d in docs if d["daily_stats"]["n_hours"] == 24][:2]
            sample_docs = [{k: v for k, v in d.items() if k != "_id"} for d in full_days]

    # indexes for the demonstration queries
    db[DAILY_COLLECTION].create_index([("region_code", ASCENDING), ("date", ASCENDING)])
    db[PRED_COLLECTION].create_index(
        [("region_code", ASCENDING), ("target_ts", ASCENDING), ("model_name", ASCENDING)],
        unique=True,
    )
    print(f"[done] energy_daily total: {total} documents; predictions ready (empty).")

    if args.sample_out:
        # a representative empty-collection prediction doc so the report shows its shape
        mock_pred = {
            "region_code": "PJME",
            "target_ts": "2018-08-03T01:00:00",
            "predicted_mw": 32950.5,
            "model_name": "xgboost",
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        }
        out = Path(args.sample_out)
        if not out.is_absolute():
            out = Path(__file__).with_name(args.sample_out)
        payload = {
            "energy_daily": sample_docs,
            "predictions": [mock_pred],
        }
        out.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
        print(f"[sample] wrote {out}")


if __name__ == "__main__":
    main()
