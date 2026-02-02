"""Main diagnosis pipeline."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config
from .eppo_client import EPPOClient
from .generation import ResponseGenerator
from .normalization import normalize_cv_label
from .retrieval import query_candidates, select_best
from .validation import validate_eppo_against_label

# Refusal messages
REFUSAL_NO_CANDIDATES = (
    "I cannot verify this diagnosis: no matching EPPO record was found for this label."
)
REFUSAL_LOW_CONFIDENCE = (
    "I cannot verify this diagnosis: the match to EPPO data is too uncertain."
)
REFUSAL_EPPO_FAILED = (
    "I cannot verify this diagnosis: EPPO data could not be retrieved."
)
REFUSAL_VALIDATION_FAILED = (
    "I cannot verify this diagnosis: the retrieved EPPO data does not support this label."
)


@dataclass
class DiagnosisResult:
    """Result of a disease diagnosis."""

    refused: bool
    message: str
    eppocode: Optional[str] = None
    confidence: Optional[float] = None


def diagnose(
    cv_label: str,
    sqlite_path: Optional[Path] = None,
    cache_dir: Optional[Path] = None,
    confidence_threshold: float = None,
    eppo_client: Optional[EPPOClient] = None,
    generator: Optional[ResponseGenerator] = None,
) -> DiagnosisResult:
    """Diagnose a plant disease from a CV model label.

    Args:
        cv_label: Disease label from computer vision model
        sqlite_path: Path to SQLite database (defaults to Config.SQLITE_PATH)
        cache_dir: Cache directory (defaults to Config.EPPO_CACHE_DIR)
        confidence_threshold: Minimum confidence threshold (defaults to Config.CONFIDENCE_THRESHOLD)
        eppo_client: EPPO client instance (creates new if None)
        generator: Response generator instance (creates new if None)

    Returns:
        DiagnosisResult with diagnosis information
    """
    # Set defaults
    sqlite_path = sqlite_path or Config.SQLITE_PATH
    cache_dir = cache_dir or Config.EPPO_CACHE_DIR
    confidence_threshold = confidence_threshold or Config.CONFIDENCE_THRESHOLD

    # Initialize clients if not provided
    if eppo_client is None:
        eppo_client = EPPOClient(cache_dir=cache_dir)
    if generator is None:
        generator = ResponseGenerator()

    # Step 1: Normalize label
    norm = normalize_cv_label(cv_label)
    if not norm.tokens:
        return DiagnosisResult(refused=True, message=REFUSAL_NO_CANDIDATES)

    # Step 2: Query candidates
    candidates = query_candidates(sqlite_path, norm)

    # Step 3: Select best candidate
    best = select_best(candidates, confidence_threshold)
    if best is None:
        return DiagnosisResult(
            refused=True,
            message=REFUSAL_LOW_CONFIDENCE,
            confidence=candidates[0].score if candidates else None,
        )

    # Step 4: Fetch EPPO facts
    facts = eppo_client.fetch_facts(best.eppocode)
    if not facts.get("overview"):
        return DiagnosisResult(
            refused=True,
            message=REFUSAL_EPPO_FAILED,
            eppocode=best.eppocode,
        )

    # Step 5: Validate facts against label
    if not validate_eppo_against_label(facts, norm, min_token_overlap=1):
        return DiagnosisResult(
            refused=True,
            message=REFUSAL_VALIDATION_FAILED,
            eppocode=best.eppocode,
        )

    # Step 6: Generate response
    answer = generator.generate(cv_label, facts)
    return DiagnosisResult(
        refused=False,
        message=answer,
        eppocode=best.eppocode,
        confidence=best.score,
    )