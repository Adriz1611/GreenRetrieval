"""GreenRetrieval - AI-powered plant disease diagnosis using EPPO database and Groq LLM."""

__version__ = "1.0.0"

from .pipeline import diagnose, DiagnosisResult
from .normalization import normalize_cv_label, NormalizedLabel
from .config import Config

__all__ = [
    "diagnose",
    "DiagnosisResult",
    "normalize_cv_label",
    "NormalizedLabel",
    "Config",
]