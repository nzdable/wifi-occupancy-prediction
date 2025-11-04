import pandas as pd, numpy as np
from django.utils import timezone
from occupancy.models import Library, Signal, Forecast
from occupancy.ml.loader import get_model_bundle

def predict_latest_from_db(lib_key: str, family: str):
    model, preproc, meta = get_model_bundle(family, lib_key)
    spec = preproc["spec"]
    W    = spec["window"]
    feats = spec["feature_order"]

    lib = Library.objects.get(key=lib_key)
    qs = Signal.objects.filter(library=lib).order_by("-ts")[:W]
    if qs.count() < W:
        return {"ok": False, "detail": f"Need {W} Signal rows: found {qs.count()}."}

    # Oldest→Newest order, index = ts
    df = pd.DataFrame(list(qs.values("ts", "wifi_clients"))).sort_values("ts").set_index("ts")

    # ---------------------------
    # Branch by available preproc
    # ---------------------------

    # Case A: CNN (no 'ohe' in bundle, single feature 'occupancy_scaled')
    if "ohe" not in preproc and feats == ["occupancy_scaled"]:
        occ_scaled = preproc["occ_scaler"].transform(df["wifi_clients"].to_numpy().reshape(-1,1)).ravel()
        X = occ_scaled.reshape(1, W, 1)

    # Case B: hybrid/attention models (your existing path)
    else:
        idx = pd.DatetimeIndex(df.index, tz="UTC")

        # --- derived features (same as before) ---
        f = pd.DataFrame(index=idx)
        f["hour"]=idx.hour; f["day_of_week"]=idx.dayofweek
        f["is_weekend"]=(f["day_of_week"]>=5).astype(int)
        f["is_sunday"]=(f["day_of_week"]==6).astype(int)
        f["library_open"]=0; wk = (f["day_of_week"]<5)
        f.loc[wk & (f["hour"].between(7,19)), "library_open"]=1
        f["class_hours"]=0; f.loc[wk & (f["hour"].between(7,21)),"class_hours"]=1
        f["activity_period"]=0; f.loc[(f["day_of_week"].isin([0,2])) & (f["hour"].between(15,17)),"activity_period"]=1
        f["morning_peak"]=((f["hour"].between(8,10)) & wk).astype(int)
        f["afternoon_peak"]=((f["hour"].between(13,15)) & wk).astype(int)
        f["evening_peak"]=((f["hour"].between(18,19)) & wk).astype(int)
        f["is_holiday"]=0; f["is_preliminary"]=0
        f["study_intensity"]=(f["library_open"] * (f["class_hours"] + f["activity_period"] + 1 + 1)).clip(0,1)
        f["hour_sin"]=np.sin(2*np.pi*f["hour"]/24); f["hour_cos"]=np.cos(2*np.pi*f["hour"]/24)
        f["dow_sin"]=np.sin(2*np.pi*f["day_of_week"]/7); f["dow_cos"]=np.cos(2*np.pi*f["day_of_week"]/7)

        occ_scaled = preproc["occ_scaler"].transform(df["wifi_clients"].to_numpy().reshape(-1,1)).ravel()

        num = pd.DataFrame({
            'occupancy_scaled': occ_scaled,
            'is_weekend': f['is_weekend'], 'is_sunday': f['is_sunday'],
            'library_open': f['library_open'], 'class_hours': f['class_hours'],
            'activity_period': f['activity_period'], 'morning_peak': f['morning_peak'],
            'afternoon_peak': f['afternoon_peak'], 'evening_peak': f['evening_peak'],
            'is_holiday': f['is_holiday'], 'is_preliminary': f['is_preliminary'],
            'study_intensity': f['study_intensity'], 'hour_sin': f['hour_sin'],
            'hour_cos': f['hour_cos'], 'dow_sin': f['dow_sin'], 'dow_cos': f['dow_cos'],
        }, index=idx)

        cats = preproc["ohe"].transform(f[['hour', 'day_of_week']])
        cat_names = preproc["ohe"].get_feature_names_out(['hour', 'day_of_week'])
        cats_df = pd.DataFrame(cats, columns=cat_names, index=idx)

        X_df = pd.concat([num, cats_df], axis=1).reindex(columns=feats)
        X = X_df.to_numpy().reshape(1, W, X_df.shape[1])

    # Predict & inverse-scale
    y_scaled = model.predict(X, verbose=0).reshape(-1,1)
    y_pred = preproc["occ_scaler"].inverse_transform(y_scaled).ravel()[0]

    return {
        "ok": True,
        "prediction": float(y_pred),
        "generated_at": timezone.now(),
        "model_version": meta.get("model_version"),
        "model_family": family,
        "library": lib_key
    }
