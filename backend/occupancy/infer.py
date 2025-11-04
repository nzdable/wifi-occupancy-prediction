# infer.py
from pathlib import Path
import json, pickle, numpy as np
import pandas as pd
from django.conf import settings
from functools import lru_cache
from keras.models import load_model

ARTIFACTS_ROOT = Path(settings.BASE_DIR) / "artifacts"
PH_TZ = "Asia/Manila"

LIBRARY_CAPACITIES = {
    "gisbert_2nd_floor": 250,
    "gisbert_3rd_floor": 100, 
    "gisbert_4th_floor": 100,
    "gisbert_5th_floor": 100,
    "american_corner": 80,
    "miguel_pro": 500
}

LIBRARY_CORRECTION_FACTORS = {
    'miguel_pro': 1.5,
    'gisbert_2nd_floor': 8.0,
    'american_corner': 3.5,
    'gisbert_4th_floor': 5.0,
    'gisbert_5th_floor': 10.0,
    'gisbert_3rd_floor': 5.0,
}

def correct_live_occupancy(raw_occupancy, lib_key):
    multiplier = LIBRARY_CORRECTION_FACTORS.get(lib_key, 1.0)
    return raw_occupancy * multiplier

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

    feature_order = preproc.get("spec", {}).get("feature_order")
    ohe = preproc.get("ohe")
    scaling_metadata = preproc.get("spec", {}).get("scaling_metadata", {})
    
    if isinstance(meta, dict):
        meta = {**meta, "feature_order": feature_order, "ohe": ohe, "scaling_metadata": scaling_metadata}
    else:
        meta = {"model_version": "v1", "feature_order": feature_order, "ohe": ohe, "scaling_metadata": scaling_metadata}

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

    lib_key = library.key if hasattr(library, 'key') else str(library)
    s = s.apply(lambda x: correct_live_occupancy(x, lib_key))
    s = s.round().astype(int)

    idx = pd.date_range(start=start, end=end, freq="h", tz="UTC")
    s = s.reindex(idx, fill_value=0)
    return s.rename("occupancy")

# -------------------- ENHANCED Feature engineering --------------------
def _sched_row(ts_local: pd.Timestamp) -> dict:
    hour = ts_local.hour
    dow = ts_local.dayofweek
    
    # Enhanced day differentiation
    is_weekend = int(dow >= 5)
    is_sunday = int(dow == 6)
    is_monday = int(dow == 0)
    is_friday = int(dow == 4)
    
    # Enhanced library hours with better differentiation
    if dow < 5:  # Weekdays
        library_open = int(7 <= hour < 20)
    elif dow == 5:  # Saturday
        library_open = int(7 <= hour < 12)
    else:  # Sunday
        library_open = 0

    # Enhanced class schedule - differentiate by day
    if dow < 5:  # Weekdays only
        class_hours = int(7 <= hour < 22)
    else:
        class_hours = 0

    # Enhanced activity periods - specific to days
    if dow == 0:  # Monday
        activity_period = int(15 <= hour < 18)
    elif dow == 2:  # Wednesday  
        activity_period = int(15 <= hour < 18)
    else:
        activity_period = 0

    # Enhanced peak hours with day differentiation
    if dow < 5:  # Weekdays
        morning_peak = int(8 <= hour < 11)
        afternoon_peak = int(13 <= hour < 16)
        evening_peak = int(18 <= hour < 20)
    else:  # Weekend
        morning_peak = int(9 <= hour < 12) if dow == 5 else 0  # Saturday morning
        afternoon_peak = 0
        evening_peak = 0

    # Holiday logic
    is_holiday = 0
    is_preliminary = 0

    # Enhanced study intensity with day weighting
    day_weight = 1.0
    if is_monday or dow == 2:  # Monday/Wednesday - high intensity
        day_weight = 1.2
    elif is_friday:  # Friday - lower intensity
        day_weight = 0.8
    elif is_weekend:  # Weekend - much lower
        day_weight = 0.5

    study_intensity = library_open * (
        class_hours + activity_period + 
        (1 - is_holiday) + (1 - is_preliminary)
    ) * day_weight

    # Cyclic encoding
    hour_sin = np.sin(2 * np.pi * hour / 24.0)
    hour_cos = np.cos(2 * np.pi * hour / 24.0)
    dow_sin = np.sin(2 * np.pi * dow / 7.0)
    dow_cos = np.cos(2 * np.pi * dow / 7.0)

    return {
        "hour": hour, 
        "day_of_week": dow,
        "is_weekend": is_weekend, 
        "is_sunday": is_sunday,
        "library_open": library_open, 
        "class_hours": class_hours, 
        "activity_period": activity_period,
        "morning_peak": morning_peak, 
        "afternoon_peak": afternoon_peak, 
        "evening_peak": evening_peak,
        "is_holiday": is_holiday, 
        "is_preliminary": is_preliminary, 
        "study_intensity": study_intensity,
        "hour_sin": hour_sin, 
        "hour_cos": hour_cos, 
        "dow_sin": dow_sin, 
        "dow_cos": dow_cos,
    }

def _ohe_vec(hour: int, dow: int, ohe) -> np.ndarray:
    if ohe is None:
        return np.zeros((1, 0), dtype=float)

    ohe_in = list(getattr(ohe, "feature_names_in_", [])) or ["hour", "day_of_week"]

    data = {}
    for name in ohe_in:
        if name.lower() in ("hour", "hr"):
            data[name] = [hour]
        elif name.lower() in ("day_of_week", "dow", "weekday"):
            data[name] = [dow]
        else:
            data[name] = [0]

    X_df = pd.DataFrame(data)
    return ohe.transform(X_df).astype(float)

def _row_vector(ts_utc: pd.Timestamp, occ_value: float, occ_scaler, ohe, feature_order: list[str], meta: dict, lib_key: str) -> np.ndarray:
    ts_local = ts_utc.tz_convert(PH_TZ)
    sched = _sched_row(ts_local)

    # --- CAPACITY-AWARE SCALING ---
    library_capacity = LIBRARY_CAPACITIES.get(lib_key, 100)  # Default to 100 if not found
    
    if occ_scaler is not None and hasattr(occ_scaler, 'transform'):
        try:
            # Scale based on library capacity, not training data range
            occ_scaled = occ_value / library_capacity  # Convert to 0-1 range based on capacity
        except Exception as e:
            print(f"Capacity scaling error: {e}, using fallback")
            occ_scaled = occ_value / 100  # Fallback scaling
    else:
        # Manual capacity-based scaling
        occ_scaled = occ_value / library_capacity

    # Build numeric features
    num_features = {
        "occupancy_scaled": float(occ_scaled),
        "is_weekend": float(sched["is_weekend"]),
        "is_sunday": float(sched["is_sunday"]),
        "library_open": float(sched["library_open"]),
        "class_hours": float(sched["class_hours"]),
        "activity_period": float(sched["activity_period"]),
        "morning_peak": float(sched["morning_peak"]),
        "afternoon_peak": float(sched["afternoon_peak"]),
        "evening_peak": float(sched["evening_peak"]),
        "is_holiday": float(sched["is_holiday"]),
        "is_preliminary": float(sched["is_preliminary"]),
        "study_intensity": float(sched["study_intensity"]),
        "hour_sin": float(sched["hour_sin"]),
        "hour_cos": float(sched["hour_cos"]),
        "dow_sin": float(sched["dow_sin"]),
        "dow_cos": float(sched["dow_cos"]),
    }

    # Categorical OHE features
    if ohe is not None:
        try:
            cat_vec = _ohe_vec(int(sched["hour"]), int(sched["day_of_week"]), ohe).ravel()
            ohe_names = list(ohe.get_feature_names_out(['hour', 'day_of_week']))
        except Exception as e:
            print(f"OHE error: {e}")
            cat_vec = np.array([])
            ohe_names = []
    else:
        cat_vec = np.array([])
        ohe_names = []

    # Combine all features in correct order
    feature_bank = {**num_features}
    for i, name in enumerate(ohe_names):
        feature_bank[name] = float(cat_vec[i]) if i < len(cat_vec) else 0.0

    # Ensure feature order matches training exactly
    try:
        result = np.array([feature_bank[name] for name in feature_order], dtype=float)
    except KeyError as e:
        print(f"Missing feature in order: {e}")
        result = np.zeros(len(feature_order), dtype=float)
        for i, name in enumerate(feature_order):
            if name in feature_bank:
                result[i] = feature_bank[name]
    
    return result

def _one_step_hybrid(
    model, occ_scaler, ohe, feature_order, meta, lib_key: str,
    window_ts: pd.DatetimeIndex,
    window_vals: np.ndarray
) -> float:
    rows = [
        _row_vector(ts, occ, occ_scaler, ohe, feature_order, meta, lib_key)
        for ts, occ in zip(window_ts, window_vals)
    ]
    X = np.stack(rows, axis=0)[None, ...]  # Shape: (1, window, n_features)
    
    # Make prediction
    yhat_scaled = model.predict(X, verbose=0).ravel()[0]

    # SPECIAL HANDLING FOR MIGUEL_PRO - Based on actual data patterns
    if lib_key == "miguel_pro":
        # Use data-driven capacity limits instead of theoretical 500
        library_capacity = 80  # Based on actual max of 66 + small buffer
        yhat = yhat_scaled * library_capacity
        
        # Apply much more conservative constraints
        yhat = max(0.0, min(yhat, 150))  # Cap at 150 (well above actual max of 66)
        
        # Add reality checks based on time of day
        current_hour = pd.Timestamp.now(PH_TZ).hour
        current_dow = pd.Timestamp.now(PH_TZ).dayofweek
        
        # Sunday should have VERY low occupancy based on patterns
        if current_dow == 6:  # Sunday
            yhat = max(0, min(yhat, 20))  # Sundays rarely exceed 20
        
        # Evening hours should be low
        elif current_hour >= 18 or current_hour < 7:
            yhat = max(0, min(yhat, 30))

    if lib_key == "gisbert_3rd_floor":
        # Use traditional inverse scaling instead of capacity-based
        if occ_scaler is not None and hasattr(occ_scaler, 'inverse_transform'):
            yhat = occ_scaler.inverse_transform([[yhat_scaled]])[0][0]
        else:
            # Fallback scaling
            yhat = yhat_scaled * 100
        
        # Apply realistic constraints but keep more variation
        
        current_hour = pd.Timestamp.now(PH_TZ).hour
        current_dow = pd.Timestamp.now(PH_TZ).dayofweek

        # Peak hour multipliers
        if current_dow < 5:  # Weekdays
            if 8 <= current_hour < 11:   # Morning peak
                yhat *= 1.3
            elif 13 <= current_hour < 16: # Afternoon peak  
                yhat *= 1.4
            elif 18 <= current_hour < 20: # Evening peak
                yhat *= 1.2
        elif current_dow == 5:  # Saturday
            if 9 <= current_hour < 12:   # Saturday morning
                yhat *= 1.1

        yhat = max(0.0, yhat)
        return float(yhat)
    else:
        # --- CAPACITY-AWARE INVERSE SCALING ---
        library_capacity = LIBRARY_CAPACITIES.get(lib_key, 100)
        # Convert from 0-1 scaled prediction back to actual occupancy
        yhat = yhat_scaled * library_capacity    
        # Apply realistic constraints based on library capacity
        yhat = max(0.0, min(yhat, library_capacity * 0.8))  # Cap at 80% of capacity
    
    # Add time-based adjustments for more realistic predictions
    current_hour = pd.Timestamp.now(PH_TZ).hour
    current_dow = pd.Timestamp.now(PH_TZ).dayofweek
    
    # Peak hour multipliers
    if lib_key == "miguel_pro":
        if current_dow < 5:  # Weekdays
            if 8 <= current_hour < 11:   # Morning peak
                yhat *= 1.2
            elif 13 <= current_hour < 16: # Afternoon peak  
                yhat *= 1.3
            elif 18 <= current_hour < 20: # Evening peak
                yhat *= 1.1
        elif current_dow == 5:  # Saturday
            if 9 <= current_hour < 12:   # Saturday morning
                yhat *= 1.1
    else:
        # Original multipliers for other libraries
        if current_dow < 5:
            if 8 <= current_hour < 11:
                yhat *= 1.3
            elif 13 <= current_hour < 16:
                yhat *= 1.4
            elif 18 <= current_hour < 20:
                yhat *= 1.2
        elif current_dow == 5:
            if 9 <= current_hour < 12:
                yhat *= 1.1
    

    if lib_key == "miguel_pro":
        yhat = max(0, min(yhat, 120))
    else:
        # Ensure final prediction is realistic
        yhat = max(0, min(yhat, library_capacity * 0.9))
    
    print(f"Prediction debug - scaled: {yhat_scaled:.4f}, capacity: {library_capacity}, final: {yhat:.1f}")
    return float(yhat)

def _one_step_simple(model, scaler, window, recent_vals: np.ndarray, lib_key: str) -> float:
    # Simple fallback with capacity awareness
    library_capacity = LIBRARY_CAPACITIES.get(lib_key, 100)
    
    # Use moving average as base prediction
    avg_occupancy = np.mean(recent_vals[-6:])  # Last 6 hours
    
    # Apply capacity-based scaling and time adjustments
    base_prediction = avg_occupancy * 1.2  # Slight upward trend
    
    # Cap at reasonable levels
    yhat = min(base_prediction, library_capacity * 0.7)
    yhat = max(15, yhat)  # Minimum reasonable occupancy
    
    return float(yhat)

def walk_forward(model, scaler, window, base_series: np.ndarray, steps: int,
                 base_index: pd.DatetimeIndex | None = None, meta: dict | None = None,
                 lib_key: str = "unknown") -> np.ndarray:
    
    print(f"Walk forward for {lib_key}: window={window}, steps={steps}, series_range={base_series.min():.1f}-{base_series.max():.1f}")
    
    feature_order = (meta or {}).get("feature_order")
    ohe = (meta or {}).get("ohe")
    occ_scaler = scaler

    # HYBRID PATH
    if feature_order and ohe is not None and base_index is not None:
        print(f"Using HYBRID path for {lib_key} (capacity: {LIBRARY_CAPACITIES.get(lib_key, 'unknown')})")
        buf_vals = list(map(float, base_series))
        buf_ts = pd.DatetimeIndex(pd.to_datetime(base_index, utc=True)).tz_convert("UTC")

        preds = []
        for step in range(int(steps)):
            window_vals = np.array(buf_vals[-window:], dtype=float)
            window_ts   = pd.DatetimeIndex(buf_ts[-window:]).tz_convert("UTC")
            
            y = _one_step_hybrid(model, occ_scaler, ohe, feature_order, meta, lib_key, window_ts, window_vals)
            preds.append(y)
            
            # Update buffers
            last_ts = pd.Timestamp(buf_ts[-1]).tz_convert("UTC")
            buf_ts  = buf_ts.append(pd.DatetimeIndex([last_ts + pd.Timedelta(hours=1)]))
            buf_vals.append(y)
            
            print(f"Step {step+1}: predicted {y:.1f} users")
            
        return np.array(preds, dtype=float)

    # CLASSIC PATH (fallback)
    print(f"Using CLASSIC path for {lib_key}")
    buf = base_series.astype(float).tolist()
    preds = []
    for step in range(int(steps)):
        window_vals = np.array(buf[-window:], dtype=float)
        y = _one_step_simple(model, scaler, window, window_vals, lib_key)
        preds.append(y)
        buf.append(y)
        print(f"Step {step+1}: predicted {y:.1f} users")
        
    return np.array(preds, dtype=float)

def one_step(
    model,
    scaler,
    window: int,
    recent_vals: np.ndarray,
    base_index: pd.DatetimeIndex | None = None,
    meta: dict | None = None,
    lib_key: str = "unknown"
) -> float:
    """
    Single-step forecast with library capacity awareness
    """
    preds = walk_forward(
        model=model,
        scaler=scaler,
        window=int(window),
        base_series=np.asarray(recent_vals, dtype=float),
        steps=1,
        base_index=base_index,
        meta=meta,
        lib_key=lib_key
    )
    return float(preds[-1])

def ensure_dt_index_tz(df_or_s, tz=PH_TZ):
    """Return object with a tz-aware DatetimeIndex (coerce if needed)."""
    obj = df_or_s
    idx = obj.index

    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, errors="coerce", utc=True)

    if not isinstance(idx, pd.DatetimeIndex):
        raise ValueError("History index cannot be parsed as datetime")

    if idx.tz is None:
        idx = idx.tz_localize(tz)
    else:
        idx = idx.tz_convert(tz)

    obj.index = idx
    return obj