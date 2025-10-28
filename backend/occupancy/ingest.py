# occupancy/ingest.py
import pandas as pd

def aggregate_per_cleaned_library(
    df: pd.DataFrame,
    *,
    tz: str = "Asia/Manila",
    ts_col: str = "Start_dt",
    mac_col: str = "Client MAC",
    dayfirst: bool = True,
) -> pd.DataFrame:
    """
    Aggregate a per-library 'cleaned' CSV to hourly unique client counts.
    Returns DataFrame with columns [ts, wifi_clients]; ts is UTC and hour-aligned.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["ts", "wifi_clients"])

    if ts_col not in df.columns or mac_col not in df.columns:
        raise ValueError(f"CSV must have columns '{ts_col}' and '{mac_col}'")

    # Parse timestamps (day-first), localize to the CSV timezone, convert to UTC, floor to hour
    ts = pd.to_datetime(df[ts_col], errors="coerce", dayfirst=dayfirst)
    ts = ts.dt.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    ts = ts.dt.floor("H")

    tmp = pd.DataFrame({"ts": ts, "mac": df[mac_col].astype(str)}).dropna()

    # Group and rename safely
    agg = tmp.groupby("ts")["mac"].nunique().reset_index(name="wifi_clients")
    agg["wifi_clients"] = agg["wifi_clients"].astype(int)

    return agg[["ts", "wifi_clients"]]
