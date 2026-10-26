"""Task 4 - forecast script (Member 4).

fetch -> preprocess (reuse Phase 1's feature pipeline) -> load model -> predict -> write
back through the Phase 3 API. Run with:

    python -m src.forecast.run_forecast                  # both regions
    python -m src.forecast.run_forecast --region PJME     # one region
"""

import argparse
import logging
import os
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from src.models.train import ARTIFACTS_DIR, FULL_FEATURES, PROJECT_ROOT
from src.preprocessing.features import build_feature_set

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("forecast")

SQL_REGION_IDS = {"PJME": 1, "AEP": 2}
WINDOW_HOURS = 24 * 14  # 14 days of history - covers lag_168h plus headroom
MODEL_NAME = "xgboost"  # Phase 1's winning model for both regions


def get_latest_timestamp(api_base: str, region_code: str) -> pd.Timestamp:
    """The dataset is historical (frozen at 2018-08-03), so "now" is wall-clock
    time, not data time - anchor the forecast on the latest reading actually in
    the DB rather than datetime.now(), or the range fetch below would come back
    empty."""
    url = f"{api_base}/api/sql/readings/latest"
    resp = requests.get(url, params={"region_id": SQL_REGION_IDS[region_code]}, timeout=30)
    resp.raise_for_status()
    return pd.Timestamp(resp.json()["reading_ts"])


def fetch_window(api_base: str, region_code: str, end_ts: pd.Timestamp) -> pd.DataFrame:
    start_ts = end_ts - timedelta(hours=WINDOW_HOURS - 1)
    url = f"{api_base}/api/sql/readings/range"
    params = {
        "region_id": SQL_REGION_IDS[region_code],
        "start_date": start_ts.isoformat(),
        "end_date": end_ts.isoformat(),
    }
    log.info(f"Fetching {region_code} window from {url} ({start_ts} -> {end_ts})")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()

    if not rows:
        raise RuntimeError(
            f"No readings returned for {region_code} in [{start_ts}, {end_ts}]. "
            "Has data been loaded into MySQL via src/database/sql/load_mysql.py?"
        )

    df = pd.DataFrame(rows)
    df["reading_ts"] = pd.to_datetime(df["reading_ts"])
    df = df.sort_values("reading_ts").set_index("reading_ts")
    log.info(f"Fetched {len(df)} rows, {df.index.min()} -> {df.index.max()}")
    return df


def build_target_features(window_df: pd.DataFrame, target_ts: pd.Timestamp) -> pd.DataFrame:
    """Extend the fetched window with one empty row at target_ts and run it
    through Phase 1's build_feature_set - the same lag/rolling code trained the
    model on - so the target's lag_1h/24h/168h and rolling stats are computed
    from the real preceding history already in hand, not re-derived by hand."""
    extended = window_df[["mw"]].copy()
    extended.loc[target_ts] = np.nan
    extended = extended.sort_index()

    featured = build_feature_set(extended)
    target_row = featured.loc[[target_ts]]

    missing = target_row[FULL_FEATURES].isna().any(axis=1).iloc[0]
    if missing:
        raise RuntimeError(
            f"Not enough history in the fetched window to compute all features for {target_ts} "
            f"(need {WINDOW_HOURS}h; rolling_mean_7d alone needs 168h of lookback)."
        )
    return target_row


def load_model(region_code: str):
    path = ARTIFACTS_DIR / f"{region_code.lower()}_winning_model.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run `python -m src.models.train` first.")
    return joblib.load(path)


def post_prediction(api_base: str, region_code: str, target_ts: pd.Timestamp, predicted_mw: float) -> None:
    target_iso = target_ts.isoformat()

    sql_payload = {
        "region_id": SQL_REGION_IDS[region_code],
        "target_ts": target_iso,
        "predicted_mw": predicted_mw,
        "model_name": MODEL_NAME,
    }
    _post_or_warn(f"{api_base}/api/sql/predictions", sql_payload, "SQL")

    mongo_payload = {
        "region_code": region_code,
        "target_ts": target_iso,
        "predicted_mw": predicted_mw,
        "model_name": MODEL_NAME,
    }
    _post_or_warn(f"{api_base}/api/mongo/predictions", mongo_payload, "Mongo")


def _post_or_warn(url: str, payload: dict, label: str) -> None:
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code == 409:
        # both predictions tables have a unique (region, target_ts, model) key -
        # re-running the script for the same (frozen-dataset) target hour hits it.
        log.warning(f"{label} write for {payload['target_ts']} skipped: already predicted by a previous run "
                    f"(409 Conflict).")
        return
    if resp.status_code >= 400:
        log.error(f"{label} write for {payload['target_ts']} failed (status {resp.status_code}): "
                  f"{resp.text[:200]}")
        return
    log.info(f"{label} prediction stored: {resp.json()}")


def run(api_base: str, region_code: str) -> float:
    log.info(f"=== Forecasting next hour for {region_code} ===")
    latest_ts = get_latest_timestamp(api_base, region_code)
    target_ts = latest_ts + timedelta(hours=1)

    window_df = fetch_window(api_base, region_code, latest_ts)
    target_features = build_target_features(window_df, target_ts)

    model = load_model(region_code)
    predicted_mw = float(model.predict(target_features[FULL_FEATURES])[0])

    log.info(f"--- BEFORE: last 3 hours of input for {region_code} ---\n"
             f"{window_df['mw'].tail(3).to_string()}")
    log.info(f"--- AFTER: {region_code} forecast for {target_ts} -> {predicted_mw:.1f} MW ---")

    post_prediction(api_base, region_code, target_ts, predicted_mw)
    return predicted_mw


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forecast the next hour of demand and write it back through the API."
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="API root URL (default: API_BASE_URL from .env, else http://localhost:8000)",
    )
    parser.add_argument("--region", choices=list(SQL_REGION_IDS), help="Single region; omit to run both.")
    args = parser.parse_args()

    regions = [args.region] if args.region else list(SQL_REGION_IDS)
    for region_code in regions:
        run(args.api_base, region_code)


if __name__ == "__main__":
    main()
