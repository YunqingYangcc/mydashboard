---
name: data-import
description: 行情数据导入技能。当用户需要导入、刷新、获取行情数据时触发此技能。典型指令包括"导入数据"、"刷新行情"、"拉取数据"、"获取行情"、"开始导入"等。此技能会先读取 prompts/数据导入.md 确认数据源规则，再执行数据获取和入库操作。支持智能增量更新，自动检测数据库状态，避免重复拉取。
---

# 数据导入技能

## 触发场景

用户发出以下类型指令时激活:
- "导入数据" / "开始导入" / "刷新行情" / "拉取数据"
- "获取行情" / "刷新所有标的" / "导入120天数据"
- "一键刷新" / "完整更新" / "日常更新"
- 任何涉及行情数据获取/刷新的请求

## 工作流程

### Step 1: 读取 Prompt（强制）

**必须严格执行**，不得跳过或臆测：
1. 完整读取 `prompts/数据导入.md`
2. 确认数据源配置（baostock vs Yahoo API）
3. 确认标的清单（25只，不得增删改）
4. 确认存储表结构（stock_daily_quotes）
5. 确认时区处理规则（美股 → US/Eastern）

⚠️ **禁止行为**:
- ❌ 不得修改标的清单
- ❌ 不得更改数据源配置
- ❌ 不得臆测字段映射关系
- ❌ 不得使用未经验证的数据源

### Step 2: 检查数据库状态

在执行导入前，先调用 `get_db_status()` 检查当前数据库状态：
- 各标的数据量
- 最新日期
- 判断是否需要全量或增量更新

**关键函数**: `kb/data_fetcher.py` → `get_db_status()`, `print_db_status()`

### Step 3: 执行数据导入（智能增量模式）

根据数据库状态自动选择导入策略：

| 场景 | 策略 | 说明 |
|---|---|---|
| 首次导入（无数据） | 全量拉取120天 | 每个标的从 start_date 到 end_date |
| 数据不足（<60天） | 全量拉取120天 | 确保数据完整性 |
| 日常更新（已有数据） | 增量更新 | 只拉取最新日期之后的数据 |
| 数据已是最新 | 跳过 | 最新日期 >= 昨天，无需更新 |

**关键代码**: `kb/data_fetcher.py` → `batch_fetch_and_store(days=120)`

**自动决策逻辑**: 详见代码实现中的智能判断逻辑

### Step 4: 数据验证（关键）

**导入完成后必须执行数据验证**，确保数据准确性：

#### 验证1: 数据量检查
```python
# 检查每个标的是否有合理的数据量
for symbol in TARGET_STOCKS:
    df = get_quotes_from_db(symbol, days=120)
    if len(df) < 60:  # 至少应有60天数据
        logger.warning(f"{symbol} 数据量不足: {len(df)}行")
```

#### 验证2: 日期连续性检查
```python
# 检查是否有数据缺口
expected_dates = pd.bdate_range(start_date, end_date)
actual_dates = pd.to_datetime(df['trade_date'])
missing_dates = expected_dates.difference(actual_dates)
if len(missing_dates) > 5:  # 允许最多5个交易日缺失
    logger.warning(f"{symbol} 存在{len(missing_dates)}天数据缺口")
```

#### 验证3: 数值合理性检查
```python
# 检查OHLCV数据是否合理
assert (df['high'] >= df['low']).all(), "最高价不能低于最低价"
assert (df['high'] >= df['close']).all(), "最高价不能低于收盘价"
assert (df['low'] <= df['open']).all(), "最低价不能高于开盘价"
assert (df['volume'] >= 0).all(), "成交量不能为负"
assert (df['close'] > 0).all(), "收盘价必须大于0"
```

#### 验证4: 跨源一致性检查（美股）
```python
# 对于美股，对比 Yahoo API 和 yfinance（如果可用）
# 确保两个数据源返回的收盘价差异 < 1%
```

#### 验证5: 数据库完整性检查
```python
# 确认主键唯一性
conn.execute("SELECT symbol, trade_date, COUNT(*) FROM stock_daily_quotes GROUP BY symbol, trade_date HAVING COUNT(*) > 1")
# 应该返回空结果，否则说明有重复数据
```

### Step 5: 报告结果（含验证信息）

输出导入结果摘要:
- 总标的数、成功数、失败数
- 各标的获取行数（区分全量/增量）
- **数据验证结果**（通过/警告/失败）
- 失败标的的失败原因
- 美股 API 403 时提示备用方案
- 数据库最终状态统计

**示例输出**:
```
✅ 数据导入完成
- 总标的: 25只
- 成功: 24只
- 失败: 1只 (XXX - API限频)
- 新增数据: 24行（增量模式）

🔍 数据验证:
- ✅ 数据量检查: 24/25 通过
- ⚠️ 日期连续性: 2个标的小幅缺口(<3天)
- ✅ 数值合理性: 全部通过
- ✅ 数据库完整性: 无重复数据
```

### Step 6: 同步检查

如果本次改动涉及 prompt 中定义的固定值（数据源、标的清单、表结构），同步更新 `prompts/数据导入.md`。

## 使用场景

### 场景1: 首次运行（全量导入）
```bash
python scripts/fetch_history_quotes.py
```
- 自动检测无数据，执行全量120天导入
- 耗时约3-5分钟（含美股API间隔）

### 场景2: 日常更新（增量模式）
```bash
python scripts/fetch_history_quotes.py
```
- 自动检测最新日期，只拉取缺失的天数
- 通常只需1-2秒（仅1天数据）
- 大幅降低API限频风险

### 场景3: 强制全量刷新
如需重新导入所有数据，先清空表后再次运行脚本（详见代码实现）

### 场景4: 查看数据库状态
```python
from kb.data_fetcher import print_db_status
print_db_status()
```

## 美股 API 限频处理

Yahoo Chart API 可能返回 403，此时:
1. 等待 10 秒重试 1 次
2. 仍然 403 → 尝试 yfinance 库
3. yfinance 也失败 → 报告失败，建议稍后重试或手动导入

**优化策略**: 
- 增量更新模式下，每天仅需1次API调用，几乎不会触发限频
- 全量导入时，sleep_interval=1.0秒，降低并发压力

## 关联文件

- Prompt: `prompts/数据导入.md`
- 代码: `kb/data_fetcher.py`
  - `batch_fetch_and_store()` - 智能增量导入主函数
  - `get_db_status()` - 查询数据库状态
  - `print_db_status()` - 打印状态摘要
  - `store_quotes_to_db()` - 数据存储（INSERT OR REPLACE）
  - `get_quotes_from_db()` - 数据读取
- 常量: `kb/market_constants.py`（标的清单）
- 存储: `kb/storage.py`（stock_daily_quotes 表，主键 symbol+trade_date）
- 脚本: `scripts/fetch_history_quotes.py`（命令行入口）

## 数据准确性保障（核心原则）

### 🚫 严禁幻觉行为

1. **不得臆造数据**
   - ❌ 禁止填充缺失数据（如用平均值填补）
   - ❌ 禁止推算历史价格
   - ❌ 禁止修改API返回的原始数据
   - ✅ 只能原样存储API返回的数据

2. **不得修改标的清单**
   - ❌ 禁止添加未在 prompt 中定义的标的
   - ❌ 禁止删除 prompt 中定义的标的
   - ❌ 禁止修改标的代码或名称
   - ✅ 严格按 `kb/market_constants.py` 中的 TARGET_STOCKS 执行

3. **不得更改数据源**
   - ❌ 禁止使用未经验证的第三方数据源
   - ❌ 禁止混用不同数据源的数据
   - ✅ A股/ETF 只能用 baostock
   - ✅ 美股只能用 Yahoo Finance API

4. **不得篡改时间**
   - ❌ 禁止修改交易日期
   - ❌ 禁止调整时区（美股必须用 US/Eastern）
   - ✅ 严格按 API 返回的日期存储

### ✅ 数据验证机制

#### 验证层级
```
Level 1: API响应验证
  ├─ HTTP状态码检查（200 OK）
  ├─ JSON格式验证
  └─ 必填字段检查

Level 2: 数据质量验证
  ├─ 数值范围检查（价格>0，成交量>=0）
  ├─ OHLC逻辑检查（high>=low, high>=close等）
  └─ 日期格式检查（YYYY-MM-DD）

Level 3: 业务逻辑验证
  ├─ 数据量合理性（至少60天）
  ├─ 日期连续性（缺口<5天）
  └─ 涨跌幅合理性（单日涨跌停限制）

Level 4: 数据库完整性验证
  ├─ 主键唯一性（无重复）
  ├─ 外键约束（market/chain有效）
  └─ 索引有效性
```

#### 验证失败处理
- **Level 1失败**: 记录错误，重试1次，仍失败则标记该标的为失败
- **Level 2失败**: 记录警告，存储数据但标记异常
- **Level 3失败**: 记录警告，建议人工检查
- **Level 4失败**: **立即停止**，回滚事务，修复后重新导入

### 🔍 数据溯源

所有数据必须可追溯：
1. **来源明确**: 每条数据都知道来自哪个API
2. **时间戳记录**: 记录数据获取时间（created_at）
3. **版本控制**: 如有数据修正，保留历史记录
4. **审计日志**: 记录每次导入的时间、标的数、成功/失败情况

### 📊 数据质量指标

每次导入后输出质量报告：
```python
{
    "total_symbols": 25,
    "success_count": 24,
    "failed_count": 1,
    "data_quality": {
        "completeness": 0.96,  # 数据完整性
        "accuracy": 1.0,       # 数据准确性（通过验证的比例）
        "consistency": 0.98,   # 数据一致性
        "timeliness": 1.0      # 数据及时性（最新日期）
    },
    "warnings": [
        "NVDA: 存在2天数据缺口",
        "AMD: 单日涨跌幅超过10%（需人工确认）"
    ]
}
```
