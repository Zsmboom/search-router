# Search Router

Hermes Agent 的多 Provider 统一搜索路由层。支持 Tavily、Serper、Exa、Brave 四种搜索 API，自动 key 轮换、智能路由、统一输出格式。

---

## 功能特性

- **智能路由** — 根据查询类型自动选择最优 Provider
- **Key 自动轮换** — 429/403 时自动切换下一个 Key
- **多 Provider 级联** — 主 Provider 失败时自动降级到下一个
- **统一输出格式** — 所有 Provider 返回相同结构
- **多 Key 支持** — 每个 Provider 可配置多个 Key

## 支持的 Provider

| Provider | 适用场景 | Key 获取 |
|----------|---------|---------|
| **Tavily** | 综合搜索、新闻、研究 | [tavily.com](https://tavily.com) |
| **Serper** | Google SERP 快照、竞品分析 | [serper.dev](https://serper.dev) |
| **Exa** | 深度研究、长文检索 | [exa.ai](https://exa.ai) |
| **Brave** | 通用搜索、安全隐私 | [brave.com/search/api](https://brave.com/search/api) |

---

## 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 配置 API Keys

复制模板文件并填入你的 Key：

```bash
cp config.json.template config.json
```

编辑 `config.json`：

```json
{
  "providers": {
    "tavily": {
      "enabled": true,
      "keys": [
        "tvly-YOUR-KEY-HERE"
      ],
      "current_key_index": 0
    },
    "serper": {
      "enabled": true,
      "keys": [
        "YOUR-SERPER-KEY-HERE"
      ],
      "current_key_index": 0
    },
    "exa": {
      "enabled": true,
      "keys": [
        "YOUR-EXA-KEY-HERE"
      ],
      "current_key_index": 0
    },
    "brave": {
      "enabled": true,
      "keys": [
        "YOUR-BRAVE-KEY-HERE"
      ],
      "current_key_index": 0
    }
  }
}
```

> ⚠️ **不要提交 config.json** — 已加入 .gitignore

### 3. 使用

#### Python API

```python
import sys
sys.path.insert(0, "/path/to/search-router")

from router import SearchRouter

router = SearchRouter()

# 基础搜索（使用默认路由）
result = router.search("AI news today", num_results=10)
print(f"Provider: {result['provider']}")
for r in result["results"]:
    print(f"  - {r['title']}: {r['url']}")

# 指定查询类型（显式路由）
result = router.search("AI research trends", query_type="research", num_results=10)

# 获取所有 Provider 结果（对比模式）
results = router.search_with_fallback("keyword analysis")
for r in results:
    print(f"[{r['provider']}] {r['total']} results, {r['latency_ms']}ms")

# 查看 Provider 状态
status = router.provider_status()
print(status)

# 运行时添加 Key
router.add_provider_key("tavily", "new-key-here")
router.save_config()
```

#### Shell / CLI

```bash
cd /path/to/search-router

# 单次搜索
python router.py "AI news" news 10

# 参数：<查询词> <查询类型> <结果数量>
# 查询类型：news, research, deep, google-serp, competitor, default
```

---

## 查询类型与路由规则

| 查询类型 | 路由顺序 | 最佳场景 |
|----------|---------|---------|
| `news` | Tavily → Exa → Serper | 最新新闻、快速事实 |
| `research` | Exa → Tavily → Serper | 深度研究、长文分析 |
| `deep` | Exa → Tavily | 综合分析、全面检索 |
| `google-serp` | Serper → Exa | Google SERP 快照 |
| `competitor` | Serper → Exa | 竞品分析 |
| `default` | Tavily → Exa → Serper → Brave | 通用查询 |

---

## 统一输出格式

所有 Provider 返回相同结构：

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

## Key 轮换逻辑

```
For each provider:
  1. 使用当前 Key 请求
  2. 成功 (200) → 返回结果
  3. 认证错误 (401/403) → 立即切换下一个 Key
  4. 频率限制 (429) → 切换下一个 Key
  5. 其他错误 → 切换下一个 Key
  6. 所有 Key 用尽 → 标记 Provider 失效，尝试下一个 Provider
```

---

## 添加新 Provider

1. 创建 `providers/your_provider.py`：

```python
class YourProviderProvider:
    name = "your_provider"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        ...

    def search(self, query: str, num_results: int = 10, **kwargs):
        return {
            "provider": self.name,
            "query": query,
            "results": [...],
            "total": len(results),
            "latency_ms": ms,
        }
```

2. 更新 `router.py` 中的 `PROVIDER_CLASSES`

3. 在 `config.json` 中添加 Provider 配置

---

## 文件结构

```
search-router/
├── SKILL.md              # Skill 定义文档
├── README.md             # 本文件
├── config.json.template  # Key 配置模板
├── router.py             # 主程序 + CLI
└── providers/
    ├── __init__.py
    ├── tavily.py         # Tavily 实现
    ├── serper.py         # Serper 实现
    ├── exa.py            # Exa 实现
    └── brave.py          # Brave 实现
```

---

## 注意事项

- `config.json` 包含敏感 Key，已加入 .gitignore，切勿提交
- Tavily 不暴露配额信息，请通过日志或 `provider_status()` 手动跟踪
- Exa 支持 `search_with_contents()` 方法获取全文（延迟更高）
- Serper 支持 `search_images()` 图片搜索
- 各 Provider Key 池独立，轮换互不影响
