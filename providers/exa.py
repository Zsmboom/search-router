"""
Exa Search Provider
API: https://api.exa.ai/search
"""

import requests
import time


class ExaProvider:
    name = "exa"
    base_url = "https://api.exa.ai/search"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        self.current_key_index = config.get("current_key_index", 0)
        self.max_retries = config.get("max_retries_per_key", 2)

    def _get_current_key(self):
        if not self.keys:
            raise RuntimeError("No Exa API key available")
        return self.keys[self.current_key_index % len(self.keys)]

    def _rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)

    def search(self, query: str, num_results: int = 10, **kwargs):
        """
        Returns: dict with {provider, query, results, total, latency_ms}
        """
        start = time.time()
        last_error = None

        for attempt in range(len(self.keys) * (self.max_retries + 1)):
            api_key = self._get_current_key()

            try:
                # Exa highlights: max 4000 chars total across all results
                payload = {
                    "query": query,
                    "numResults": num_results,
                    "type": kwargs.get("type", "auto"),
                    "contents": {
                        "highlights": {
                            "maxCharacters": kwargs.get("max_chars", 4000),
                            "includeSubpages": False,
                        }
                    },
                }

                # Optional filters
                if kwargs.get("category"):
                    payload["category"] = kwargs["category"]
                if kwargs.get("start_published_date"):
                    payload["startPublishedDate"] = kwargs["start_published_date"]
                if kwargs.get("end_published_date"):
                    payload["endPublishedDate"] = kwargs["end_published_date"]

                resp = requests.post(
                    self.base_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    },
                    json=payload,
                    timeout=kwargs.get("timeout", 20),
                )

                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("highlight", item.get("text", "")),
                            "date": item.get("published-date", item.get("publishedDate", "")),
                            "score": item.get("score", None),
                        })
                    return {
                        "provider": self.name,
                        "query": query,
                        "results": results,
                        "total": len(results),
                        "latency_ms": int((time.time() - start) * 1000),
                    }

                elif resp.status_code in (401, 403):
                    self._rotate_key()
                    last_error = f"Auth error ({resp.status_code}), rotating key"
                    continue

                elif resp.status_code == 429:
                    self._rotate_key()
                    last_error = "Rate limit (429), rotating key"
                    continue

                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    self._rotate_key()
                    continue

            except Exception as e:
                last_error = str(e)
                self._rotate_key()
                continue

        raise RuntimeError(f"Exa all keys failed: {last_error}")

    def search_with_contents(self, query: str, num_results: int = 5, **kwargs):
        """Deep search with full content (more tokens, slower)."""
        start = time.time()
        last_error = None

        for attempt in range(len(self.keys) * (self.max_retries + 1)):
            api_key = self._get_current_key()
            try:
                payload = {
                    "query": query,
                    "numResults": num_results,
                    "type": "auto",
                    "contents": {
                        "text": {
                            "maxCharacters": kwargs.get("max_chars", 3000),
                        },
                        "highlights": {
                            "maxCharacters": kwargs.get("max_chars", 4000),
                        }
                    },
                }
                resp = requests.post(
                    self.base_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    },
                    json=payload,
                    timeout=kwargs.get("timeout", 30),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("text", ""),
                            "date": item.get("published-date", ""),
                        })
                    return {
                        "provider": self.name,
                        "type": "deep",
                        "query": query,
                        "results": results,
                        "total": len(results),
                        "latency_ms": int((time.time() - start) * 1000),
                    }
                elif resp.status_code in (401, 403, 429):
                    self._rotate_key()
                    last_error = f"HTTP {resp.status_code}, rotating key"
                    continue
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    self._rotate_key()
                    continue
            except Exception as e:
                last_error = str(e)
                self._rotate_key()
                continue

        raise RuntimeError(f"Exa deep search all keys failed: {last_error}")
