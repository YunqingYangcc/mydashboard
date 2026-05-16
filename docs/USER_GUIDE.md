# 使用文档

## 1. 这套系统是干什么的

这是一个本地运行的个人认知操作系统，目标是把你的输入、研究、判断、行动、复盘沉淀成长期资产。

当前版本优先聚焦 2 类能力：

- 文档知识库：文件夹投喂（inbox）+ Markdown 渲染
- 文档自动抽取：从 Markdown 抽取 `claims / relations / tasks`

推荐的一条工作流是：

- 只写 Markdown 文档
- 系统自动抽取 `claims / relations / tasks`

## 2. 安装与启动

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

初始化数据库：

```bash
python3 -m kb.main init-db
```

启动看板：

```bash
streamlit run dashboard/Home.py
```

## 3. 日常使用流程

推荐按下面的节奏使用。

### 每周一

1. 拉取最新数据

```bash
python3 -m kb.main ingest-all
```

2. 生成本周任务草案

```bash
python3 -m kb.main weekly-plan
```

3. 打开看板

```bash
streamlit run dashboard/Home.py
```

### 每周中

- 把研报、纪要、笔记、PDF、Markdown、图片资料放进 `data/inbox/`
- 在“文档工作台”逐篇阅读与复盘
- 在“认知闭环”里做当天输入 / 历史沉淀 / 汇总出题

如果你想走“只写文档”的方式，建议优先按模板写 Markdown：

- 模板见 `docs/MARKDOWN_TEMPLATE.md`
- 示例见 `data/inbox/markdown_sample_nvda.md`

### 每周五

导出复盘模板：

```bash
python3 -m kb.main weekly-review-template
```

导出的文件在：

- `data/exports/weekly_review_日期.md`

## 4. 看板说明

### 首页

- 查看今天先处理什么
- 查看最近判断更新
- 查看最近 3 篇研究文档及自动抽取摘要
- 搜索并预览 Markdown 知识文档
- 查看当前文档自动抽取出的断言 / 关系 / 任务数量

### 文档工作台

- 逐篇查看 Markdown 文档
- 对照原文检查自动抽取结果
- 查看该文档生成的 claims / relations / tasks

### 认知闭环

- 当天输入：快速看到今天写了什么文档、沉淀了哪些判断
- 历史沉淀：回看历史文档与抽取结果
- 汇总出题：聚合一段时间的抽取内容，生成可复制给 AI 的测验提示词

## 5. 目录说明

- `kb/`：后端逻辑
- `dashboard/`：Streamlit 页面
- `data/inbox/`：投喂目录
- `data/cognitive_os.db`：数据库文件
- `data/exports/`：导出的周报或模板
- `logs/`：运行日志

## 6. 环境变量说明

配置文件是 `.env`。

最重要的字段：

- `TIMEZONE`：默认北京时区
- `DATABASE_PATH`：SQLite 文件位置
- `INBOX_DIR`：投喂目录
- `RSS_URLS`：RSS 列表
- `FRED_API_KEY`
- `ALPHAVANTAGE_API_KEY`
- `FMP_API_KEY`
- `SEC_USER_AGENT`

AI 相关：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `SILICONFLOW_BASE_URL`
- `SILICONFLOW_API_KEY`
- `ZHIPU_BASE_URL`
- `ZHIPU_API_KEY`
- `XIAOMI_BASE_URL`
- `XIAOMI_API_KEY`

如果没有配置 AI 密钥，系统会自动用 mock 模式跑通流程。

## 7. 常用命令

初始化：

```bash
python3 -m kb.main init-db
```

全量采集：

```bash
python3 -m kb.main ingest-all
```

AI 工作流：

```bash
python3 -m kb.main run-ai
```

导出复盘模板：

```bash
python3 -m kb.main weekly-review-template
```

生成周任务草案：

```bash
python3 -m kb.main weekly-plan
```

运行测试：

```bash
pytest -q
```

## 8. 常见问题

### 1. 看板打开时报 `No module named 'dashboard'`

这个问题已经在当前版本修复。如果还出现，确认你是在项目根目录执行：

```bash
streamlit run dashboard/Home.py
```

### 2. AI 结果是 mock

说明你还没有配置真实模型密钥。这不影响你先跑通整套工作流。

### 3. 我只想用文件夹投喂，不想用 API

可以。把文件放到 `data/inbox/`，然后执行：

```bash
python3 -m kb.main ingest-all
```

目前支持：

- Markdown
- TXT
- HTML
- PDF
- PNG / JPG / JPEG / GIF / WEBP

如果 Markdown 使用固定标题：

- `## 判断`
- `## 关系`
- `## 下周跟踪`

系统会自动抽取：

- `claims`
- `relations`
- `tasks`

现在也支持更自由的写法：

- `判断：...`
- `关系：...`
- `任务：...`
- 标题下的单段正文

详细模板见：

- `docs/MARKDOWN_TEMPLATE.md`

## 9. 推荐使用习惯

- 每周新增 3 到 10 条高质量关系或断言
- 每周保持 10 分钟看首页与认知闭环
- 每周保持 10 分钟写复盘
- 优先沉淀事实、关系、断言，不追求一开始就全自动
