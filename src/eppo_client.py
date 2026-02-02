"""EPPO API client for fetching plant disease data."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .config import Config


class EPPOClient:
    """Client for EPPO Global Database API."""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        cache_dir: Path = None,
        use_cache: bool = True,
    ):
        """Initialize EPPO client.

        Args:
            api_key: EPPO API key (defaults to Config.EPPO_API_KEY)
            base_url: Base URL for API (defaults to Config.EPPO_BASE_URL)
            cache_dir: Directory for caching responses (defaults to Config.EPPO_CACHE_DIR)
            use_cache: Whether to use caching
        """
        self.api_key = api_key or Config.EPPO_API_KEY
        self.base_url = base_url or Config.EPPO_BASE_URL
        self.cache_dir = cache_dir or Config.EPPO_CACHE_DIR
        self.use_cache = use_cache

        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0

    def _load_cached(self, eppocode: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """Load cached response from disk."""
        if not self.use_cache:
            return None

        cache_file = self.cache_dir / "taxons" / eppocode / f"{endpoint}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_cached(self, eppocode: str, endpoint: str, data: Any):
        """Save response to cache."""
        if not self.use_cache:
            return

        cache_file = self.cache_dir / "taxons" / eppocode / f"{endpoint}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _get_endpoint(
        self, eppocode: str, endpoint: str, max_retries: int = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch data from EPPO API endpoint with retries.

        Args:
            eppocode: EPPO code to fetch
            endpoint: API endpoint (e.g., 'overview', 'names', 'hosts')
            max_retries: Maximum retry attempts

        Returns:
            JSON response data or None on failure
        """
        if max_retries is None:
            max_retries = Config.EPPO_MAX_RETRIES

        # Check cache first
        cached = self._load_cached(eppocode, endpoint)
        if cached is not None:
            self.cache_hits += 1
            return cached

        # Make API request
        url = f"{self.base_url.rstrip('/')}/taxons/taxon/{eppocode}/{endpoint}"
        headers = {"X-Api-Key": self.api_key} if self.api_key else {}

        for attempt in range(max_retries):
            try:
                self.cache_misses += 1
                self.api_calls += 1
                time.sleep(Config.EPPO_RATE_LIMIT_DELAY)

                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                # Cache successful response
                if data is not None:
                    self._save_cached(eppocode, endpoint, data)

                return data

            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    time.sleep(0.5 * (2**attempt))
                    continue
                return None

        return None

    def fetch_facts(self, eppocode: str) -> Dict[str, Any]:
        """Fetch all relevant facts for an EPPO code.

        Args:
            eppocode: EPPO code to fetch

        Returns:
            Dictionary with overview, names, and hosts data
        """
        overview = self._get_endpoint(eppocode, "overview")
        names = self._get_endpoint(eppocode, "names")
        hosts = self._get_endpoint(eppocode, "hosts")

        return {
            "overview": overview,
            "names": names if isinstance(names, list) else [],
            "hosts": hosts if isinstance(hosts, list) else [],
        }

    def get_stats(self) -> Dict[str, int]:
        """Get client statistics.

        Returns:
            Dictionary with cache_hits, cache_misses, and api_calls
        """
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "api_calls": self.api_calls,
        }