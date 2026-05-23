# Prompt 驱动开发规则

本项目的核心业务逻辑通过 `prompts/` 目录下的 Markdown 文件定义。修改代码前，必须先阅读对应的 prompt。

## Prompt 与代码绑定关系

| Prompt | 代码文件 | 职责 |
|---|---|---|
| `prompts/数据导入.md` | `kb/data_fetcher.py`, `kb/market_constants.py` | 数据源选择、获取、入库、标的清单 |
| `prompts/行情算法.md` | `kb/volume_analyzer.py`, `kb/market_constants.py` | 中间指标计算、9阶段判定规则、量能阈值 |
| `prompts/展示绘图.md` | `dashboard/components.py`, `dashboard/pages/信号仪表盘.py` | Notion主题、6区块布局、组件接口、配色 |

## 强制规则

1. **修改任何上述代码文件前，必须先用 `read_file` 读取对应的 prompt 文件**
2. 如果改动涉及 prompt 中定义的固定值（阈值、配色、数据源、表结构），必须同步更新 prompt 文件
3. 如果 prompt 文件被修改，必须检查对应代码是否需要同步修改
4. 新增功能模块时，必须先创建对应的 prompt 文件，再写代码

## 数据流

```
数据导入 → stock_daily_quotes → 行情算法 → market_phases → 展示绘图
```
