"""Configuration management for GreenRetrieval."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration settings for GreenRetrieval pipeline."""

    # Paths
    SQLITE_PATH: Path = Path(os.environ.get("EPPO_SQLITE_PATH", "eppocodes_all.sqlite"))
    EPPO_CACHE_DIR: Path = Path(os.environ.get("EPPO_CACHE_DIR", ".eppo_cache"))

    # API Keys
    EPPO_API_KEY: str = os.environ.get("EPPO_API_KEY", "")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")

    # EPPO API Configuration
    EPPO_BASE_URL: str = "https://api.eppo.int/gd/v2"
    EPPO_RATE_LIMIT_DELAY: float = 0.2
    EPPO_MAX_RETRIES: int = 3

    # Retrieval Configuration
    CONFIDENCE_THRESHOLD: float = 0.3
    MAX_CANDIDATES: int = 50

    # Groq LLM Configuration
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.3

    # Normalization
    MIN_TOKEN_LEN: int = 2
    GENERIC_TERMS = frozenset({
        "of", "the", "and", "on", "in", "plant", "plants", "crop", "crops",
    })
    LOCATION_TERMS = frozenset({
        "leaf", "leaves", "stem", "stems", "fruit", "fruits", "root", "roots",
        "seed", "seeds", "flower", "flowers", "bark", "shoot", "branch",
    })
    SYMPTOM_SYNONYMS = {
        "blight": {"blight", "spot", "lesion", "necrosis"},
        "rust": {"rust", "uredinia", "pustule"},
        "mosaic": {"mosaic", "mottle", "pattern", "variegation"},
        "rot": {"rot", "decay", "decomposition"},
        "wilt": {"wilt", "wilting", "droop", "collapse"},
        "curl": {"curl", "curling", "distortion", "deformation"},
    }

    # Retrieval Scoring
    PREFERRED_DTCODE: str = "GAF"
    SECONDARY_DTCODES = frozenset({"SFT"})
    HOST_BONUS: float = 0.2
    LOCATION_BONUS_MULTIPLIER: float = 0.3
    DTCODE_BONUS_PRIMARY: float = 0.15
    DTCODE_BONUS_SECONDARY: float = 0.05
    MAX_SCORE_CAP: float = 1.5

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls()

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.SQLITE_PATH.exists():
            raise FileNotFoundError(f"SQLite database not found at {cls.SQLITE_PATH}")
        if not cls.EPPO_API_KEY:
            raise ValueError("EPPO_API_KEY environment variable not set")
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable not set")
        return True