"""Populate the MySQL schema from Phase 1's processed CSVs.

Usage
-----
    # make sure the containers are up first:  docker compose up -d
    python -m src.database.sql.load_mysql            # apply schema + load all regions
    python -m src.database.sql.load_mysql --no-schema  # load only (schema already applied)

It applies ``schema.sql`` (drops & recreates the four tables), then for each
region in ``config.REGIONS`` inserts the region row, the distinct calendar
timestamps (shared across regions via INSERT IGNORE), and the hourly readings.
``predictions`` is left empty — it is filled by the Phase 4 forecast script.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src.database.config import PROCESSED_DIR, REGIONS, mysql_url

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
CHUNK = 5_000

# CSV column -> feature columns that may contain NaN and must become SQL NULL
_FEATURE_COLS = [
    "lag_1h", "lag_24h", "lag_168h",
    "rolling_mean_24h", "rolling_mean_7d", "rolling_std_24h",
]


def _clean(value):
    """Convert pandas NaN to None so the driver writes SQL NULL."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def apply_schema(engine) -> None:
    """Run schema.sql statement-by-statement (the driver runs one at a time)."""
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    # strip -- line comments before splitting so a ';' inside a comment does
    # not get mistaken for a statement terminator
    code = "\n".join(line.split("--", 1)[0] for line in raw.splitlines())
    statements = [s.strip() for s in code.split(";") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print(f"[schema] applied {len(statements)} statements from {SCHEMA_PATH.name}")


def _upsert_region(conn, code: str) -> int:
    meta = REGIONS[code]
    conn.execute(
        text(
            "INSERT INTO regions (region_code, region_name, description) "
            "VALUES (:code, :name, :desc) "
            "ON DUPLICATE KEY UPDATE region_name = VALUES(region_name)"
        ),
        {"code": code, "name": meta["region_name"], "desc": meta["description"]},
    )
    region_id = conn.execute(
        text("SELECT region_id FROM regions WHERE region_code = :code"),
        {"code": code},
    ).scalar_one()
    return region_id


def _load_region(engine, code: str) -> None:
    meta = REGIONS[code]
    csv_path = PROCESSED_DIR / meta["processed_file"]
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing {csv_path}. Run the Phase 1 notebook to regenerate "
            "data/processed/ from data/raw/ first."
        )

    df = pd.read_csv(csv_path, parse_dates=["datetime"])
    df = df.rename(columns={"datetime": "reading_ts"})

    with engine.begin() as conn:
        region_id = _upsert_region(conn, code)

        # calendar_features — dedup by ts, shared across regions (INSERT IGNORE)
        cal = (
            df[["reading_ts", "hour", "day_of_week", "month", "is_weekend", "is_holiday"]]
            .drop_duplicates(subset="reading_ts")
        )
        cal_rows = [
            {
                "ts": r.reading_ts.to_pydatetime(),
                "hour": int(r.hour),
                "dow": int(r.day_of_week),
                "month": int(r.month),
                "wknd": int(r.is_weekend),
                "hol": int(r.is_holiday),
            }
            for r in cal.itertuples(index=False)
        ]
        cal_sql = text(
            "INSERT IGNORE INTO calendar_features "
            "(reading_ts, hour, day_of_week, month, is_weekend, is_holiday) "
            "VALUES (:ts, :hour, :dow, :month, :wknd, :hol)"
        )
        for i in range(0, len(cal_rows), CHUNK):
            conn.execute(cal_sql, cal_rows[i : i + CHUNK])
        print(f"[{code}] calendar_features: {len(cal_rows)} distinct timestamps")

        # energy_readings — the fact rows
        read_sql = text(
            "INSERT INTO energy_readings "
            "(region_id, reading_ts, mw, lag_1h, lag_24h, lag_168h, "
            " rolling_mean_24h, rolling_mean_7d, rolling_std_24h, split) "
            "VALUES (:region_id, :ts, :mw, :lag_1h, :lag_24h, :lag_168h, "
            " :rm24, :rm7d, :rs24, :split)"
        )
        read_rows = [
            {
                "region_id": region_id,
                "ts": r.reading_ts.to_pydatetime(),
                "mw": float(r.mw),
                "lag_1h": _clean(r.lag_1h),
                "lag_24h": _clean(r.lag_24h),
                "lag_168h": _clean(r.lag_168h),
                "rm24": _clean(r.rolling_mean_24h),
                "rm7d": _clean(r.rolling_mean_7d),
                "rs24": _clean(r.rolling_std_24h),
                "split": r.split,
            }
            for r in df.itertuples(index=False)
        ]
        for i in range(0, len(read_rows), CHUNK):
            conn.execute(read_sql, read_rows[i : i + CHUNK])
        print(f"[{code}] energy_readings: {len(read_rows)} rows (region_id={region_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load processed CSVs into MySQL.")
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="skip applying schema.sql (assume tables already exist)",
    )
    args = parser.parse_args()

    engine = create_engine(mysql_url(), future=True)
    if not args.no_schema:
        apply_schema(engine)
    for code in REGIONS:
        _load_region(engine, code)
    print("[done] MySQL load complete.")


if __name__ == "__main__":
    main()
