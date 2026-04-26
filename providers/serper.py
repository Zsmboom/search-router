"""
Serper (Google Serper API) Search Provider
API: https://google.serper.dev/search
"""

import requests
import time


class SerperProvider:
    name = "serper"
    base_url = "https://google.serper.dev/search"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        self.current_key_index = config.get("current_key_index", 0)
        self.max_retries = config.get("max_retries_per_key", 2)

    def _get_current_key(self):
        if not self.keys:
            raise RuntimeError("No Serper API key available")
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
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "num": num_results,
                        "gl": kwargs.get("gl", "us"),
                        "hl": kwargs.get("hl", "en"),
                        "autocorrect": kwargs.get("autocorrect", True),
                    },
                    timeout=kwargs.get("timeout", 15),
                )

                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("organic", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "date": item.get("date", ""),
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

        raise RuntimeError(f"Serper all keys failed: {last_error}")

    def search_images(self, query: str, num_results: int = 10, **kwargs):
        """Image search endpoint."""
        start = time.time()
        last_error = None

        for attempt in range(len(self.keys) * (self.max_retries + 1)):
            api_key = self._get_current_key()
            try:
                resp = requests.post(
                    "https://google.serper.dev/images",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": num_results},
                    timeout=kwargs.get("timeout", 15),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("images", []):
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("imageUrl", ""),
                            "source": item.get("source", ""),
                        })
                    return {
                        "provider": self.name,
                        "type": "images",
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

        raise RuntimeError(f"Serper image search all keys failed: {last_error}")
