"""Validation of EPPO data against disease labels."""

import re
from typing import Any, Dict, List, Set

from .normalization import NormalizedLabel


def _tokenize_text(text: str) -> Set[str]:
    """Tokenize text into set of tokens."""
    tokens = re.split(r"[^\w]+", (text or "").lower())
    return {t for t in tokens if len(t) >= 2}


def _texts_from_facts(facts: Dict[str, Any]) -> List[str]:
    """Extract all text strings from EPPO facts.

    Args:
        facts: Dictionary with overview, names, and hosts data

    Returns:
        List of text strings to validate against
    """
    texts: List[str] = []

    overview = facts.get("overview") or {}
    if isinstance(overview, dict):
        prefname = overview.get("prefname")
        if prefname:
            texts.append(prefname)

    for name_entry in facts.get("names") or []:
        if isinstance(name_entry, dict) and name_entry.get("fullname"):
            texts.append(name_entry["fullname"])

    for host_entry in facts.get("hosts") or []:
        if isinstance(host_entry, dict) and host_entry.get("prefname"):
            texts.append(host_entry["prefname"])

    return texts


def validate_eppo_against_label(
    facts: Dict[str, Any], norm: NormalizedLabel, min_token_overlap: int = 1
) -> bool:
    """Validate that EPPO facts support the normalized label.

    Args:
        facts: EPPO facts dictionary
        norm: Normalized label
        min_token_overlap: Minimum number of overlapping tokens required

    Returns:
        True if validation passes, False otherwise
    """
    if not facts or not norm.tokens:
        return False

    overview = facts.get("overview")
    if not overview or not isinstance(overview, dict):
        return False

    texts = _texts_from_facts(facts)
    if not texts:
        return False

    label_tokens = set(norm.tokens)
    combined = " ".join(texts).lower()
    combined_tokens = _tokenize_text(combined)
    overlap = len(label_tokens & combined_tokens)

    return overlap >= min_token_overlap