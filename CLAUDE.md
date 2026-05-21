# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

「国际遗产观察」是一个基于本地文章库的遗产保护领域研究问答工具，有两种使用方式：
- **Codex skill**：通过 SKILL.md 让 Codex 调用本地检索脚本回答问题
- **网页问答 bot**：Next.js 前端 + FastAPI 后端 + LLM 润色层，面向普通用户

## 架构

```
前端 (web/)                后端 (backend/)              核心库 (src/)
Next.js 15 + React 19      FastAPI + SQLAlchemy         guoji_yichan_guancha/
                           app/routers/chat.py           query.py  ← 检索+评分+回答构建
                           app/services/query_service.py ← 调用检索 + LLM 润色
                           app/prompts/                  ← system prompt 模板
```

**数据流**：用户提问 → chat.py 接收 → query_service.py 调用 `build_answer_bundle()` 检索 → LLM 润色（可选）→ 返回回答 + 来源卡片

**核心检索引擎** (`src/guoji_yichan_guancha/query.py`)：
- 纯规则引擎，无 LLM 参与
- 关键词匹配 + 多维评分排序（类别、年份、主题、证据类型）
- 支持 UNESCO 官方数据 API 补充查询
- 输出结构化回答（问题理解→库内结论→证据文章→证据边界）

**LLM 润色层** (`backend/app/services/query_service.py`)：
- `answer_from_library()`：纯规则检索，不调 LLM
- `answer_from_library_with_llm()`：规则检索 + OpenRouter LLM 润色
- LLM 只在 sources 非空时调用，失败时 fallback 到原始检索结果

## 常用命令

### 后端

```bash
# 安装依赖（项目根目录）
pip install -e ".[dev]"

# 运行后端测试
PYTHONPATH=backend:src python3 -m pytest backend/tests -v

# 运行单个测试
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_chat.py::test_name -v

# 编译检查
python3 -m compileall backend/app

# 初始化数据库
PYTHONPATH=backend:src python3 scripts/init_web_db.py

# 启动后端开发服务器
PYTHONPATH=backend:src uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd web
npm install
npm run dev        # 开发服务器
npm run build      # 生产构建
npm run typecheck  # TypeScript 检查
```

### 核心库

```bash
# 命令行问答
PYTHONPATH=src python3 scripts/query_library.py "你的问题" --library data/library/articles.jsonl --limit 5

# 增量补库
PYTHONPATH=src python3 scripts/sync_incremental.py

# 全量重建库
PYTHONPATH=src python3 scripts/build_library.py --source-dir "<文章目录>" --output-dir data/library

# 安装 Codex skill
python3 scripts/install_codex_skill.py
```

### 核心库测试

```bash
PYTHONPATH=src python3 -m pytest tests -v
```

## 环境变量

后端需要 `.env` 文件（项目根目录），关键配置：

| 变量 | 说明 |
|---|---|
| `database_url` | 数据库连接串，开发用 `sqlite:///data/runtime/app.db` |
| `session_secret` | 会话密钥 |
| `openrouter_api_key` | OpenRouter API key（LLM 润色用） |
| `openrouter_model` | 模型标识，如 `openai/gpt-5.4` |
| `library_path` | 文章库路径，如 `data/library/articles.jsonl` |
| `strict_source_mode` | 是否只允许 KB + UNESCO 数据源，默认 `true` |

## 关键约定

- **PYTHONPATH**：后端测试和运行需要 `PYTHONPATH=backend:src`，因为后端 `from guoji_yichan_guancha.query import ...` 直接引用核心库
- **pytest 配置**：`pyproject.toml` 中已设置 `pythonpath = ["backend", "src"]`，直接 `pytest` 即可
- **前端代理**：Next.js `rewrites` 将 `/api/*` 转发到 `http://127.0.0.1:8000/*`，开发时前后端分离运行
- **访客机制**：普通用户首次打开自动生成 `guest-uuid@guest.local` 身份，存 localStorage，无需注册
- **管理员**：通过 `/admin/login` 登录，账号密码固定为 `admin`
- **会话存储**：所有对话和消息持久化到数据库，支持历史恢复
- **来源卡片**：每个回答附带 `sources` 列表（标题、链接、日期、分类、证据类型），前端渲染为可点击卡片

## 数据源

- **主知识库**：`data/library/articles.jsonl`（~2500 篇文章，6MB）
- **UNESCO 数据**：通过 `data.unesco.org` API 实时查询世界遗产名录
- **证据类型**：报告资源、书刊资讯、会议新闻、政策动态、一般动态

## 部署

部署到腾讯云轻量服务器，详见 `deploy/setup-server.md`：
- Nginx 反向代理前端 3000 端口 + 后端 8000 端口
- systemd 管理前后端服务
- SQLite 作为数据库（当前规模足够）
