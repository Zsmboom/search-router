# Search Router

多 Provider 统一搜索路由层。**你只管搜，路由、降级、Key 轮换全自动。**

> 纯 Python 3 实现，零 Agent 框架依赖。任何能跑 Python 3 的 Agent 都能用。

---

## 解决的问题

用 AI Agent 做搜索时，最烦的不是搜不到，而是**该用哪个搜索工具**：

| 场景 | 最佳工具 |
|------|---------|
| 搜新闻快讯 | Tavily（速度快） |
| 查 Google 排名 | Serper（接近 Google 原始结果） |
| 深度研究 | Exa（全文检索，支持长文） |
| 通用查询 | Brave / 任意 |

但来回切换、记 API Key、管配额——累。Search Router 解决的就是这个问题：**你只管搜，剩下的它自动安排。**

### 核心能力

- **智能路由** — 根据查询类型自动选最优 Provider
- **Key 自动轮换** — 429/403 时自动换下一个 Key，不卡壳
- **多 Provider 级联** — 主 Provider 用尽配额，自动降级到下一个
- **统一输出格式** — 不管用哪个 Provider，返回结构都一样
- **环境变量注入** — 不配 config 文件也能用
- **运行时加 Key** — 不用重启，`add_provider_key()` 即加即用

---

## 快速开始

### 1. 克隆

```bash
git clone https://github.com/Zsmboom/search-router.git
cd search-router
```

### 2. 安装依赖

```bash
pip install requests
```

> 唯一依赖，无其他第三方库。

### 3. 配置 API Key

```bash
cp config.json.template config.json
```

编辑 `config.json`，至少启用一个 Provider：

```json
{
  "providers": {
    "tavily": {
      "enabled": true,
      "keys": ["tvly-YOUR-KEY-HERE"]
    }
  }
}
```

> ⚠️ `config.json` 已加入 `.gitignore`，**切勿提交**。

---

## API Key 获取

| Provider | 注册地址 | 免费额度 | 最佳用途 |
|----------|---------|---------|---------|
| **Tavily** | [tavily.com](https://tavily.com) | 1000次/天 | 综合搜索、新闻快讯、通用查询 |
| **Serper** | [serper.dev](https://serper.dev) | 2500次/月 | Google SERP 快照、竞品分析、SEO |
| **Exa** | [exa.ai](https://exa.ai) | 1000次/月 | 深度研究、长文检索、学术 |
| **Brave** | [brave.com/search/api](https://brave.com/search/api) | 2000次/月 | 通用搜索、隐私优先场景 |

**最少配一个就能用**（Tavily 推荐首选）。配多个有级联容灾——Tavily 用尽自动切 Exa。

---

## 在 Agent 中使用

### Hermes Agent

作为 skill 加载后自动路由，或通过 terminal 调用：

```bash
# 作为 skill 触发（加载 search-router skill 后）
# 说"搜索XXX"即可自动进入路由

# 或直接 terminal 调用
python ~/.hermes/skills/research/search-router/router.py "搜索词"
python ~/.hermes/skills/research/search-router/router.py "搜索词" research 10
```

```python
# execute_code 中 import 使用
import sys
sys.path.insert(0, "~/.hermes/skills/research/search-router")
from router import SearchRouter

router = SearchRouter()
result = router.search("AI Agent trends", query_type="research", num_results=10)
print(result["results"])
```

### OpenClaw 子 Agent

子 Agent 里直接通过 terminal 调用，纯 Python 脚本无框架依赖：

```bash
python ~/.hermes/skills/research/search-router/router.py "搜索词" research 10
```

或 clone 到项目目录后：

```python
from router import SearchRouter

router = SearchRouter()
result = router.search("搜索词", query_type="research")
```

### Codex CLI / Claude Code

纯 Python 调用，先 `pip install requests`，然后：

```bash
# Shell 搜索
python /path/to/search-router/router.py "搜索词" news 10

# 或 Python 内联
python -c "
from router import SearchRouter
r = SearchRouter()
res = r.search('搜索词', query_type='research')
for r in res['results']:
    print(f'{r[\"title\"]}: {r[\"url\"]}')
"
```

> Codex 和 Claude Code 都支持执行 Python 和 Shell 命令，两种方式都可以。

### 任何 Python 进程

```python
from router import SearchRouter

router = SearchRouter()

# 通用搜索
result = router.search("搜索词", num_results=10)
print(f"使用了: {result['provider']}")

# 指定场景
result = router.search("搜索词", query_type="research", num_results=10)

# 多 Provider 对比
results = router.search_with_fallback("搜索词")
for r in results:
    print(f"[{r['provider']}] {r['total']}条结果, 耗时{r['latency_ms']}ms")

# 查看各 Provider 状态
print(router.provider_status())

# 运行时加 Key
router.add_provider_key("tavily", "new-key")
router.save_config()
```

### 为什么所有 Agent 都能用？

SearchRouter 是纯 Python 3 实现，唯一第三方依赖是 `requests`。它不依赖 Hermes 的 tool calling、不依赖 OpenClaw 的进程管理、不绑定任何 Agent 框架——就是一个搜索 API 的封装层。**只要能 `pip install requests` 就能跑。**

---

## 路由规则

系统根据 `query_type` 自动选择最优 Provider 顺序：

| 查询类型 | 路由顺序 | 适用场景 |
|----------|---------|---------|
| `default` | Tavily → Exa → Serper → Brave | 通用搜索，不指定类型时默认走这个 |
| `news` | Tavily → Exa → Serper | 最新新闻、快速事实核查 |
| `research` | Exa → Tavily → Serper | 深度研究、趋势分析、长文阅读 |
| `deep` | Exa → Tavily | 综合分析、全面检索（只走全文检索强的） |
| `google-serp` | Serper → Exa | Google SERP 快照，SEO 分析 |
| `competitor` | Serper → Exa | 竞品动态、市场调研 |
| `brave` | Brave → Tavily → Exa | 隐私优先场景 |

路由顺序含义：排在越前面的 Provider 优先尝试。如果失败了（Key 用尽、网络错误），自动依次尝试后面的。

路由规则在 `config.json` 的 `routing` 字段中定义，可自行修改。

---

## Key 轮换逻辑

```
你的请求
    ↓
SearchRouter 查路由表，决定用 Tavily
    ↓
Tavily 用当前 Key 发起请求
    ↓
├── 成功 (200) → 返回结果 ✅
├── Key 过期 (401/403) → 自动换下一个 Key，重试
├── 频率限制 (429) → 自动换下一个 Key，重试
└── 其他错误 → 换 Key，重试
    ↓
所有 Key 用尽 → 标记 Tavily 失效，降级到 Exa
    ↓
Exa 同上流程...
    ↓
全部失效 → 抛出 RuntimeError
```

**关键行为：**
- 每个 Provider 的 Key 池独立，互不影响
- `max_retries_per_key` 在 config.json 中配置（默认 2）
- 运行时可以用 `provider_status()` 查看各 Provider 状态
- 可以用 `add_provider_key("tavily", "新key")` 动态加 Key，不重启

---

## 环境变量注入

不想配 `config.json`？通过环境变量注入 Key，适合 Codex/Claude Code 等临时环境：

```bash
# 单个 Key
export SEARCH_TAVILY_KEYS="tvly-your-key"
export SEARCH_EXA_KEYS="your-exa-key"

# 多个 Key（逗号分隔）
export SEARCH_TAVILY_KEYS="key1,key2,key3"

# 然后直接搜
python router.py "搜索词"
```

环境变量格式：`SEARCH_{PROVIDER}_KEYS`，支持逗号分隔多 Key。

优先级：`config.json` 的 Key + 环境变量的 Key 会合并。环境变量中的 Key 追加到已有的 Key 列表后面。

---

## API 参考

### `SearchRouter(config_path=None, config=None)`

初始化路由器。

- `config_path` — config.json 路径。默认在脚本同目录找。
- `config` — 直接传 dict 作为配置。优先级高于 config_path。

### `search(query, query_type="default", num_results=10, **kwargs) → dict`

主搜索接口。自动路由、Key 轮换、Provider 降级。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `query` | str | 必填 | 搜索查询词 |
| `query_type` | str | `"default"` | 场景：`news/research/deep/google-serp/competitor/default` |
| `num_results` | int | `10` | 返回结果数量 |

返回统一格式 dict（见下方）。

### `search_with_fallback(query, query_type="default", num_results=10, **kwargs) → list`

同时调用所有可用 Provider，返回所有成功的结果列表。适合需要多源对比的场景。

### `provider_status() → dict`

返回各 Provider 状态：

```python
{
  "tavily": {"enabled": true, "keys_count": 2, "current_key_index": 0},
  "exa": {"enabled": false, "keys_count": 0, "current_key_index": 0},
  ...
}
```

### `add_provider_key(provider_name, key)`

运行时动态添加 Key。会同时写入内存和 `config.json`。

### `save_config(path=None)`

将当前配置（含运行时添加的 Key）持久化到文件。

---

## 统一输出格式

所有 Provider 返回相同结构，切换 Provider 不用改代码：

```json
{
  "provider": "tavily",
  "query": "搜索词",
  "results": [
    {
      "title": "文章标题",
      "url": "https://example.com/article",
      "snippet": "摘要内容...",
      "date": "2026-04-07",
      "score": null
    }
  ],
  "total": 10,
  "latency_ms": 342
}
```

| 字段 | 说明 |
|------|------|
| `provider` | 实际使用的 Provider 名称 |
| `query` | 原始查询词 |
| `results` | 搜索结果列表 |
| `results[].title` | 标题 |
| `results[].url` | 链接 |
| `results[].snippet` | 摘要（200-300 字符） |
| `results[].date` | 发布日期（部分 Provider 可能不返回） |
| `results[].score` | 相关性评分（部分 Provider 不返回） |
| `total` | 实际返回的结果数量 |
| `latency_ms` | 耗时（毫秒） |

---

## 添加新 Provider

想接入其他搜索 API？三步搞定：

**1. 在 `providers/` 下新建文件：**

```python
# providers/my_provider.py
class MyProviderProvider:
    name = "my_provider"

    def __init__(self, keys: list, config: dict):
        self.keys = keys
        self.current_key_index = 0
        self.config = config

    def search(self, query: str, num_results: int = 10, **kwargs) -> dict:
        # 你的 API 调用逻辑...
        return {
            "provider": self.name,
            "query": query,
            "results": [...],
            "total": len(results),
            "latency_ms": elapsed_ms,
        }
```

**2. 在 `router.py` 的 `PROVIDER_CLASSES` 中注册：**

```python
PROVIDER_CLASSES = {
    "tavily": TavilyProvider,
    "serper": SerperProvider,
    "exa": ExaProvider,
    "brave": BraveProvider,
    "my_provider": MyProviderProvider,  # ← 新增
}
```

**3. 在 `config.json` 中添加配置和路由规则：**

```json
{
  "providers": {
    "my_provider": {
      "enabled": true,
      "keys": ["your-api-key"],
      "current_key_index": 0,
      "priority": {"default": 2},
      "routing_score": {"default": 7}
    }
  },
  "routing": {
    "default": ["tavily", "my_provider", "exa", "serper", "brave"]
  }
}
```

---

## 文件结构

```
search-router/
├── README.md                # 本文档
├── SKILL.md                 # Hermes Agent Skill 定义
├── config.json.template     # API Key 配置模板（复制为 config.json 后修改）
├── config.json              # 实际配置（已 gitignore）
├── router.py                # 主程序 + CLI 入口（237 行）
├── .gitignore
└── providers/
    ├── __init__.py
    ├── tavily.py             # Tavily 搜索 API 实现
    ├── serper.py             # Serper (Google SERP) API 实现
    ├── exa.py                # Exa 深度搜索 API 实现
    └── brave.py              # Brave 搜索 API 实现
```

---

## 注意事项

1. **`config.json` 包含 API Key** — 已加入 `.gitignore`，切勿提交到 Git 仓库
2. **Tavily snippet 截断** — 每个结果只返回 ~300 字符摘要。需要完整原文时配合浏览器直接抓取目标页面
3. **免费额度**
   - Tavily 1000次/天 / Exa 1000次/月 / Serper 2500次/月 / Brave 2000次/月
   - Tavily 超额后返回 432，自动降级到 Exa
4. **Exa 延迟更高** — `search_with_contents()` 可获取全文，但延迟要比普通搜索高
5. **Serper 额外功能** — 支持 `search_images()` 进行图片搜索（需在代码中直接调用）
6. **各 Provider Key 池独立** — 轮换互不影响。Tavily Key 用尽不会影响 Serper

---

## License

MIT
