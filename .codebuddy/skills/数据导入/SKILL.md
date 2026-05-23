---
name: 数据导入
description: 行情数据导入技能。当用户需要导入、刷新、获取行情数据时触发此技能。典型指令包括"导入数据"、"刷新行情"、"拉取数据"、"获取行情"、"开始导入"等。此技能会先读取 prompts/数据导入.md 确认数据源规则，再执行数据获取和入库操作。
---

# 数据导入技能

## 触发场景

用户发出以下类型指令时激活:
- "导入数据" / "开始导入" / "刷新行情" / "拉取数据"
- "获取行情" / "刷新所有标的" / "导入120天数据"
- 任何涉及行情数据获取/刷新的请求

## 工作流程

### Step 1: 读取 Prompt

执行任何操作前，必须先读取 `prompts/数据导入.md`，确认:
- 数据源配置（baostock vs Yahoo API）
- 标的清单（25只）
- 存储表结构（stock_daily_quotes）
- 时区处理规则（美股 → US/Eastern）

### Step 2: 执行数据导入

根据用户指令执行:

| 指令 | 操作 | 代码调用 |
|---|---|---|
| 导入/刷新全部 | 批量获取120天数据 | `batch_fetch_and_store(days=120)` |
| 刷新单只 | 获取单只标的最新数据 | `fetch_single_latest(symbol, days=10)` |
| 导入N天 | 批量获取N天数据 | `batch_fetch_and_store(days=N)` |

关键代码文件: `kb/data_fetcher.py`

### Step 3: 报告结果

输出导入结果摘要:
- 总标的数、成功数、失败数
- 各标的获取行数
- 失败标的的失败原因
- 美股 API 403 时提示备用方案

### Step 4: 同步检查

如果本次改动涉及 prompt 中定义的固定值（数据源、标的清单、表结构），同步更新 `prompts/数据导入.md`。

## 美股 API 限频处理

Yahoo Chart API 可能返回 403，此时:
1. 等待 10 秒重试 1 次
2. 仍然 403 → 尝试 yfinance 库
3. yfinance 也失败 → 报告失败，建议稍后重试或手动导入

## 关联文件

- Prompt: `prompts/数据导入.md`
- 代码: `kb/data_fetcher.py`
- 常量: `kb/market_constants.py`（标的清单）
- 存储: `kb/storage.py`（stock_daily_quotes 表）
