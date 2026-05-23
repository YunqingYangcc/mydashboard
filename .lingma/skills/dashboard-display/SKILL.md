---
name: dashboard-display
description: 仪表盘展示与绘图技能。当用户需要修改仪表盘布局、调整图表样式、修改配色方案、新增展示区块、修改UI交互时触发此技能。典型指令包括"改布局"、"调配色"、"改图表"、"新增区块"、"UI调整"、"仪表盘样式"等。此技能会先读取 prompts/展示绘图.md 确认6区块布局和Notion配色规范，再执行展示层修改。
---

# 展示绘图技能

## 触发场景

用户发出以下类型指令时激活:
- "改布局" / "调配色" / "改样式" / "UI调整"
- "改图表" / "新增区块" / "修改展示"
- "仪表盘样式" / "Notion风格" / "暗色主题"
- 任何涉及仪表盘页面展示、布局、配色的修改请求

## 工作流程

### Step 1: 读取 Prompt

执行任何操作前，必须先读取 `prompts/展示绘图.md`，确认:
- Notion 暗色主题配色值
- 6个区块的布局定义
- 行情阶段配色表（9种阶段 × bg/text/emoji）
- 组件函数清单和接口
- 数据缓存策略

### Step 2: 确认修改范围

根据指令确定涉及的文件:

| 修改类型 | 涉及文件 |
|---|---|
| 全局样式/CSS | `dashboard/components.py` → `init_page_style()` |
| 新增组件 | `dashboard/components.py` → 新函数 |
| 区块布局调整 | `dashboard/pages/信号仪表盘.py` |
| 图表样式 | `dashboard/components.py` → `render_volume_price_chart()` |
| 阶段配色 | `dashboard/components.py` + `kb/market_constants.py` |
| 页面配置 | `dashboard/components.py` → `init_page_style()` |
| 侧边栏/签名 | `dashboard/components.py` → `render_signature()` |

### Step 3: 执行修改

- 严格按照 `prompts/展示绘图.md` 中的配色值和布局规范编码
- 修改组件接口时，同步更新所有调用处
- 新增区块时，更新 prompt 中的区块清单

### Step 4: 同步 Prompt

**核心原则**: 展示层修改必须同步更新 prompt
- 改了配色值 → 更新 `prompts/展示绘图.md` 的配色表
- 新增区块 → 更新区块清单
- 新增组件 → 更新组件清单
- 改了缓存策略 → 更新缓存策略章节

## 配色速查

| 用途 | 色值 |
|---|---|
| 页面背景 | #1a1a1a |
| 卡片 | #242424 |
| 主文字 | #e6e6e6 |
| 边框 | rgba(255,255,255,0.06) |
| 圆角 | 6px |
| 输入框高 | 40px(单) / 120px(多) |

## 关联文件

- Prompt: `prompts/展示绘图.md`
- 组件: `dashboard/components.py`
- 页面: `dashboard/pages/信号仪表盘.py`
- 常量: `kb/market_constants.py`（阶段配色）
- 配置: `.streamlit/config.toml`（Streamlit主题）
