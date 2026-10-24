"""Data cleaning utilities for hourly PJM energy consumption series."""

import pandas as pd


def load_raw_series(csv_path, mw_col):
    df = pd.read_csv(csv_path, parse_dates=["Datetime"])
    df = df.rename(columns={"Datetime": "datetime", mw_col: "mw"})
    df = df.sort_values("datetime").set_index("datetime")
    return df[["mw"]]


def dedupe(df):
    return df[~df.index.duplicated(keep="first")]


def reindex_hourly(df):
    full_index = pd.date_range(df.index.min(), df.index.max(), freq="h")
    return df.reindex(full_index)


def report_gaps(df, mw_col="mw"):
    missing = df[mw_col].isna()
    missing_hours = int(missing.sum())
    total_hours = len(df)
    return {
        "total_hours": total_hours,
        "missing_hours": missing_hours,
        "missing_pct": round(100 * missing_hours / total_hours, 4),
    }


def fill_gaps(df, mw_col="mw", max_gap=3):
    """Linearly interpolate gaps of length <= max_gap hours (e.g. DST/meter
    blips). Longer gaps are considered unreliable to interpolate over, so
    they're forward/backward-filled instead as a conservative fallback."""
    filled = df.copy()
    filled[mw_col] = filled[mw_col].interpolate(
        method="linear", limit=max_gap, limit_area="inside"
    )
    if filled[mw_col].isna().any():
        filled[mw_col] = filled[mw_col].ffill().bfill()
    return filled


def clean_pipeline(csv_path, mw_col, max_gap=3):
    raw = load_raw_series(csv_path, mw_col)
    raw = dedupe(raw)
    reindexed = reindex_hourly(raw)
    gap_report = report_gaps(reindexed)
    cleaned = fill_gaps(reindexed, max_gap=max_gap)
    return cleaned, gap_report
