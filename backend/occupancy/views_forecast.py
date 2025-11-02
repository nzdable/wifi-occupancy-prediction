# occupancy/views_forecast.py
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

from .infer import (
    get_series_df,
    load_artifacts_cached,
    one_step,
    walk_forward,
    _feature_row_for_ts,
    walk_forward_hybrid,
)
from .models import Library, Signal
from .utils.validate import clean_choice

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

FAMILIES = {"cnn", "lstm", "cnn_lstm", "cnn_lstm_attn"}
PH_TZ = "Asia/Manila"

# ------------------------------------------------------------------
# Helpers: parsing
# ------------------------------------------------------------------

def parse_local_dt(s: str) -> pd.Timestamp:
    """
    Parse 'YYYY-MM-DDTHH:mm' in Asia/Manila into tz-aware Timestamp.
    """
    ts = pd.to_datetime(s, errors="coerce")
    if pd.isna(ts):
        raise ValueError("Invalid datetime format.")
    if ts.tz is None:
        ts = ts.tz_localize(PH_TZ)
    else:
        ts = ts.tz_convert(PH_TZ)
    return ts


def parse_local_date(s: str) -> pd.Timestamp:
    """
    Parse 'YYYY-MM-DD' (date-only) in Asia/Manila; returns midnight Timestamp.
    """
    ts = pd.to_datetime(s, errors="coerce")
    if pd.isna(ts):
        raise ValueError("Invalid date.")
    ts = ts.normalize()
    if ts.tz is None:
        ts = ts.tz_localize(PH_TZ)
    else:
        ts = ts.tz_convert(PH_TZ)
    return ts

# ------------------------------------------------------------------
# Lightweight historical profile fallback
# ------------------------------------------------------------------

def build_profile(library: Library, weeks: int = 8) -> Optional[pd.Series]:
    """
    Build a (dow, hour) → mean wifi count profile from recent signals.
    Returns a pandas Series indexed by MultiIndex(dow, hour) or None if no data.
    """
    qs = Signal.objects.filter(library=library).values_list("ts", "wifi_clients")
    df = pd.DataFrame(qs, columns=["ts", "wifi"])
    if df.empty:
        return None

    # Convert to local PH tz; create a proper frame we can filter.
    ts_local = pd.to_datetime(df["ts"], utc=True, errors="coerce").tz_convert(PH_TZ)
    frame = pd.DataFrame({"ts_local": ts_local, "wifi": df["wifi"].astype(int)})
    frame = frame.dropna(subset=["ts_local"])

    # Keep only last N weeks.
    cutoff = pd.Timestamp.now(tz=PH_TZ) - pd.Timedelta(weeks=weeks)
    frame = frame.loc[frame["ts_local"] >= cutoff]
    if frame.empty:
        return None

    frame["dow"] = frame["ts_local"].dt.dayofweek.astype(int)
    frame["hour"] = frame["ts_local"].dt.hour.astype(int)

    prof = (
        frame.groupby(["dow", "hour"])["wifi"]
        .mean()
        .round()
        .astype(int)
    )
    return prof  # index: MultiIndex(dow, hour)


@lru_cache(maxsize=64)
def _load_profile_cached(lib_pk: int) -> Optional[pd.Series]:
    lib = Library.objects.get(pk=lib_pk)
    return build_profile(lib)


def load_profile(library: Library) -> Optional[pd.Series]:
    """
    Cached getter for a library's profile.
    """
    return _load_profile_cached(int(library.pk))


def profile_lookup(profile: Optional[pd.Series], target_utc: pd.Timestamp | str) -> int:
    """
    Return the profile mean for the given UTC timestamp.
    """
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
        # Series with MultiIndex can be accessed via .loc[(dow, hour)]
        return int(profile.loc[key])
    except Exception:
        return 0

# ------------------------------------------------------------------
# Views
# ------------------------------------------------------------------

class ForecastAtView(APIView):
    """
    One prediction for an exact future/local time.
    Supports graceful fallback to (dow, hour) profile when history is stale.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lib_key = clean_choice(request.query_params.get("library"), default="")
            family  = clean_choice(request.query_params.get("family"), default="cnn", choices=FAMILIES)
            version = clean_choice(request.query_params.get("version"), default="v1")
            when_s  = request.query_params.get("when")
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        if not lib_key or not when_s:
            return Response({"detail": "Missing 'library' or 'when'."}, status=400)

        lib = get_object_or_404(Library, key=lib_key)
        try:
            when_local = parse_local_dt(when_s)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        when_utc = when_local.tz_convert("UTC")

        # Load model artifacts once (cached)
        model, scaler, window, meta = load_artifacts_cached(family, lib.key, version)

        # Pull only what's needed (window + small cushion)
        need = int(window) + 6
        history = get_series_df(lib, hours=need)

        if history.empty or len(history) < window:
            # No seed for the ML model → pure profile fallback.
            prof = load_profile(lib)
            yhat = profile_lookup(prof, when_utc)
            return Response({
                "ok": True,
                "stale": True,
                "mode": "profile",
                "prediction": int(max(0, yhat)),
                "library": lib.key,
                "model_family": family,
                "model_version": meta.get("model_version"),
                "data_ts_latest": None,
                "requested_utc": when_utc.isoformat(),
                "generated_at": timezone.now().isoformat(),
            }, status=200)

        last_known = history.index[-1]
        gap_h = int(np.ceil((when_utc - last_known).total_seconds() / 3600.0))

        if gap_h <= 2:
            # Live ML (fast)
            base = history.values.astype(float)
            yhat = float(walk_forward(model, scaler, window, base, steps=max(1, gap_h))[-1])
            return Response({
                "ok": True,
                "stale": False,
                "mode": "live",
                "prediction": int(round(max(0, yhat))),
                "library": lib.key,
                "model_family": family,
                "model_version": meta.get("model_version"),
                "data_ts_latest": last_known.isoformat(),
                "requested_utc": when_utc.isoformat(),
                "generated_at": timezone.now().isoformat(),
            }, status=200)

        if gap_h <= 24:
            # Short gap: backfill missing hours with profile, then run ML.
            prof = load_profile(lib)
            s = history.asfreq("H")

            fill_idx = pd.date_range(start=last_known + pd.Timedelta(hours=1),
                                     end=when_utc, freq="H", tz="UTC")
            fill_vals = [profile_lookup(prof, t) for t in fill_idx]
            s = pd.concat([s, pd.Series(fill_vals, index=fill_idx)], axis=0).astype(float)

            base = s.values.astype(float)
            yhat = float(walk_forward(model, scaler, window, base, steps=max(1, gap_h))[-1])
            return Response({
                "ok": True,
                "stale": True,
                "mode": "seeded",
                "prediction": int(round(max(0, yhat))),
                "library": lib.key,
                "model_family": family,
                "model_version": meta.get("model_version"),
                "data_ts_latest": last_known.isoformat(),
                "requested_utc": when_utc.isoformat(),
                "generated_at": timezone.now().isoformat(),
            }, status=200)

        # Long gap → pure profile
        prof = load_profile(lib)
        yhat = profile_lookup(prof, when_utc)
        return Response({
            "ok": True,
            "stale": True,
            "mode": "profile",
            "prediction": int(max(0, yhat)),
            "library": lib.key,
            "model_family": family,
            "model_version": meta.get("model_version"),
            "data_ts_latest": last_known.isoformat(),
            "requested_utc": when_utc.isoformat(),
            "generated_at": timezone.now().isoformat(),
        }, status=200)


class ForecastDayView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lib_key = clean_choice(request.query_params.get("library"), default="")
            family  = clean_choice(request.query_params.get("family"), default="cnn", choices=FAMILIES)
            version = clean_choice(request.query_params.get("version"), default="v1")
            date_s  = request.query_params.get("date")
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        if not lib_key or not date_s:
            return Response({"detail": "Missing 'library' or 'date'."}, status=400)

        lib = get_object_or_404(Library, key=lib_key)
        try:
            day_local = parse_local_date(date_s)          # Asia/Manila midnight
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        # Build target hours for the requested day
        hours_local = pd.date_range(day_local, day_local + pd.Timedelta(hours=23),
                                    freq="H", tz=PH_TZ)
        hours_utc   = hours_local.tz_convert("UTC")
        start_utc   = hours_utc[0]

        model, scaler, window, meta = load_artifacts_cached(family, lib.key, version)
        

        # ---- Seed history that ENDS at the requested midnight (for past days) ----
        # If the requested day is in the future, this will just end at 'now'.
        # We request at least 'window' hours; add a small cushion.
        need_seed_hours = max(window, 24)
        history = get_series_df(lib, hours=need_seed_hours, end_utc=start_utc)

        if len(history) < window:
            return Response({"detail": "Not enough history to predict."}, status=422)

        last_known = history.index[-1]          # should be <= start_utc
        base = history.values.astype(float)

        # If the requested day starts AFTER our last data point (future gap),
        # roll forward to reach the requested midnight, then forecast the day.
        gap_h = int(np.ceil((start_utc - last_known).total_seconds() / 3600.0))
        if gap_h > 0:
            MAX_GAP = 24 * 90
            gap_h = min(gap_h, MAX_GAP)
            gap_preds = walk_forward(model, scaler, window, base, steps=gap_h)
            seed = np.concatenate([base, gap_preds]).astype(float)
        else:
            # For past days, history already ends at start_utc (or same hour)
            seed = base

        # Now forecast 24 steps for the requested day
        day_preds = walk_forward(model, scaler, window, seed, steps=24)
        out_vals  = day_preds[-24:]

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
    """
    Actual hourly occupancy (Signals) for a chosen date—useful to overlay.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lib_key = request.query_params.get("library")
            date_s  = request.query_params.get("date")
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
        end_utc   = (day_local + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).tz_convert("UTC")

        qs = (
            Signal.objects
            .filter(library=lib, ts__gte=start_utc, ts__lte=end_utc)
            .order_by("ts")
            .values_list("ts", "wifi_clients")
        )
        df = pd.DataFrame(qs, columns=["ts", "wifi"])

        if df.empty:
            series = []
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
                    "time_utc":   ts_utc.isoformat(),
                    "actual":     int(v),
                })

        return Response({
            "ok": True,
            "library": lib.key,
            "date_local": day_local.date().isoformat(),
            "points": series,
        }, status=200)
