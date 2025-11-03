# occupancy/utils/active.py
from typing import Tuple, Optional
from django.db.models import Prefetch
from ..models import ActiveModel, ModelCandidate, Library

DEFAULT_FAMILY = "cnn_lstm_attn"
DEFAULT_VERSION = "v1"

def get_active_family_version(library: Library) -> Tuple[str, str]:
    """
    Return (family, version) for the library's active model.
    Fallbacks:
      1) ActiveModel → its candidate
      2) First candidate row (latest created)
      3) Hard defaults (cnn_lstm_attn, v1)
    """
    # 1) Active row
    try:
        am = (ActiveModel.objects
              .select_related("candidate")
              .get(library=library))
        if am.candidate:
            return am.candidate.family, am.candidate.version
    except ActiveModel.DoesNotExist:
        pass

    # 2) Any candidate
    row = (ModelCandidate.objects
           .filter(library=library)
           .order_by("-created_at")
           .first())
    if row:
        return row.family, row.version

    # 3) Hard default
    return DEFAULT_FAMILY, DEFAULT_VERSION