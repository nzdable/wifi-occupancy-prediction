# infer.py
from pathlib import Path
import json, pickle, numpy as np
import pandas as pd
from django.conf import settings
from functools import lru_cache
from keras.models import load_model

ARTIFACTS_ROOT = Path(settings.BASE_DIR) / "artifacts"
PH_TZ = "Asia/Manila"

def _utc_now():
    return pd.Timestamp.now(tz="UTC")

@lru_cache(maxsize=64)
def load_artifacts_cached(family: str, lib_key: str, version: str):
    return load_artifacts(family, lib_key, version)

def load_artifacts(family: str, lib_key: str, version: str):
    root = ARTIFACTS_ROOT / family / lib_key
    model_p = root / "model.keras"
    pre_p   = root / "preproc.pkl"
    meta_p  = root / "meta.json"
    for p in (model_p, pre_p, meta_p):
        if not p.exists():
            raise FileNotFoundError(f"Missing artifact: {p.as_posix()}")

    model  = load_model(model_p, compile=False)
    with open(pre_p, "rb") as f: preproc = pickle.load(f)
    with open(meta_p, "r")  as f: meta    = json.load(f)

    window = int(preproc["spec"]["window"])
    scaler = preproc.get("occ_scaler", None)

    # ---- carry hybrid info in meta so walk_forward can switch paths ----
    feature_order = preproc.get("spec", {}).get("feature_order")
    ohe = preproc.get("ohe")
    if isinstance(meta, dict):
        meta = {**meta, "feature_order": feature_order, "ohe": ohe}
    else:
        meta = {"model_version": "v1", "feature_order": feature_order, "ohe": ohe}

    return model, scaler, window, meta

# -------------------- Data fetch --------------------
def get_series_df(library, hours: int = 14*24, end_utc: pd.Timestamp | None = None):
    from .models import Signal

    need = max(1, int(hours))
    end = (end_utc.tz_convert("UTC").floor("h") if isinstance(end_utc, pd.Timestamp)
           else _utc_now().floor("h"))
    start = end - pd.Timedelta(hours=need-1)

    qs = (Signal.objects
          .filter(library=library, ts__gte=start, ts__lte=end)
          .order_by("ts")
          .values_list("ts", "wifi_clients"))
    df = pd.DataFrame(list(qs), columns=["ts", "wifi_clients"])

    if df.empty:
        qs2 = (Signal.objects
               .filter(library=library)
               .order_by("-ts")
               .values_list("ts", "wifi_clients")[: need * 2])
        df = pd.DataFrame(list(qs2), columns=["ts", "wifi_clients"]).iloc[::-1]
        if df.empty:
            idx = pd.date_range(start=start, end=end, freq="h", tz="UTC")
            return pd.Series(0, index=idx, name="occupancy")

    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).set_index("ts").sort_index()
    s = df["wifi_clients"].resample("h").max().fillna(0).astype(int)

    idx = pd.date_range(start=start, end=end, freq="h", tz="UTC")
    s = s.reindex(idx, fill_value=0)
    return s.rename("occupancy")

# -------------------- Feature engineering for the hybrid model --------------------
NUMERIC_FEATURES = [
    'occupancy_scaled','is_weekend','is_sunday','library_open','class_hours',
    'activity_period','morning_peak','afternoon_peak','evening_peak',
    'is_holiday','is_preliminary','study_intensity','hour_sin','hour_cos','dow_sin','dow_cos'
]

def _sched_row(ts_local: pd.Timestamp) -> dict:
    hour = ts_local.hour
    dow  = ts_local.dayofweek
    is_weekend   = int(dow >= 5)
    is_sunday    = int(dow == 6)

    # Library hours: Mon–Fri 7–19, Sat 7–11 (bin by hour)
    library_open = int((dow < 5 and 7 <= hour < 20) or (dow == 5 and 7 <= hour < 12))
    class_hours  = int((dow < 5) and (7 <= hour < 22))
    activity_period = int((dow in (0,2)) and (15 <= hour < 18))
    morning_peak   = int((dow < 5) and (8  <= hour < 11))
    afternoon_peak = int((dow < 5) and (13 <= hour < 16))
    evening_peak   = int((dow < 5) and (18 <= hour < 20))

    is_holiday = 0
    is_preliminary = 0

    study_intensity = int(library_open and (class_hours or activity_period) and not is_holiday and not is_preliminary)

    hour_sin = np.sin(2*np.pi*hour/24.0)
    hour_cos = np.cos(2*np.pi*hour/24.0)
    dow_sin  = np.sin(2*np.pi*dow/7.0)
    dow_cos  = np.cos(2*np.pi*dow/7.0)

    return {
        "hour": hour, "day_of_week": dow,
        "is_weekend": is_weekend, "is_sunday": is_sunday,
        "library_open": library_open, "class_hours": class_hours, "activity_period": activity_period,
        "morning_peak": morning_peak, "afternoon_peak": afternoon_peak, "evening_peak": evening_peak,
        "is_holiday": is_holiday, "is_preliminary": is_preliminary, "study_intensity": study_intensity,
        "hour_sin": hour_sin, "hour_cos": hour_cos, "dow_sin": dow_sin, "dow_cos": dow_cos,
    }

def _ohe_vec(hour: int, dow: int, ohe) -> np.ndarray:
    """
    Transform using the same feature names/order the encoder was fitted with.
    Falls back to ['hour','day_of_week'] if metadata is missing.
    """
    if ohe is None:
        return np.zeros((1, 0), dtype=float)

    # Respect fitted names if present (sklearn >=1.0 usually sets this)
    ohe_in = list(getattr(ohe, "feature_names_in_", [])) or ["hour", "day_of_week"]

    # Build a one-row DataFrame with those exact column names
    data = {}
    # map by name; if someone trained with different order/names, we still align
    for name in ohe_in:
        if name.lower() in ("hour", "hr"):
            data[name] = [hour]
        elif name.lower() in ("day_of_week", "dow", "weekday"):
            data[name] = [dow]
        else:
            # unknown extra column name — default to 0
            data[name] = [0]

    X_df = pd.DataFrame(data)
    return ohe.transform(X_df).astype(float)  # (1, k)

def _row_vector(ts_utc: pd.Timestamp, occ_value: float, occ_scaler, ohe, feature_order: list[str]) -> np.ndarray:
    ts_local = ts_utc.tz_convert(PH_TZ)
    sched = _sched_row(ts_local)

    # --- numeric block (with named column for scaler) ---
    # Respect the scaler's fitted feature name if present
    scaler_in = list(getattr(occ_scaler, "feature_names_in_", [])) or ["occupancy"]
    scaler_col = list(getattr(occ_scaler, "feature_names_in_", []))[:1] or ["occupancy"]
    occ_df = pd.DataFrame([[occ_value]], columns=[scaler_col[0]])

    if hasattr(occ_scaler, "transform"):
        _arr = occ_scaler.transform(occ_df)   # returns ndarray
        occ_scaled = float(_arr[0, 0])
    else:
        occ_scaled = float(occ_value)

    num = {
        "occupancy_scaled": occ_scaled,
        **{k: float(sched[k]) for k in NUMERIC_FEATURES if k != "occupancy_scaled"},
    }

    # --- categorical OHE block (now using named DF in _ohe_vec) ---
    cat_vec = _ohe_vec(int(sched["hour"]), int(sched["day_of_week"]), ohe).ravel() if ohe is not None else np.array([])

    # names for the OHE block in the same way they were exported
    ohe_names = list(getattr(ohe, "get_feature_names_out", lambda *_: [])(['hour', 'day_of_week'])) if ohe is not None else []

    # Assemble according to the exact training order in feature_order
    bank = {**num}
    for i, name in enumerate(ohe_names):
        bank[name] = float(cat_vec[i]) if cat_vec.size else 0.0

    return np.array([bank[name] for name in feature_order], dtype=float)

def _one_step_hybrid(
    model, occ_scaler, ohe, feature_order,
    window_ts: pd.DatetimeIndex,
    window_vals: np.ndarray
) -> float:
    rows = [
        _row_vector(ts, occ, occ_scaler, ohe, feature_order)
        for ts, occ in zip(window_ts, window_vals)
    ]
    X = np.stack(rows, axis=0)[None, ...]
    yhat_scaled = model.predict(X, verbose=0).ravel()[0]
    yhat = occ_scaler.inverse_transform([[yhat_scaled]])[0, 0] if occ_scaler is not None else yhat_scaled
    return float(max(0.0, yhat))

def _one_step_simple(model, scaler, window, recent_vals: np.ndarray) -> float:
    x = scaler.transform(recent_vals.reshape(-1, 1))
    x = x.reshape(1, window, 1)
    yhat_scaled = model.predict(x, verbose=0)
    yhat = scaler.inverse_transform(yhat_scaled).ravel()[0]
    return float(max(0.0, yhat))

def walk_forward(model, scaler, window, base_series: np.ndarray, steps: int,
                 base_index: pd.DatetimeIndex | None = None, meta: dict | None = None) -> np.ndarray:
    """
    If meta includes 'feature_order' and 'ohe' and base_index is provided,
    use the hybrid path (window×N features + timestamps). Else, classic path.
    """
    feature_order = (meta or {}).get("feature_order")
    ohe = (meta or {}).get("ohe")
    occ_scaler = scaler

    # --- HYBRID PATH ---
    if feature_order and ohe is not None and base_index is not None:
        buf_vals = list(map(float, base_series))
        buf_ts = pd.DatetimeIndex(pd.to_datetime(base_index, utc=True)).tz_convert("UTC")

        preds = []
        for _ in range(int(steps)):
            window_vals = np.array(buf_vals[-window:], dtype=float)
            window_ts   = pd.DatetimeIndex(buf_ts[-window:]).tz_convert("UTC")
            y = _one_step_hybrid(model, occ_scaler, ohe, feature_order, window_ts, window_vals)
            preds.append(y)
            last_ts = pd.Timestamp(buf_ts[-1]).tz_convert("UTC")
            buf_ts  = buf_ts.append(pd.DatetimeIndex([last_ts + pd.Timedelta(hours=1)]))
            buf_vals.append(y)
        return np.array(preds, dtype=float)

    # --- CLASSIC PATH ---
    buf = base_series.astype(float).tolist()
    preds = []
    for _ in range(int(steps)):
        window_vals = np.array(buf[-window:], dtype=float)
        y = _one_step_simple(model, scaler, window, window_vals)
        preds.append(y)
        buf.append(y)
    return np.array(preds, dtype=float)

def one_step(
    model,
    scaler,
    window: int,
    recent_vals: np.ndarray,
    base_index: pd.DatetimeIndex | None = None,
    meta: dict | None = None,
) -> float:
    """
    Single-step forecast.
    Uses the same hybrid/classic switching as `walk_forward`:
    - If meta has 'feature_order' + 'ohe' and base_index is provided (tz-aware UTC),
      it will use the hybrid path.
    - Otherwise it falls back to the classic (window×1) path.
    """
    preds = walk_forward(
        model=model,
        scaler=scaler,
        window=int(window),
        base_series=np.asarray(recent_vals, dtype=float),
        steps=1,
        base_index=base_index,
        meta=meta,
    )
    return float(preds[-1])

def ensure_dt_index_tz(df_or_s, tz=PH_TZ):
    """Return object with a tz-aware DatetimeIndex (coerce if needed)."""
    obj = df_or_s
    idx = obj.index

    # If it’s a plain column you set as index later, call this AFTER set_index('ts')
    if not isinstance(idx, pd.DatetimeIndex):
        # try to coerce whatever the index is into datetime with UTC
        idx = pd.to_datetime(idx, errors="coerce", utc=True)

    # If still not datetime (all NaT), bail early (let caller raise a clean 400)
    if not isinstance(idx, pd.DatetimeIndex):
        raise ValueError("History index cannot be parsed as datetime")

    # Localize or convert
    if idx.tz is None:
        idx = idx.tz_localize(tz)
    else:
        idx = idx.tz_convert(tz)

    obj.index = idx
    return obj