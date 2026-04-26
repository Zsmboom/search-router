"""
Tavily Search Provider
API: https://api.tavily.com/search
"""

import requests
import time


class TavilyProvider:
    name = "tavily"
    base_url = "https://api.tavily.com/search"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        self.current_key_index = config.get("current_key_index", 0)
        self.max_retries = config.get("max_retries_per_key", 2)

    def _get_current_key(self):
        if not self.keys:
            raise RuntimeError("No Tavily API key available")
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
                resp = requests.post(
                    self.base_url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": kwargs.get("search_depth", "basic"),
                        "num_results": num_results,
                        "include_answer": kwargs.get("include_answer", False),
                        "include_raw_content": False,
                        "include_domains": kwargs.get("include_domains", []),
                        "exclude_domains": kwargs.get("exclude_domains", []),
                    },
                    timeout=kwargs.get("timeout", 15),
                )

                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                            "date": item.get("published_date", ""),
                        })
                    return {
                        "provider": self.name,
                        "query": query,
                        "results": results,
                        "total": len(results),
                        "latency_ms": int((time.time() - start) * 1000),
                    }

                elif resp.status_code in (401, 403):
                    # Bad key — rotate immediately
                    self._rotate_key()
                    last_error = f"Auth error ({resp.status_code}), rotating key"
                    continue

                elif resp.status_code == 429:
                    # Quota exceeded — rotate
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

        raise RuntimeError(f"Tavily all keys failed: {last_error}")

    def get_quota(self, api_key: str = None):
        """Check quota for a specific key (if available from Tavily)."""
        key = api_key or self._get_current_key()
        # Tavily doesn't expose quota via API — caller should track usage
        return None
