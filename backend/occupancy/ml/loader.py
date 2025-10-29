# occupancy/ml/loader.py
import os, json, pickle, threading
from pathlib import Path
import keras

_LOCK = threading.Lock()
_CACHE = {}  # {("cnn_lstm_attn","gisbert_3rd_floor"): (model, preproc, meta)}

ROOT            = Path(os.getenv("MODEL_DIR", "artifacts"))
MODEL_FILE      = os.getenv("MODEL_FILE", "model.keras")
PREPROC_FILE    = os.getenv("PREPROC_FILE", "preproc.pkl")
META_FILE       = os.getenv("META_FILE", "meta.json")

def get_model_bundle(family: str, lib_key: str | None = None):
    """
    family: one of ["cnn","lstm","cnn_lstm","cnn_lstm_attn"]
    lib_key: e.g. "gisbert_3rd_floor" (omit if global model)
    """
    cache_key = (family, lib_key or "__global__")
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    with _LOCK:
        if cache_key in _CACHE:
            return _CACHE[cache_key]

        # Resolve directory: artifacts/<family>[/<lib_key>]
        base = ROOT / family
        lib_dir = base / lib_key if lib_key and (base / lib_key).exists() else base
        model = keras.models.load_model(lib_dir / MODEL_FILE, compile=False)
        with open(lib_dir / PREPROC_FILE, "rb") as f: preproc = pickle.load(f)
        with open(lib_dir / META_FILE, "r") as f: meta = json.load(f)

        _CACHE[cache_key] = (model, preproc, meta)
        return _CACHE[cache_key]
