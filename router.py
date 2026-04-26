"""
Search Router — intelligent multi-provider search routing

Supports: Tavily, Serper, Exa
Auto-rotates keys on 429/403, falls back to next provider on exhaustion.
"""

import json
import os
import time
from typing import Optional

# Import providers
try:
    from .providers.tavily import TavilyProvider
    from .providers.serper import SerperProvider
    from .providers.exa import ExaProvider
    from .providers.brave import BraveProvider
except ImportError:
    from providers.tavily import TavilyProvider
    from providers.serper import SerperProvider
    from providers.exa import ExaProvider
    from providers.brave import BraveProvider


class SearchRouter:
    """
    Unified search interface with intelligent routing and key rotation.

    Usage:
        router = SearchRouter(config_path="config.json")
        result = router.search("AI news", query_type="news")
    """

    PROVIDER_CLASSES = {
        "tavily": TavilyProvider,
        "serper": SerperProvider,
        "exa": ExaProvider,
        "brave": BraveProvider,
    }

    def __init__(self, config_path: str = None, config: dict = None):
        if config:
            self.config = config
        elif config_path:
            with open(config_path) as f:
                self.config = json.load(f)
        else:
            default_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(default_path) as f:
                self.config = json.load(f)

        self.providers = {}
        self._init_providers()
        self._load_keys_from_env()

    def _init_providers(self):
        for name, cfg in self.config.get("providers", {}).items():
            if name not in self.PROVIDER_CLASSES:
                continue
            cls = self.PROVIDER_CLASSES[name]
            self.providers[name] = cls(
                keys=cfg.get("keys", []),
                config=cfg,
            )

    def _load_keys_from_env(self):
        """Allow API keys to be injected via environment variables."""
        for name in self.PROVIDER_CLASSES:
            env_key = f"SEARCH_{name.upper()}_KEYS"
            env_val = os.environ.get(env_key, "")
            if env_val:
                keys = [k.strip() for k in env_val.split(",") if k.strip()]
                if name in self.providers:
                    self.providers[name].keys.extend(keys)
                else:
                    cfg = self.config.get("providers", {}).get(name, {})
                    self.PROVIDER_CLASSES[name](keys=keys, config=cfg)

    def _get_provider_order(self, query_type: str) -> list:
        """Return ordered list of providers to try for this query type."""
        routing = self.config.get("routing", {})
        fallback = self.config.get("fallback_order", [])

        # Normalize query_type
        qtype = query_type.lower().strip() if query_type else "default"
        if qtype not in routing:
            qtype = "default"

        order = routing.get(qtype, fallback)
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for p in order:
            if p not in seen and p in self.providers:
                cfg = self.config["providers"].get(p, {})
                if cfg.get("enabled", True):
                    seen.add(p)
                    deduped.append(p)
        return deduped

    def search(
        self,
        query: str,
        query_type: str = "default",
        num_results: int = 10,
        **kwargs
    ) -> dict:
        """
        Main entry point. Tries providers in routing order.

        Args:
            query: Search query string
            query_type: One of "news", "research", "deep", "google-serp", "competitor", "default"
            num_results: Number of results to return

        Returns:
            Unified result dict: {provider, query, results, total, latency_ms}
        """
        start = time.time()
        provider_order = self._get_provider_order(query_type)

        if not provider_order:
            raise RuntimeError(f"No providers available for query type: {query_type}")

        tried_providers = []

        for provider_name in provider_order:
            provider = self.providers[provider_name]
            tried_providers.append(provider_name)

            if not provider.keys:
                continue

            try:
                result = provider.search(query, num_results=num_results, **kwargs)
                return result

            except RuntimeError as e:
                # Provider exhausted all keys — move to next
                err_msg = str(e)
                print(f"[SearchRouter] {provider_name} exhausted: {err_msg}")
                continue

            except Exception as e:
                print(f"[SearchRouter] {provider_name} error: {e}")
                continue

        raise RuntimeError(
            f"All providers failed for query '{query}' (type={query_type}). "
            f"Tried: {tried_providers}"
        )

    def search_with_fallback(
        self,
        query: str,
        query_type: str = "default",
        num_results: int = 10,
        **kwargs
    ) -> list:
        """
        Try all providers and return results from all that succeed.
        Useful for comparison / aggregate results.
        """
        provider_order = self._get_provider_order(query_type)
        results = []

        for provider_name in provider_order:
            provider = self.providers[provider_name]
            if not provider.keys:
                continue
            try:
                result = provider.search(query, num_results=num_results, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"[SearchRouter] {provider_name} fallback failed: {e}")
                continue

        return results

    def provider_status(self) -> dict:
        """Return status of all providers (for debugging/health checks)."""
        status = {}
        for name, provider in self.providers.items():
            cfg = self.config.get("providers", {}).get(name, {})
            status[name] = {
                "enabled": cfg.get("enabled", True),
                "keys_count": len(provider.keys),
                "current_key_index": provider.current_key_index,
            }
        return status

    def add_provider_key(self, provider_name: str, key: str):
        """Dynamically add a key to a provider at runtime."""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        if key not in self.providers[provider_name].keys:
            self.providers[provider_name].keys.append(key)
            # Also update config so it persists
            if "keys" not in self.config["providers"][provider_name]:
                self.config["providers"][provider_name]["keys"] = []
            if key not in self.config["providers"][provider_name]["keys"]:
                self.config["providers"][provider_name]["keys"].append(key)

    def save_config(self, path: str = None):
        """Persist current config (including added keys) to file."""
        target = path or os.path.join(os.path.dirname(__file__), "config.json")
        with open(target, "w") as f:
            json.dump(self.config, f, indent=2)


# CLI entry point
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python router.py <query> [query_type] [num_results]")
        print("  query_type: news | research | deep | google-serp | competitor | default")
        sys.exit(1)

    query = sys.argv[1]
    query_type = sys.argv[2] if len(sys.argv) > 2 else "default"
    num_results = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    router = SearchRouter(config_path=config_path)

    print(f"\n=== SearchRouter: '{query}' (type={query_type}) ===\n")
    result = router.search(query, query_type=query_type, num_results=num_results)
    print(f"Provider: {result['provider']}")
    print(f"Latency: {result['latency_ms']}ms")
    print(f"Results: {result['total']}\n")
    for i, r in enumerate(result["results"], 1):
        print(f"{i}. {r['title']}")
        print(f"   {r['url']}")
        print(f"   {r['snippet'][:150]}...")
        print()
