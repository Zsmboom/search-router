---
name: search-router
description: |
  统一搜索路由层。核心解决的问题：skill 太多，不知道用哪个搜索工具。
  当用户说"搜索XXX"/"帮我查一下"/"网络查询"时，加载此 skill 并执行搜索路由。
  支持 Tavily/Serper/Exa/Brave 四个 Provider，自动 key 轮换，智能路由。
triggers:
  - "搜索"
  - "帮我查一下"
  - "网络查询"
  - "搜索一下"
  - "查一下"
  - "search"
---

# Search Router — 统一搜索路由

## 解决的问题

用 AI Agent 时，最烦的不是"搜不到"，而是"该用哪个搜索工具"。

Tavily 搜新闻快，Serper 拿来查 Google 排名，Exa 适合深度研究——每种场景各有好用的工具，但来回切换、记 API Key、管理配额，累。

Search Router 就是来解决这个问题的：**你只管搜，剩下的它帮你安排。**

---

## 核心能力

- **智能路由** — 根据查询类型自动选最优 Provider
- **Key 自动轮换** — 429/403 时自动换下一个 Key，不卡壳
- **多 Provider 级联** — 主 Provider 失效，自动降级到下一个
- **统一输出格式** — 不管用哪个 Provider，返回结构都一样

---

## 支持的搜索场景

| 场景 | 推荐 Provider | 说明 |
|------|-------------|------|
| 最新新闻 / 快讯 | Tavily → Exa | 速度优先 |
| 深度研究 / 学术 | Exa → Tavily | 全面优先 |
| Google SERP 快照 | Serper | 接近 Google 原始结果 |
| 竞品分析 | Serper → Exa | 多维度抓取 |
| 通用查询 | Tavily → Exa → Serper → Brave | 默认级联 |

---

## 快速使用

### 第一步：配置 API Key

```bash
cd ~/.hermes/skills/research/search-router
cp config.json.template config.json
# 编辑 config.json，填入你的 Key
```

支持四个 Provider，按需启用：

| Provider | Key 获取 | 免费额度 |
|----------|---------|---------|
| **Tavily** | [tavily.com](https://tavily.com) | 1000次/天 |
| **Serper** | [serper.dev](https://serper.dev) | 2500次/月 |
| **Exa** | [exa.ai](https://exa.ai) | 1000次/月 |
| **Brave** | [brave.com/search/api](https://brave.com/search/api) | 2000次/月 |

### 第二步：搜索

```python
import sys
sys.path.insert(0, "/path/to/search-router")
from router import SearchRouter

router = SearchRouter()

# 通用搜索（自动路由）
result = router.search("MiniMax 最新模型发布", num_results=10)
print(f"使用: {result['provider']}")
for r in result["results"]:
    print(f"  {r['title']}: {r['url']}")

# 指定场景（显式路由）
result = router.search("AI Agent 组织落地趋势", query_type="research", num_results=10)

# 获取所有 Provider 结果对比
results = router.search_with_fallback("搜索工具对比")
for r in results:
    print(f"[{r['provider']}] {r['total']}条结果, 耗时{r['latency_ms']}ms")
```

### 第三步：查看 Provider 状态

```python
status = router.provider_status()
print(status)
# 看到某个 Provider 的 key 用尽，可以运行时添加新 key:
router.add_provider_key("tavily", "新key")
router.save_config()
```

---

## Key 轮换逻辑（发生了什么）

```
你的请求
    ↓
SearchRouter 查路由表，决定用 Tavily
    ↓
Tavily 用当前 Key 发请求
    ↓
├── 成功 (200) → 返回结果，结束
├── Key 过期 (401/403) → 自动换下一个 Key，重试
├── 频率限制 (429) → 自动换下一个 Key，重试
└── 其他错误 → 换 Key，重试
    ↓
所有 Key 用尽 → 标记 Tavily 失效，降级到 Exa
    ↓
Exa 同上流程...
    ↓
全部失效 → 返回空结果
```

每个 Provider 可以配置多个 Key，轮换是自动的，你不需要管。

---

## 与其他工具的区别

| | Search Router | 单 Provider | 手动切换 |
|---|---|---|---|
| **配置一次** | ✅ 多个 Key 自动轮换 | ❌ Key 用尽要手动换 | ❌ 每个工具都要配 |
| **智能路由** | ✅ 按场景选最优 | ❌ 什么场景都用同一个 | ❌ 要记哪个场景用哪个 |
| **自动降级** | ✅ 主 Provider 失效自动切 | ❌ 失败就停了 | ❌ 要自己判断 |
| **统一格式** | ✅ 换 Provider 不改代码 | ✅ | ❌ 每种格式要单独解析 |

---

## 技术细节

**统一返回格式：**

```json
{
  "provider": "tavily",
  "query": "搜索词",
  "results": [
    {
      "title": "文章标题",
      "url": "https://example.com",
      "snippet": "摘要内容...",
      "date": "2026-04-07",
      "score": null
    }
  ],
  "total": 10,
  "latency_ms": 342
}
```

**Provider 支持情况：**

- **Tavily**：综合搜索，速度快，支持新闻场景
- **Serper**：Google SERP 近似结果，适合 SEO 和竞品分析
- **Exa**：深度全文检索，支持 `search_with_contents()` 获取文章完整内容
- **Brave**：隐私优先的搜索，适合通用查询

---

## 项目地址

**GitHub：** [https://github.com/Zsmboom/search-router](https://github.com/Zsmboom/search-router)

```bash
# Clone
git clone https://github.com/Zsmboom/search-router.git
cd search-router

# 配置 Key
cp config.json.template config.json
# 编辑 config.json 填入你的 API keys

# 安装依赖
pip install requests

# 使用
python router.py "搜索词" [场景] [结果数]
```

---

## 使用场景示例

**场景 1：竞品动态监控**
```python
router.search("Notion AI 最新功能", query_type="competitor")
```

**场景 2：技术趋势研究**
```python
router.search("small AI model 2026", query_type="research")
```

**场景 3：突发新闻**
```python
router.search("英伟达发布会", query_type="news")
```

**场景 4：通用查询（不用记用什么）**
```python
router.search("iPhone 17 配置曝光")
# 自动走默认路由：Tavily → Exa → Serper → Brave
```

---

## 注意事项

- `config.json` 包含敏感 Key，已加入 .gitignore，切勿提交到 Git
- 各 Provider 的 Key 池独立，轮换互不影响
- Exa 的 `search_with_contents()` 可获取全文，但延迟更高
- Serper 支持 `search_images()` 图片搜索方法
