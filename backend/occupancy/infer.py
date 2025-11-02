# occupancy/infer.py
from pathlib import Path
import json, pickle, numpy as np
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import pandas as pd
from keras.models import load_model
from functools import lru_cache

ARTIFACTS_ROOT = Path(settings.BASE_DIR) / "artifacts"

def _utc_now():
    # pandas-safe: always tz-aware UTC
    return pd.Timestamp.now(tz="UTC")

def load_artifacts(family: str, lib_key: str, version: str):
    root = ARTIFACTS_ROOT / family / lib_key
    model_p = root / "model.keras"
    pre_p   = root / "preproc.pkl"
    meta_p  = root / "meta.json"

    for p in (model_p, pre_p, meta_p):
        if not p.exists():
            raise FileNotFoundError(f"Missing artifact: {p.as_posix()}")

    # ⚡ faster load: no optimizer/compile graph
    model  = load_model(model_p, compile=False)
    with open(pre_p, "rb") as f: preproc = pickle.load(f)
    with open(meta_p, "r")  as f: meta    = json.load(f)

    window = int(preproc["spec"]["window"])
    scaler = preproc["occ_scaler"]
    return model, scaler, window, meta

def get_series_df(library, hours: int = 14*24, end_utc: pd.Timestamp | None = None):
    """
    Return a tz-aware UTC hourly occupancy series (name='occupancy').
    If there are no rows in [start,end], fall back to the most recent block
    of length `hours` ending at the latest available timestamp (not `end_utc`),
    so callers still get a non-zero seed they can roll forward from.
    """
    from .models import Signal

    need = max(1, int(hours))
    req_end = (end_utc.tz_convert("UTC").floor("h") if isinstance(end_utc, pd.Timestamp)
               else _utc_now().floor("h"))
    req_start = req_end - pd.Timedelta(hours=need-1)

    # First try: bounded to the requested window
    qs = (Signal.objects
          .filter(library=library, ts__gte=req_start, ts__lte=req_end)
          .order_by("ts")
          .values_list("ts", "wifi_clients"))
    df = pd.DataFrame(list(qs), columns=["ts", "wifi_clients"])

    # Fallback: no rows in requested window → pull last 2*need rows overall
    if df.empty:
        qs2 = (Signal.objects
               .filter(library=library)
               .order_by("-ts")
               .values_list("ts", "wifi_clients")[: need * 2])
        df = pd.DataFrame(list(qs2), columns=["ts", "wifi_clients"]).iloc[::-1]  # ascending

        if df.empty:
            # Truly no data in DB: return zeros ending at requested end (or now)
            idx = pd.date_range(start=req_start, end=req_end, freq="h")
            return pd.Series(0, index=idx, name="occupancy")

        # When falling back, end the window at the latest available timestamp
        avail_end = pd.to_datetime(df["ts"], utc=True, errors="coerce").dropna().max().floor("h")
        end = avail_end
    else:
        end = req_end

    # Normalize to hourly series using whatever rows we do have
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).set_index("ts").sort_index()

    s = df["wifi_clients"].resample("h").max().fillna(0).astype(int)

    # Build a contiguous hourly index ending at `end` (not always req_end)
    start = end - pd.Timedelta(hours=need-1)
    idx = pd.date_range(start=start, end=end, freq="h")
    s = s.reindex(idx, fill_value=0)

    return s.rename("occupancy")

def one_step(model, scaler, window, recent_vals: np.ndarray) -> float:
    x = scaler.transform(recent_vals.reshape(-1, 1))  # (window,1)
    x = x.reshape(1, window, 1)
    yhat_scaled = model.predict(x, verbose=0)
    yhat = scaler.inverse_transform(yhat_scaled).ravel()[0]
    return float(max(0.0, yhat))

def walk_forward(model, scaler, window, base_series: np.ndarray, steps: int) -> np.ndarray:
    buf = base_series.copy().tolist()
    preds = []
    for _ in range(steps):
        window_vals = np.array(buf[-window:])
        y = one_step(model, scaler, window, window_vals)
        preds.append(y)
        buf.append(y)
    return np.array(preds)

@lru_cache(maxsize=64)
def load_artifacts_cached(family: str, lib_key: str, version: str):
    return load_artifacts(family, lib_key, version)

def _feature_row_for_ts(ts_utc, last_occ, preproc):
    # ts_utc: pandas Timestamp tz-aware UTC
    PH_TZ = "Asia/Manila"
    tloc = ts_utc.tz_convert(PH_TZ)
    hour = int(tloc.hour); dow = int(tloc.dayofweek)

    # === numerical block ===
    f = {}
    f["occupancy_scaled"] = preproc["occ_scaler"].transform([[last_occ]])[0,0]
    # replicate your schedule rules (same as services.py):
    is_weekend = int(dow >= 5); is_sunday = int(dow == 6)
    library_open = int((dow < 5 and 7 <= hour <= 19) or (dow == 5 and 7 <= hour <= 11))
    class_hours = int(dow < 5 and 7 <= hour <= 21)
    activity_period = int(dow in [0,2] and 15 <= hour <= 17)
    morning_peak = int(dow < 5 and 8 <= hour <= 10)
    afternoon_peak = int(dow < 5 and 13 <= hour <= 15)
    evening_peak = int(dow < 5 and 18 <= hour <= 19)
    is_holiday = 0; is_preliminary = 0
    study_intensity = int(library_open and (class_hours or activity_period or 1))
    f["is_weekend"]=is_weekend; f["is_sunday"]=is_sunday
    f["library_open"]=library_open; f["class_hours"]=class_hours
    f["activity_period"]=activity_period
    f["morning_peak"]=morning_peak; f["afternoon_peak"]=afternoon_peak; f["evening_peak"]=evening_peak
    f["is_holiday"]=is_holiday; f["is_preliminary"]=is_preliminary
    f["study_intensity"]=study_intensity
    f["hour_sin"]=np.sin(2*np.pi*hour/24.0); f["hour_cos"]=np.cos(2*np.pi*hour/24.0)
    f["dow_sin"]=np.sin(2*np.pi*dow/7.0);   f["dow_cos"]=np.cos(2*np.pi*dow/7.0)

    # === categorical OHE ===
    ohe = preproc.get("ohe")
    cat = ohe.transform([[hour, dow]])  # handle_unknown="ignore"
    cat_names = list(ohe.get_feature_names_out(["hour","day_of_week"]))

    # Assemble in EXACT order
    feats = preproc["spec"]["feature_order"]
    num_block = {
      'occupancy_scaled': f["occupancy_scaled"], 'is_weekend':f["is_weekend"], 'is_sunday':f["is_sunday"],
      'library_open':f["library_open"], 'class_hours':f["class_hours"], 'activity_period':f["activity_period"],
      'morning_peak':f["morning_peak"], 'afternoon_peak':f["afternoon_peak"], 'evening_peak':f["evening_peak"],
      'is_holiday':f["is_holiday"], 'is_preliminary':f["is_preliminary"], 'study_intensity':f["study_intensity"],
      'hour_sin':f["hour_sin"], 'hour_cos':f["hour_cos"], 'dow_sin':f["dow_sin"], 'dow_cos':f["dow_cos"],
    }
    num_vec = [num_block[k] for k in preproc["spec"]["numerical_names"]]
    cat_vec = cat.ravel().tolist()
    full = dict(zip(preproc["spec"]["numerical_names"], num_vec))
    for name, val in zip(cat_names, cat_vec):
        full[name] = val
    # return vector aligned to feature_order
    return np.array([full[k] for k in feats], dtype=float)

def walk_forward_hybrid(model, preproc, window, seed_ts_idx, seed_occ_vals, steps):
    """
    seed_ts_idx: DatetimeIndex (tz-aware UTC) for the seed occupancy series
    seed_occ_vals: numpy array of occupancies aligned with seed_ts_idx
    """
    assert len(seed_ts_idx) == len(seed_occ_vals)
    feats_order = preproc["spec"]["feature_order"]
    # Build initial sliding window of FEATURE VECTORS from the last `window` timestamps
    bufX = []
    for ts, occ in zip(seed_ts_idx[-window:], seed_occ_vals[-window:]):
        bufX.append(_feature_row_for_ts(ts, occ, preproc))
    bufX = np.array(bufX)  # shape (window, n_features)
    occ_last = float(seed_occ_vals[-1])
    ts_last  = seed_ts_idx[-1]
    preds = []
    for _ in range(steps):
        # predict next using current window
        x = bufX.reshape(1, bufX.shape[0], bufX.shape[1])
        yhat_scaled = model.predict(x, verbose=0)
        # inverse scale using occ_scaler
        yhat = preproc["occ_scaler"].inverse_transform(yhat_scaled.reshape(-1,1)).ravel()[0]
        yhat = float(max(0.0, yhat))
        preds.append(yhat)
        # advance 1 hour
        ts_next = (ts_last + pd.Timedelta(hours=1)).tz_convert("UTC")
        row = _feature_row_for_ts(ts_next, yhat, preproc)
        # slide window
        bufX = np.vstack([bufX[1:], row])
        ts_last  = ts_next
        occ_last = yhat
    return np.array(preds)