from __future__ import annotations

from functools import lru_cache
from typing import Optional, cast

import numpy as np
import pandas as pd
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .infer import get_series_df, load_artifacts_cached, walk_forward, ensure_dt_index_tz
from .models import Library, Signal
from .utils.active import get_active_family_version

# If your clean_choice requires defaults, we’ll validate manually instead.
FAMILIES = {"cnn", "lstm", "cnn_lstm", "cnn_lstm_attn"}
PH_TZ = "Asia/Manila"

# -------------------- parsing --------------------
def parse_local_dt(s: str) -> pd.Timestamp:
    ts = pd.to_datetime(s, errors="coerce")
    if pd.isna(ts):
        raise ValueError("Invalid datetime format.")
    ts = ts.tz_localize(PH_TZ) if ts.tz is None else ts.tz_convert(PH_TZ)
    return ts

def parse_local_date(s: str) -> pd.Timestamp:
    ts = pd.to_datetime(s, errors="coerce")
    if pd.isna(ts):
        raise ValueError("Invalid date.")
    ts = ts.normalize()
    ts = ts.tz_localize(PH_TZ) if ts.tz is None else ts.tz_convert(PH_TZ)
    return ts

# -------------------- profile fallback --------------------
def build_profile(library: Library, weeks: int = 8) -> Optional[pd.Series]:
    qs = Signal.objects.filter(library=library).values_list("ts", "wifi_clients")
    df = pd.DataFrame(qs, columns=["ts", "wifi"])
    if df.empty:
        return None

    ts_local = pd.to_datetime(df["ts"], utc=True, errors="coerce").tz_convert(PH_TZ)
    frame = (
        pd.DataFrame({"ts_local": ts_local, "wifi": df["wifi"].astype(int)})
        .dropna(subset=["ts_local"])
    )

    cutoff = pd.Timestamp.now(tz=PH_TZ) - pd.Timedelta(weeks=weeks)
    frame = frame.loc[frame["ts_local"] >= cutoff]
    if frame.empty:
        return None

    frame["dow"] = frame["ts_local"].dt.dayofweek.astype(int)
    frame["hour"] = frame["ts_local"].dt.hour.astype(int)
    prof = frame.groupby(["dow", "hour"])["wifi"].mean().round().astype(int)
    return prof

@lru_cache(maxsize=64)
def _load_profile_cached(lib_pk: int) -> Optional[pd.Series]:
    lib = Library.objects.get(pk=lib_pk)
    return build_profile(lib)

def load_profile(library: Library) -> Optional[pd.Series]:
    return _load_profile_cached(int(library.pk))

def profile_lookup(profile: Optional[pd.Series], target_utc: pd.Timestamp | str) -> int:
    if profile is None or profile.empty:
        return 0
    ts = pd.to_datetime(target_utc, utc=True, errors="coerce")
    if pd.isna(ts):
        return 0
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    t_local = ts.tz_convert(PH_TZ)
    key = (int(t_local.dayofweek), int(t_local.hour))
    try:
        return int(profile.loc[key])
    except Exception:
        return 0

# -------------------- internal wrapper --------------------
def _forecast_steps(
    model,
    scaler,
    window: int,
    base_vals: np.ndarray,
    steps: int,
    base_index: Optional[pd.DatetimeIndex],
    meta: dict,
) -> np.ndarray:
    """
    Always call walk_forward; it auto-switches to hybrid if meta carries
    'feature_order' + 'ohe' and base_index is provided.
    """
    idx: Optional[pd.DatetimeIndex] = None
    if base_index is not None:
        # Silence type-checkers and guarantee tz-aware UTC
        idx = pd.DatetimeIndex(base_index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")

    

    return walk_forward(
        model=model,
        scaler=scaler,
        window=int(window),
        base_series=np.asarray(base_vals, dtype=float),
        steps=int(steps),
        base_index=idx,
        meta=meta,
    )

# -------------------- views --------------------
class ForecastAtView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lib_key = (request.query_params.get("library") or "").strip()
            family_q = (request.query_params.get("family") or "").strip() or None
            version_q = (request.query_params.get("version") or "").strip() or None
            when_s = request.query_params.get("when")
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        if not lib_key or not when_s:
            return Response({"detail": "Missing 'library' or 'when'."}, status=400)

        lib = get_object_or_404(Library, key=lib_key)

        # Resolve active/default family+version AFTER lib is known
        fam_default, ver_default = get_active_family_version(lib)
        family = family_q or fam_default
        version = version_q or ver_default
        if family not in FAMILIES:
            return Response({"detail": f"Unknown model family: {family}"}, status=400)

        try:
            when_local = parse_local_dt(when_s)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        when_utc = when_local.tz_convert("UTC")

        model, scaler, window, meta = load_artifacts_cached(family, lib.key, version)

        # Pull only what's needed (window + small cushion)
        need = int(window) + 6
        history = get_series_df(lib, hours=need)
        history = ensure_dt_index_tz(history, tz="UTC")

        if history.empty or len(history) < int(window):
            prof = load_profile(lib)
            yhat = profile_lookup(prof, when_utc)
            return Response({
                "ok": True, "stale": True, "mode": "profile",
                "prediction": int(max(0, yhat)),
                "library": lib.key, "model_family": family,
                "model_version": meta.get("model_version"),
                "data_ts_latest": None,
                "requested_utc": when_utc.isoformat(),
                "generated_at": timezone.now().isoformat(),
            }, status=200)

        last_known = history.index[-1]
        gap_h = int(np.ceil((when_utc - last_known).total_seconds() / 3600.0))

        base_vals = history.values.astype(float)
        base_index = pd.DatetimeIndex(history.index)  # satisfy type checkers

        if gap_h <= 2:
            yhat = float(_forecast_steps(model, scaler, window, base_vals, max(1, gap_h), base_index, meta)[-1])
            return Response({
                "ok": True, "stale": False, "mode": "live",
                "prediction": int(round(max(0, yhat))),
                "library": lib.key, "model_family": family,
                "model_version": meta.get("model_version"),
                "data_ts_latest": last_known.isoformat(),
                "requested_utc": when_utc.isoformat(),
                "generated_at": timezone.now().isoformat(),
            }, status=200)

        if gap_h <= 24:
            prof = load_profile(lib)
            s = history.asfreq("h")  # UTC index; 'h' avoids FutureWarning
            fill_idx = pd.date_range(
                start=last_known + pd.Timedelta(hours=1),
                end=when_utc,
                freq="h",
                tz="UTC",
            )
            fill_vals = [profile_lookup(prof, t) for t in fill_idx]
            s_filled = pd.concat([s, pd.Series(fill_vals, index=fill_idx)], axis=0).astype(float)
            s_filled = ensure_dt_index_tz(s_filled, tz="UTC")

            yhat = float(_forecast_steps(
                model, scaler, window,
                base_vals=s_filled.values.astype(float),
                steps=max(1, gap_h),
                base_index=pd.DatetimeIndex(s_filled.index),
                meta=meta
            )[-1])

            return Response({
                "ok": True, "stale": True, "mode": "seeded",
                "prediction": int(round(max(0, yhat))),
                "library": lib.key, "model_family": family,
                "model_version": meta.get("model_version"),
                "data_ts_latest": last_known.isoformat(),
                "requested_utc": when_utc.isoformat(),
                "generated_at": timezone.now().isoformat(),
            }, status=200)

        prof = load_profile(lib)
        yhat = profile_lookup(prof, when_utc)
        return Response({
            "ok": True, "stale": True, "mode": "profile",
            "prediction": int(max(0, yhat)),
            "library": lib.key, "model_family": family,
            "model_version": meta.get("model_version"),
            "data_ts_latest": last_known.isoformat(),
            "requested_utc": when_utc.isoformat(),
            "generated_at": timezone.now().isoformat(),
        }, status=200)


class ForecastDayView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lib_key = (request.query_params.get("library") or "").strip()
            family_q = (request.query_params.get("family") or "").strip() or None
            version_q = (request.query_params.get("version") or "").strip() or None
            date_s = request.query_params.get("date")
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        if not lib_key or not date_s:
            return Response({"detail": "Missing 'library' or 'date'."}, status=400)

        lib = get_object_or_404(Library, key=lib_key)

        # Resolve active/default family+version AFTER lib is known
        fam_default, ver_default = get_active_family_version(lib)
        family = family_q or fam_default
        version = version_q or ver_default
        if family not in FAMILIES:
            return Response({"detail": f"Unknown model family: {family}"}, status=400)

        try:
            day_local = parse_local_date(date_s)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        # Build target hours for requested local date
        hours_local = pd.date_range(day_local, day_local + pd.Timedelta(hours=23), freq="h", tz=PH_TZ)
        hours_utc = hours_local.tz_convert("UTC")
        start_utc = hours_utc[0]

        model, scaler, window, meta = load_artifacts_cached(family, lib.key, version)

        # Seed history that ENDS at requested midnight (or now if future)
        need_seed_hours = max(int(window), 24)
        history = get_series_df(lib, hours=need_seed_hours, end_utc=start_utc)
        history = ensure_dt_index_tz(history, tz="UTC")
        if len(history) < int(window):
            return Response({"detail": "Not enough history to predict."}, status=422)

        last_known = history.index[-1]
        base_vals = history.values.astype(float)
        base_index = pd.DatetimeIndex(history.index)  # ensure DatetimeIndex type

        # If requested day starts after last data point, roll forward to midnight
        gap_h = int(np.ceil((start_utc - last_known).total_seconds() / 3600.0))
        if gap_h > 0:
            MAX_GAP = 24 * 90
            gap_h = min(gap_h, MAX_GAP)
            gap_preds = _forecast_steps(model, scaler, window, base_vals, gap_h, base_index, meta)

            seed_vals = np.concatenate([base_vals, gap_preds]).astype(float)
            gap_index = pd.date_range(
                start=last_known + pd.Timedelta(hours=1),
                end=start_utc,
                freq="h",
                tz="UTC",
            )
            seed_index = pd.DatetimeIndex(base_index.append(gap_index))
        else:
            seed_vals = base_vals
            seed_index = base_index

        # Forecast the 24 hours for the requested day
        day_preds = _forecast_steps(model, scaler, window, seed_vals, 24, seed_index, meta)
        out_vals = day_preds[-24:]

        preds = [int(round(max(0.0, x))) for x in out_vals]
        lower = [max(0, int(round(x * 0.85))) for x in out_vals]
        upper = [int(round(x * 1.15)) for x in out_vals]

        return Response({
            "ok": True,
            "library": lib.key,
            "date_local": day_local.date().isoformat(),
            "points": [
                {
                    "time_local": t.isoformat(),
                    "time_utc": tu.isoformat(),
                    "predicted": p,
                    "lo": lo,
                    "hi": hi,
                }
                for t, tu, p, lo, hi in zip(hours_local, hours_utc, preds, lower, upper)
            ],
            "model_family": family,
            "model_version": version,
            "data_ts_latest": last_known.isoformat(),
            "generated_at": timezone.now().isoformat(),
        }, status=200)


class HistoryDayView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lib_key = request.query_params.get("library")
            date_s = request.query_params.get("date")
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        if not lib_key or not date_s:
            return Response({"detail": "Missing 'library' or 'date'."}, status=400)

        lib = get_object_or_404(Library, key=lib_key)

        day_local = pd.to_datetime(date_s, errors="coerce")
        if pd.isna(day_local):
            return Response({"detail": "Invalid date."}, status=400)
        day_local = day_local.normalize().tz_localize(PH_TZ)

        start_utc = day_local.tz_convert("UTC")
        end_utc = (day_local + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).tz_convert("UTC")

        qs = (
            Signal.objects
            .filter(library=lib, ts__gte=start_utc, ts__lte=end_utc)
            .order_by("ts")
            .values_list("ts", "wifi_clients")
        )
        df = pd.DataFrame(qs, columns=["ts", "wifi"])

        if df.empty:
            series: list[dict] = []
        else:
            df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
            df = df.dropna(subset=["ts"]).set_index("ts").sort_index()

            idx = cast(pd.DatetimeIndex, df.index)
            df.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")

            series = []
            for ts_utc, v in df["wifi"].items():
                ts_utc = cast(pd.Timestamp, ts_utc)
                series.append({
                    "time_local": ts_utc.tz_convert(PH_TZ).isoformat(),
                    "time_utc": ts_utc.isoformat(),
                    "actual": int(v),
                })

        return Response({
            "ok": True,
            "library": lib.key,
            "date_local": day_local.date().isoformat(),
            "points": series,
        }, status=200)
