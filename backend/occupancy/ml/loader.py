# backend/occupancy/loader.py
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    # If running inside Django
    from django.conf import settings
    BASE_DIR = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2]))
except Exception:
    # Fallback for standalone scripts
    BASE_DIR = Path(__file__).resolve().parents[2]

# -------- env-configurable filenames (what you already had) --------
MODEL_DIR   = os.getenv("MODEL_DIR", "artifacts")
MODEL_FILE  = os.getenv("MODEL_FILE", "model.keras")
PREPROC_FILE= os.getenv("PREPROC_FILE", "preproc.pkl")
META_FILE   = os.getenv("META_FILE", "meta.json")

# Optional default family for UI fallback / student default suggestion
MODEL_DEFAULT_FAMILY = os.getenv("MODEL_DEFAULT_FAMILY", "cnn_lstm_attn")

# Recognized families (keep in sync with frontend & views)
FAMILIES = ("cnn", "lstm", "cnn_lstm", "cnn_lstm_attn")

# Absolute root where artifacts live
ARTIFACTS_ROOT = (BASE_DIR / MODEL_DIR).resolve()

def artifacts_triplet_paths(family: str, lib_key: str) -> Tuple[Path, Path, Path]:
    """
    Build absolute paths to {model, preproc, meta} for a given (family, library).
    Layout:
      <BASE_DIR>/<MODEL_DIR>/<family>/<lib_key>/{model.keras,preproc.pkl,meta.json}
    """
    root = ARTIFACTS_ROOT / family / lib_key
    return root / MODEL_FILE, root / PREPROC_FILE, root / META_FILE

def _assert_exists(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing artifact: {p.as_posix()}")

def _safe_load_pickle(p: Path) -> Any:
    with open(p, "rb") as f:
        return pickle.load(f)

def _safe_load_json(p: Path) -> Dict[str, Any]:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_keras(path: Path):
    # Import lazily so unit tests (without TF) can still run
    from keras.models import load_model
    return load_model(path, compile=False)

def load_artifacts(family: str, lib_key: str) -> Tuple[Any, Any, int, Dict[str, Any]]:
    """
    Returns: (model, scaler/occ_scaler, window:int, meta:dict)

    - Works for all families; hybrid paths (cnn_lstm / cnn_lstm_attn) carry the
      'feature_order' and 'ohe' inside the returned meta (if present in preproc).
    - For simple CNN/LSTM, scaler is whatever was saved as 'occ_scaler' (or None).
    """
    if family not in FAMILIES:
        raise ValueError(f"Unknown model family '{family}'. Expected one of {FAMILIES}.")

    model_p, pre_p, meta_p = artifacts_triplet_paths(family, lib_key)
    for p in (model_p, pre_p, meta_p):
        _assert_exists(p)

    # Load on disk
    model  = _load_keras(model_p)
    pre    = _safe_load_pickle(pre_p)
    meta   = _safe_load_json(meta_p)

    # Pull training-time spec
    spec   = (pre or {}).get("spec", {})
    window = int(spec.get("window", 24))

    # Primary scaler for occupancy
    occ_scaler = (pre or {}).get("occ_scaler", None)

    # Hybrid extras (if any)
    feature_order: Optional[List[str]] = (spec or {}).get("feature_order")
    ohe = (pre or {}).get("ohe")

    # Enrich meta so the inference code can auto-switch to hybrid when available
    if isinstance(meta, dict):
        meta = {
            **meta,
            "feature_order": feature_order,
            "ohe": ohe,
            "model_family": meta.get("model_family", family),
        }
    else:
        meta = {
            "model_version": "v1",
            "model_family": family,
            "feature_order": feature_order,
            "ohe": ohe,
        }

    return model, occ_scaler, window, meta

def get_model_bundle(family: str, lib_key: str):
    """
    Back-compat for legacy callers:
    Returns (model, preproc, meta) where:
      - preproc["spec"]["window"] (int)
      - preproc["spec"]["feature_order"] (list[str])  # present for hybrid
      - preproc["occ_scaler"] (scaler)
      - preproc["ohe"] (sklearn OneHotEncoder)  # only for hybrid models
    """
    model, occ_scaler, window, meta = load_artifacts(family, lib_key)

    # Build the legacy `preproc` dict shape expected by existing code
    feature_order = meta.get("feature_order") or ["occupancy_scaled"]
    preproc = {
        "spec": {
            "window": int(window),
            "feature_order": feature_order,
        },
        "occ_scaler": occ_scaler,
    }
    if meta.get("ohe") is not None:
        preproc["ohe"] = meta["ohe"]

    return model, preproc, meta

# ---------- Discovery helpers (handy for the Admin “Active Model” UI) ----------
def list_library_families(lib_key: str) -> List[Dict[str, Any]]:
    """
    For a given library key, return a list like:
      [
        {"family":"cnn", "versions":["v1.2"]},
        {"family":"lstm","versions":["v1.0"]},
        {"family":"cnn_lstm","versions":["v1.1"]},
        ...
      ]
    The “versions” here are read from each family's <meta.json> -> model_version.
    (One version per family, matching your current layout.)
    """
    out: List[Dict[str, Any]] = []
    for fam in FAMILIES:
        m_p, p_p, j_p = artifacts_triplet_paths(fam, lib_key)
        if m_p.exists() and p_p.exists() and j_p.exists():
            try:
                meta = _safe_load_json(j_p)
                ver = str(meta.get("model_version", "v1"))
                out.append({"family": fam, "versions": [ver]})
            except Exception:
                # If meta is malformed, still expose family with unknown version
                out.append({"family": fam, "versions": []})
    return out

def list_all_libraries() -> List[str]:
    """
    Enumerate library keys present under any family, e.g. ["american_corner", "gisbert_3rd_floor", ...]
    """
    libs: set[str] = set()
    for fam in FAMILIES:
        fam_dir = ARTIFACTS_ROOT / fam
        if fam_dir.exists() and fam_dir.is_dir():
            for child in fam_dir.iterdir():
                if child.is_dir():
                    libs.add(child.name)
    return sorted(libs)

def default_family() -> str:
    """Single place to read the default family (for UI or fallbacks)."""
    if MODEL_DEFAULT_FAMILY in FAMILIES:
        return MODEL_DEFAULT_FAMILY
    return "cnn_lstm_attn"
