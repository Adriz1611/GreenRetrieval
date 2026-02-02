"""Label normalization for plant disease names."""

import re
from dataclasses import dataclass
from typing import List

from .config import Config


@dataclass
class NormalizedLabel:
    """Normalized disease label with extracted components."""

    original: str
    tokens: List[str]
    host_candidates: List[str]
    symptom_candidates: List[str]
    location_terms: List[str]


def _tokenize(text: str) -> List[str]:
    """Tokenize text into words of minimum length."""
    text = (text or "").strip().lower()
    tokens = re.split(r"[^\w]+", text)
    return [t for t in tokens if len(t) >= Config.MIN_TOKEN_LEN]


def normalize_cv_label(label: str) -> NormalizedLabel:
    """Normalize a CV model's disease label.

    Args:
        label: Raw disease label from computer vision model

    Returns:
        NormalizedLabel with extracted tokens, hosts, symptoms, and locations
    """
    if not (label or isinstance(label, str)):
        return NormalizedLabel(
            original=label or "",
            tokens=[],
            host_candidates=[],
            symptom_candidates=[],
            location_terms=[],
        )

    original = label.strip()
    tokens = _tokenize(original)

    # Extract location terms BEFORE filtering
    location_terms = [t for t in tokens if t in Config.LOCATION_TERMS]

    # Filter out generic terms but keep location terms
    meaningful = [t for t in tokens if t not in Config.GENERIC_TERMS]

    if not meaningful:
        meaningful = tokens

    host_candidates = [meaningful[0]] if meaningful else []
    symptom_candidates = meaningful[1:] if len(meaningful) > 1 else meaningful

    return NormalizedLabel(
        original=original,
        tokens=meaningful,
        host_candidates=host_candidates,
        symptom_candidates=symptom_candidates,
        location_terms=location_terms,
    )