# occupancy/utils/artifacts.py
from pathlib import Path
import json
from django.conf import settings

ARTIFACTS_ROOT = Path(settings.BASE_DIR) / "artifacts"

def read_meta_version(family: str, lib_key: str) -> str | None:
    meta_p = ARTIFACTS_ROOT / family / lib_key / "meta.json"
    if not meta_p.exists():
        return None
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        v = meta.get("model_version")
        return str(v) if v is not None else None
    except Exception:
        return None
