"""SQLite database retrieval for EPPO codes."""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .config import Config
from .normalization import NormalizedLabel


@dataclass
class Candidate:
    """Candidate EPPO code with matching score."""

    eppocode: str
    dtcode: str
    fullname: str
    score: float
    token_overlap: int
    host_match: bool


def _tokenize_name(name: str) -> set:
    """Tokenize a name into a set of tokens."""
    tokens = re.split(r"[^\w]+", (name or "").lower())
    return {t for t in tokens if len(t) >= 2}


def _score_candidate(
    eppocode: str, dtcode: str, fullname: str, norm: NormalizedLabel
) -> Tuple[float, int, bool]:
    """Score a candidate based on token overlap and other factors.

    Args:
        eppocode: EPPO code
        dtcode: Data type code
        fullname: Full name from database
        norm: Normalized label

    Returns:
        Tuple of (score, token_overlap, host_match)
    """
    name_tokens = _tokenize_name(fullname)
    query_tokens = set(norm.tokens)
    overlap = len(query_tokens & name_tokens)
    host_match = bool(
        norm.host_candidates and (set(norm.host_candidates) & name_tokens)
    )

    # Check if location terms match
    location_match = 0
    if norm.location_terms:
        location_tokens = set(norm.location_terms)
        location_match = len(location_tokens & name_tokens) / len(location_tokens)

    query_len = max(len(query_tokens), 1)
    overlap_ratio = overlap / query_len
    host_bonus = Config.HOST_BONUS if host_match else 0.0
    location_bonus = Config.LOCATION_BONUS_MULTIPLIER * location_match
    dtcode_bonus = (
        Config.DTCODE_BONUS_PRIMARY
        if dtcode == Config.PREFERRED_DTCODE
        else (
            Config.DTCODE_BONUS_SECONDARY
            if dtcode in Config.SECONDARY_DTCODES
            else 0.0
        )
    )

    score = overlap_ratio + host_bonus + location_bonus + dtcode_bonus
    return (min(score, Config.MAX_SCORE_CAP), overlap, host_match)


def query_candidates(
    sqlite_path: Path, norm: NormalizedLabel, max_candidates: int = None
) -> List[Candidate]:
    """Query SQLite database for candidate EPPO codes.

    Args:
        sqlite_path: Path to SQLite database
        norm: Normalized label
        max_candidates: Maximum number of candidates to return

    Returns:
        List of Candidate objects sorted by score
    """
    if max_candidates is None:
        max_candidates = Config.MAX_CANDIDATES

    if not norm.tokens or not sqlite_path.exists():
        return []

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        placeholders = " OR ".join(["n.fullname LIKE ?" for _ in norm.tokens])
        params = [f"%{t}%" for t in norm.tokens]

        sql = f"""
            SELECT DISTINCT c.eppocode, c.dtcode, n.fullname
            FROM t_codes c
            JOIN t_names n ON c.codeid = n.codeid
            WHERE c.status = 'A' AND n.status = 'A'
              AND ({placeholders})
        """
        cur = conn.execute(sql, params)
        rows = list(cur.fetchall())
    finally:
        conn.close()

    query_tokens_set = set(norm.tokens)
    by_code: dict[Tuple[str, str], str] = {}
    for row in rows:
        key = (row["eppocode"], row["dtcode"])
        name = row["fullname"] or ""
        name_tokens = _tokenize_name(name)
        overlap = len(query_tokens_set & name_tokens)
        prev_name = by_code.get(key, "")
        prev_overlap = (
            len(query_tokens_set & _tokenize_name(prev_name)) if prev_name else -1
        )
        if key not in by_code or overlap > prev_overlap or (
            overlap == prev_overlap and len(name) > len(prev_name)
        ):
            by_code[key] = name

    candidates: List[Candidate] = []
    for (eppocode, dtcode), fullname in by_code.items():
        score, token_overlap, host_match = _score_candidate(
            eppocode, dtcode, fullname, norm
        )
        candidates.append(
            Candidate(
                eppocode=eppocode,
                dtcode=dtcode,
                fullname=fullname,
                score=score,
                token_overlap=token_overlap,
                host_match=host_match,
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:max_candidates]


def select_best(
    candidates: List[Candidate], threshold: float = None
) -> Optional[Candidate]:
    """Select the best candidate above threshold.

    Args:
        candidates: List of candidates
        threshold: Minimum score threshold

    Returns:
        Best candidate or None if no candidate meets threshold
    """
    if threshold is None:
        threshold = Config.CONFIDENCE_THRESHOLD

    if not candidates:
        return None
    best = candidates[0]
    return best if best.score >= threshold else None