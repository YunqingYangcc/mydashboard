# 开发文档

## 1. 总览

本项目是一个本地优先、SQLite 优先、可长期维护的个人认知操作系统。

设计原则：

- 单机可跑，不依赖重型基础设施
- 先结构化，后智能化
- 先事实、关系、断言，再逐步增强图谱和 RAG
- 先最小闭环，再增强体验

## 2. 当前模块结构

```text
mydashboard/
├── kb/
│   ├── ai.py
│   ├── config.py
│   ├── ingest.py
│   ├── logger.py
│   ├── main.py
│   ├── reports.py
│   ├── storage.py
│   └── utils.py
├── dashboard/
│   ├── Home.py
│   ├── components.py
│   └── pages/
├── docs/
└── tests/
```

## 3. 模块职责

### `kb/config.py`

- 读取 `.env`
- 定义路径、API Key、模型配置
- 创建运行目录

### `kb/logger.py`

- 提供统一 logging
- 每次运行一个日志文件
- 按北京时区输出时间

### `kb/storage.py`

- 负责 SQLite schema 初始化
- 封装 CRUD
- 提供查询函数
- 内置 FTS5 全文检索

当前表：

- `runs`
- `documents`
- `tasks`
- `entities`
- `relations`
- `claims`
- `ai_outputs`

### `kb/ingest.py`

- `ingest_rss()`：抓取 RSS 文档
- `ingest_folder()`：读取本地投喂目录
- `run_ingest_all()`：统一执行全量摄取

### `kb/ai.py`

- 两研究员 + 总监工作流
- 支持 OpenAI 兼容接口
- 未配置密钥时自动降级为 mock

### `kb/reports.py`

- 生成周复盘模板
- 导出到 `data/exports/`

### `kb/main.py`

- 命令行统一入口
- 连接初始化、ingest、AI、周计划与复盘模板

### `dashboard/`

- Streamlit 页面
- 每个页面顶部自行把项目根目录加入 `sys.path`
- 避免依赖 Streamlit 的导入上下文

## 4. 数据流

### 文档流

1. RSS / 文件夹投喂进入 `documents`
2. 通过 FTS5 提供全文检索
3. 可作为 AI 上下文和图谱证据来源

### 图谱流

1. 用户手动补录或 AI 后续抽取
2. 写入 `entities` / `relations` / `claims`
3. 在页面侧按文档与抽取结果复盘

### 闭环流

1. `tasks` 承载执行动作

## 5. Streamlit 导入机制说明

之前出现过：

- `ModuleNotFoundError: No module named 'dashboard'`

原因是 `streamlit run dashboard/Home.py` 时，脚本运行上下文不保证项目根目录已经在 `sys.path`。

当前修复策略：

- 在 `dashboard/Home.py`
- 以及 `dashboard/pages/*.py`

文件顶部先手动注入项目根目录到 `sys.path`，再导入 `dashboard.components` 和 `kb.*`。

这是为了避免不同启动方式下的包解析不一致。

## 6. 如何扩展

### 扩展 AI 工作流

推荐顺序：

1. 先让 AI 读最新 `documents`
2. 再读 `claims`
3. 最后输出结构化 JSON

后续可增强：

- 文档摘要缓存
- 图谱抽取
- claim 去重
- 支持多轮裁决

## 7. 后续建议的重构方向

当前项目为了快速落地，把不少逻辑集中在单文件中。后续如果继续扩展，建议逐步拆分：

### 存储层

把 `kb/storage.py` 拆成：

- `kb/storage/schema.py`
- `kb/storage/repositories.py`
- `kb/storage/query.py`

### ingest 层

把 `kb/ingest.py` 拆成：

- `kb/ingest/rss.py`
- `kb/ingest/folder.py`
- `kb/ingest/api.py`
- `kb/ingest/service.py`

### AI 层

把 `kb/ai.py` 拆成：

- `kb/ai/providers.py`
- `kb/ai/prompts.py`
- `kb/ai/workflow.py`

## 8. 与现有同级项目的对接建议

你同级已有：

- `yyq_monitor_nvdia`
- `yyq_monitor_gold`
- `yyq_financial_conditions_lab`

建议优先复用：

### 第一优先级

- 把 `yyq_monitor_nvdia` 的 fetcher / derived / report 逻辑迁进来
- 优先把 NVDA 的 observation 质量做高

### 第二优先级

- 把黄金和金融条件中的宏观指标迁成通用 observation

### 第三优先级

- 把多模型分析日志与原始输出的落库方式对齐到当前项目

## 9. 测试与验证

当前测试：

- `tests/test_storage.py`

运行命令：

```bash
pytest -q
```

当前已通过。

后续建议补充：

- ingest 层的最小 mock 测试
- AI prompt JSON 解析测试
- Streamlit 页面基础 smoke test

## 10. 调试建议

### 数据不进库

优先检查：

- `.env` 是否正确
- API Key 是否配置
- `logs/` 中最新日志

### 页面空白

优先检查：

- 是否先执行过 `init-db`
- 是否已投喂过 `data/inbox/` 并执行过 `ingest-all`

### AI 不出真实结果

优先检查：

- `OPENAI_API_KEY` 或各 provider key
- `base_url` 是否为兼容接口
- 模型名是否正确

## 11. 手机访问与远程访问

### 11.1 局域网手机访问（推荐）

前提：

- Dashboard 运行在你的电脑上
- 手机与电脑在同一个 Wi‑Fi / 同一个局域网

启动后，终端会输出两类 URL：

- `Local URL: http://localhost:8501`（仅本机可用）
- `Network URL: http://192.168.x.x:8501`（同一局域网设备可用）

在手机浏览器（Safari/Chrome）里直接打开 `Network URL` 即可访问。

常见注意事项：

- 电脑开启了防火墙时，可能需要允许 Python/Streamlit 接受入站连接
- 公司网络可能做了设备隔离（同 Wi‑Fi 也互相不可见），这种情况需要走“远程访问”

### 11.2 远程访问（外网/异地）

适用场景：

- 电脑在家或办公室持续运行 Dashboard
- 你希望在外面用手机访问

方案 A：ngrok（上手最快）

1. 安装并登录 ngrok
2. 在电脑上执行：

```bash
ngrok http 8501
```

3. ngrok 会输出一个公网 HTTPS 地址，在手机上打开该地址即可访问

安全建议：

- 使用 ngrok 的鉴权/访问控制能力（例如 basic auth 或仅允许你的账号访问）
- 不要把公网链接随意分享

方案 B：Cloudflare Tunnel（适合长期稳定）

如果你有域名并希望长期稳定访问，可使用 Cloudflare Tunnel 将本机 `8501` 端口绑定到子域名，再配合 Cloudflare Access 做身份验证。

## 12. 开发规范

建议继续遵守：

- 默认使用 ASCII
- 日志统一用 `logging`
- 每次运行一个日志文件
- 不用 `print`
- 尽量保证单机可跑
- 优先可维护性，不追求一开始过度抽象
