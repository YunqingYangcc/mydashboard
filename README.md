# 本地个人认知操作系统

一个低成本、可长期维护的本地认知操作系统，覆盖：

- 知识库：文档投喂、RSS 入库与全文检索
- 文档抽取：从 Markdown 自动抽取 claims / relations / tasks
- 认知沉淀：断言（claims）与关系（relations）的可复盘记录
- 认知提升：任务与复盘闭环
- AI 工作流：两研究员 + 总监，多模型结构化输出
- 仪表盘：Streamlit 多页本地看板

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m kb.main init-db
streamlit run dashboard/Home.py
```

## 目录

```text
mydashboard/
├── kb/
├── dashboard/
│   └── pages/
├── tests/
└── scheduler_examples.md
```

## 默认数据目录

- `data/cognitive_os.db`：SQLite 数据库
- `data/inbox/`：投喂研报、纪要、笔记
- `logs/`：每次运行一个日志文件
- `data/exports/`：周报、模板导出
