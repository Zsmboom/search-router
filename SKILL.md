---
name: search-router
description: Unified Search Routing Layer (Multi-Provider). Routes queries to best-performing search API (Tavily/Serper/Exa), auto-rotates keys on 429/403, and provides a unified output format. Trigger: 搜索/网络查询/search
---

# Search Router — Skill Definition

## What It Does

Intelligent search router that:
1. Routes queries to the best-performing search API based on query type
2. Auto-rotates API keys on 429/403 errors
3. Falls back to next provider when current one is exhausted
4. Provides a unified output format across all providers

**Supported Providers:** Tavily · Serper · Exa

---

## Architecture

```
User Query
    │
    ▼
SearchRouter.search(query, query_type)
    │
    ├─→ routing config → ordered provider list
    │
    ├─→ TavilyProvider.search()
    │       ├─ 200 → return unified result
    │       └─ 429/403 → rotate key, retry (max retries × keys)
    │
    ├─→ SerperProvider.search()  (fallback)
    │       └─ same key rotation logic
    │
    └─→ ExaProvider.search()     (final fallback)
            └─ same key rotation logic
```

---

## Unified Output Format

All providers return the same structure:

```json
{
  "provider": "tavily",
  "query": "AI news today",
  "results": [
    {
      "title": "Article Title",
      "url": "https://example.com/article",
      "snippet": "Brief description...",
      "date": "2026-04-07",
      "score": null
    }
  ],
  "total": 10,
  "latency_ms": 342
}
```

---

## Query Types & Routing

| Query Type | Provider Order | Best For |
|------------|---------------|----------|
| `news` | Tavily → Exa → Serper | Latest news, fast facts |
| `research` | Exa → Tavily → Serper | Deep research, long-form |
| `deep` | Exa → Tavily | Comprehensive analysis |
| `google-serp` | Serper → Exa | Google SERP snapshots |
| `competitor` | Serper → Exa | Competitive analysis |
| `default` | Tavily → Exa → Serper | General queries |

---

## API Keys Configuration

### Method 1: config.json (persistent)

Edit `~/.hermes/skills/research/search-router/config.json`:

```json
{
  "providers": {
    "tavily": {
      "enabled": true,
      "keys": ["tvly-key-1", "tvly-key-2"],
      "current_key_index": 0,
      "max_retries_per_key": 2
    },
    "serper": {
      "enabled": true,
      "keys": ["serper-key-1"],
      "current_key_index": 0
    },
    "exa": {
      "enabled": true,
      "keys": ["exa-key-1"],
      "current_key_index": 0
    }
  }
}
```

### Method 2: Environment Variables (runtime injection)

```bash
export SEARCH_TAVILY_KEYS="key1,key2"
export SEARCH_SERPER_KEYS="key1"
export SEARCH_EXA_KEYS="key1"
```

### Method 3: Programmatic (runtime)

```python
router = SearchRouter()
router.add_provider_key("tavily", "new-key")
router.save_config()  # persist
```

---

## Usage

### Python API

```python
import sys
sys.path.insert(0, "~/.hermes/skills/research/search-router")

from router import SearchRouter

# Initialize
router = SearchRouter()

# Basic search (uses default routing)
result = router.search("Nvidia latest news", num_results=10)
print(f"Provider: {result['provider']}")
for r in result["results"]:
    print(f"  - {r['title']}: {r['url']}")

# Typed search (explicit routing)
result = router.search("AI research trends", query_type="research", num_results=10)

# Get results from all providers (comparison mode)
results = router.search_with_fallback("keyword analysis", query_type="default")
for r in results:
    print(f"[{r['provider']}] {r['total']} results, {r['latency_ms']}ms")

# Check provider status
status = router.provider_status()
print(status)

# Add key at runtime
router.add_provider_key("tavily", "new-key-here")
router.save_config()
```

### Shell / CLI

```bash
cd ~/.hermes/skills/research/search-router

# Set keys in environment
export SEARCH_TAVILY_KEYS="tvly-key-1,tvly-key-2"
export SEARCH_EXA_KEYS="6afd1e56-878a-4993-8fea-bfe69afe00d5"

# Run from skills directory
python router.py "AI news" news 10
```

---

## Adding New Providers

> ⚠️ **Perplexity provider 已废弃**（额度耗尽），示例仅保留结构参考。

To add a new search provider (e.g. new_provider):

1. Create `providers/new_provider.py`:

```python
class NewProviderProvider:
    name = "new_provider"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        ...

    def search(self, query: str, num_results: int = 10, **kwargs):
        # Return same unified format:
        return {
            "provider": self.name,
            "query": query,
            "results": [...],
            "total": len(results),
            "latency_ms": ms,
        }
```

2. Update `router.py`:
```python
from .providers.new_provider import NewProviderProvider

PROVIDER_CLASSES = {
    "tavily": TavilyProvider,
    "serper": SerperProvider,
    "exa": ExaProvider,
    "new_provider": NewProviderProvider,  # add here
}
```

3. Update `config.json`: add `"new_provider"` entry in `providers` and `routing` sections.

---

## Key Rotation Logic

```
For each provider:
  1. Try current key
  2. Success (200) → return result
  3. Auth error (401/403) → rotate key immediately
  4. Rate limit (429) → rotate key
  5. Other error → rotate key
  6. All keys exhausted → mark provider dead, try next provider
```

Rotation is per-provider and stateful — `current_key_index` persists across calls.

---

## Tavily Multi-Key Support

Tavily currently has 2 keys configured. The router tracks each key's index separately and rotates on any error (429/403/4xx).

To check which key is currently active:
```python
status = router.provider_status()
print(status["tavily"]["current_key_index"])
```

---

## Dependencies

```
requests
```

Install: `pip install requests`

---

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | This file — skill definition |
| `config.json` | API keys + routing configuration |
| `router.py` | Main SearchRouter class + CLI |
| `providers/__init__.py` | Provider package init |
| `providers/tavily.py` | Tavily API implementation |
| `providers/serper.py` | Serper API implementation |
| `providers/exa.py` | Exa API implementation |

---

## Notes

- Keys are stored in `config.json` in plain text — do not commit this file to version control
- Tavily does not expose quota via API; track usage manually via logs or provider_status
- Exa `search_with_contents()` method available for deep/full-text retrieval (higher latency)
- Serper supports image search via `search_images()` method
- All providers have independent key pools — rotating one does not affect others
