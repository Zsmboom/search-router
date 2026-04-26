"""
Brave Search Provider
API: https://api.search.brave.com/res/v1/web/search
"""

import requests
import time


class BraveProvider:
    name = "brave"
    base_url = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        self.current_key_index = config.get("current_key_index", 0)
        self.max_retries = config.get("max_retries_per_key", 2)

    def _get_current_key(self):
        if not self.keys:
            raise RuntimeError("No Brave Search API key available")
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
                resp = requests.get(
                    self.base_url,
                    headers={
                        "X-Subscription-Token": api_key,
                        "Accept": "application/json",
                    },
                    params={
                        "q": query,
                        "count": min(num_results, 20),
                        "offset": kwargs.get("offset", 0),
                        "safesearch": kwargs.get("safesearch", "moderate"),
                    },
                    timeout=kwargs.get("timeout", 15),
                )

                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("web", {}).get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("description", ""),
                            "date": item.get("age", ""),
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

        raise RuntimeError(f"Brave all keys failed: {last_error}")
