"""Feature engineering for hourly PJM energy consumption series."""

import pandas as pd
import holidays

US_HOLIDAYS = holidays.US()


def add_calendar_features(df):
    out = df.copy()
    out["hour"] = out.index.hour
    out["day_of_week"] = out.index.dayofweek
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(int)
    out["is_holiday"] = [int(ts.date() in US_HOLIDAYS) for ts in out.index]
    out["month"] = out.index.month
    return out


def add_lag_features(df, mw_col="mw"):
    out = df.copy()
    out["lag_1h"] = out[mw_col].shift(1)
    out["lag_24h"] = out[mw_col].shift(24)
    out["lag_168h"] = out[mw_col].shift(168)
    return out


def add_rolling_features(df, mw_col="mw"):
    """Rolling stats are computed on values shifted by 1h first, so the
    current hour's own reading never leaks into its own feature."""
    out = df.copy()
    shifted = out[mw_col].shift(1)
    out["rolling_mean_24h"] = shifted.rolling(window=24).mean()
    out["rolling_mean_7d"] = shifted.rolling(window=24 * 7).mean()
    out["rolling_std_24h"] = shifted.rolling(window=24).std()
    return out


def build_feature_set(df, mw_col="mw"):
    out = add_calendar_features(df)
    out = add_lag_features(out, mw_col)
    out = add_rolling_features(out, mw_col)
    return out


def chronological_split(df, val_days=30, test_days=30):
    """Label rows train/val/test by time, never shuffled: the last
    `test_days` are test, the `val_days` before that are validation,
    everything earlier is train."""
    df = df.sort_index()
    test_start = df.index.max() - pd.Timedelta(days=test_days) + pd.Timedelta(hours=1)
    val_start = test_start - pd.Timedelta(days=val_days)

    split = pd.Series("train", index=df.index)
    split.loc[df.index >= val_start] = "val"
    split.loc[df.index >= test_start] = "test"

    out = df.copy()
    out["split"] = split
    return out
