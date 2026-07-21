# Search Router

多 Provider 统一搜索路由工具。**你让 Agent 搜什么，它自己选最快的渠道。**

---

## 这是什么

你的 Agent 做搜索时，背后有 4 个搜索渠道（Tavily、Serper、Exa、Brave），Search Router 会**根据你要搜的内容类型，自动选最合适的那个**。搜新闻走快的，搜深度报告走全面的，搜竞品走 Google 排名准的——你不用管它用的是哪个。

---

## 安装

### 给 Hermes Agent 安装

项目已在你 Hermes 的 skill 目录下。如果重装或给另一台机器装：

```bash
# 克隆到 Hermes skill 目录
git clone https://github.com/Zsmboom/search-router.git ~/.hermes/skills/research/search-router

# 装依赖
pip install requests
```

装好后，你跟 Hermes 说"搜索XXX"，它会自动加载这个 skill。

### 给 Codex CLI / Claude Code 用

```bash
# 随便找个目录克隆
git clone https://github.com/Zsmboom/search-router.git
cd search-router
pip install requests
```

然后告诉 Agent："search-router 项目在 /path/to/search-router，用 Python 调用 router.py 或 import SearchRouter 做搜索"。

---

## 配置 API Key

每个搜索渠道都需要注册获取 Key。最少配一个（推荐 Tavily），配多个有容灾。

```bash
cp config.json.template config.json
```

编辑 `config.json`，填入你的 Key：

```json
{
  "providers": {
    "tavily": {
      "enabled": true,
      "keys": ["tvly-你的key"]
    }
  }
}
```

### 各渠道 Key 获取

| 渠道 | 注册地址 | 免费额度 | 适合搜什么 |
|------|---------|---------|-----------|
| **Tavily** | [tavily.com](https://tavily.com) | 1000次/天 | 新闻、快讯、通用搜索 |
| **Serper** | [serper.dev](https://serper.dev) | 2500次/月 | 竞品分析、Google 排名 |
| **Exa** | [exa.ai](https://exa.ai) | 1000次/月 | 深度研究、长文、学术 |
| **Brave** | [brave.com/search/api](https://brave.com/search/api) | 2000次/月 | 通用搜索、隐私场景 |

> ⚠️ `config.json` 含 API Key，已加入 `.gitignore`，不会提交到 Git。

如果你不想改配置文件，也可以用环境变量注入 Key：

```bash
export SEARCH_TAVILY_KEYS="你的key"
export SEARCH_EXA_KEYS="你的key"
```

---

## 怎么让 Agent 用

跟 Agent 说搜索需求就行，不同场景这么描述：

### 通用搜索

> "帮我搜一下 MiniMax 最新模型发布"

Agent 自动走默认路由（Tavily → Exa → Serper → Brave）。

### 搜新闻/快讯

> "帮我查一下最近英伟达有什么新闻"
> "搜一下今天的 AI 头条"

Agent 识别为新闻场景，优先走 Tavily（速度最快）。

### 深度研究

> "帮我深入研究一下 small language model 2026 的趋势"
> "帮我查一下 AI Agent 在企业落地的案例"

Agent 识别为研究场景，优先走 Exa（全文检索最全）。

### 竞品分析

> "帮我查一下 Notion AI 的最新功能"
> "查一下竞品站点 example.com 的收录情况"

Agent 识别为竞品场景，优先走 Serper（Google 排名最准）。

### 如果 Agent 没有自动用这个工具

直接说：

> "用 search-router 搜一下 XXX"

---

## 能收到什么

搜索结果以这种形式呈现给你：

- **标题** — 文章的标题
- **链接** — 可以直接点开的 URL
- **摘要** — 文章的主要内容摘要（200-300 字）
- **时间** — 发布日期（如果有的话）

Agent 会按相关性排列，每条结果附来源链接。示例输出：

```
=== 搜索结果 ===

1. MiniMax 发布最新模型 XXX
   https://example.com/article1
   摘要：MiniMax 今日正式发布...（2026-04-07）

2. MiniMax 模型深度评测
   https://example.com/article2
   摘要：本文对 MiniMax 最新模型进行了全面评测...
```

如果你要 JSON 格式的数据给其他程序用，跟 Agent 说：

> "用 search-router 搜 XXX，返回 JSON 格式"

---

## 常见问题

**Q：Key 用完了怎么办？**
A：回到官网重新注册一个 Key，加到 `config.json` 的 `keys` 数组里就行。配了多个 Provider 的话，一个用尽会自动切到下一个。

**Q：怎么知道当前配了几个 Key、状态如何？**
A：跟 Agent 说"查一下 search-router 的 Provider 状态"。

**Q：我想再加一个搜索渠道**
A：把新渠道的 Key 加到 `config.json` 里，告诉 Agent 有新的 Provider 可用就行。不需要改代码。

**Q：结果不理想，想换一个搜索渠道试试**
A：跟 Agent 说"用 Serper 搜 XXX"或"用 Exa 搜 XXX"，指定渠道即可。

---

## 注意

- 免费额度有限：Tavily 1000次/天、Exa 1000次/月、Serper 2500次/月、Brave 2000次/月
- 摘要只有 200-300 字，需要完整内容的话让 Agent 点进链接看原文
- 搜不到敏感词或登录后的内容（这个工具走的是公开搜索 API）
