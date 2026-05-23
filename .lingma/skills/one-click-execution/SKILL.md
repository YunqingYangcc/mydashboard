---
name: one-click-execution
description: One-click execution of complete market analysis workflow. Automatically chains data-import → market-algorithm → dashboard-display three steps. Triggers when user needs "one-click refresh", "full update", "complete workflow", "re-analyze". This skill sequentially calls data-import, market-algorithm, and dashboard-display sub-skills to complete the full pipeline from data acquisition to visualization.
---

# 一键执行完整流程

## 触发场景

用户发出以下类型指令时激活:
- "一键刷新" / "完整更新" / "全流程执行"
- "重新分析" / "全部刷新" / "更新仪表盘"
- "从数据到展示" / "端到端更新"
- 任何需要执行完整数据处理 pipeline 的请求

## 工作流程

### 总览

本技能按顺序执行三个阶段：

```
阶段1: 数据导入 (data-import)
    ↓
阶段2: 行情判定 (market-algorithm)  
    ↓
阶段3: 仪表盘展示 (dashboard-display)
```

### Step 1: 数据导入

**调用技能**: `data-import`

执行操作:
1. **强制读取 prompt**：完整读取 `prompts/数据导入.md`，不得跳过或膽测
2. **检查数据库状态**：调用 `get_db_status()` 了解当前数据情况
3. **智能增量导入**：`batch_fetch_and_store(days=120)` 自动判断全量或增量
   - 首次导入：全量拉取120天
   - 日常更新：只拉取最新日期之后的数据（通常1天）
4. **数据验证**（关键）：自动执行5层验证
   - Level 1: API响应验证
   - Level 2: 数据质量验证（OHLC逻辑、数值范围）
   - Level 3: 业务逻辑验证（数据量、日期连续性）
   - Level 4: 数据库完整性验证
5. 存储到数据库 `stock_daily_quotes` 表
6. 报告导入结果（含验证信息）

**关键代码**: `kb/data_fetcher.py` → `batch_fetch_and_store(days=120)`, `validate_data_quality()`

**数据准确性保障**:
- ✅ **严禁膽造数据**：只能原样存储API返回的数据
- ✅ **严禁修改标的清单**：严格按 prompt 中的25只标的执行
- ✅ **严禁更改数据源**：A股用baostock，美股用Yahoo API
- ✅ **自动验证**：每批数据都经过5层验证
- ✅ **错误处理**：验证失败则拒绝入库，记录详细错误信息

### Step 2: 行情阶段判定

**调用技能**: `market-algorithm`

执行操作:
1. 读取 `prompts/行情算法.md` 确认9阶段判定规则
2. 对所有标的执行当前行情阶段判定
3. 根据量能、价格、均线等指标计算阶段
4. 存储判定结果到 `market_phases` 表
5. 验证并统计各阶段分布

**关键代码**: `kb/volume_analyzer.py` → `determine_all_current()` → `save_phases_to_db()`

### Step 3: 仪表盘展示更新

**调用技能**: `dashboard-display`

执行操作:
1. 读取 `prompts/展示绘图.md` 确认布局和配色规范
2. 检查是否需要更新展示层（通常不需要修改，仅验证）
3. 确保仪表盘能正确读取最新数据和判定结果
4. 如有UI问题，按 Notion 暗色主题规范修复

**关键文件**: 
- `dashboard/components.py` (组件和样式)
- `dashboard/pages/信号仪表盘.py` (页面布局)

## 执行模式

### 模式1: 完整流程（默认）

执行全部三个阶段，适合：
- 每日例行更新
- 数据完全刷新
- 重新分析所有标的

**指令示例**: "一键刷新"、"完整更新"

### 模式2: 跳过数据（增量模式）

如果用户说"只判定行情"或"已有数据"，可以跳过 Step 1，直接执行 Step 2+3。

**指令示例**: "只重新判定"、"用现有数据分析"

### 模式3: 仅展示层

如果用户说"只看仪表盘"或"不改数据"，仅执行 Step 3 的验证。

**指令示例**: "检查仪表盘"、"展示是否正常"

## 错误处理

### 数据导入失败

如果 Step 1 部分标的失败：
1. 记录失败原因（API限频、网络错误等）
2. 继续执行 Step 2（使用已成功导入的数据）
3. 在最终报告中列出失败标的和建议重试时间

### 行情判定异常

如果 Step 2 发现异常（如所有标的都是同一阶段）：
1. 警告用户可能存在算法问题
2. 建议检查数据质量或调整阈值
3. 暂停 Step 3，等待用户确认

### 展示层问题

如果 Step 3 发现UI问题：
1. 按照 `prompts/展示绘图.md` 规范修复
2. 同步更新 prompt 文档
3. 验证修复效果

## 执行清单

每次执行时，复制此清单跟踪进度：

```
Task Progress:
- [ ] Step 1: Data Import (data-import)
  - [ ] Read prompts/数据导入.md
  - [ ] Check database status via get_db_status()
  - [ ] Execute batch_fetch_and_store() (auto incremental)
  - [ ] Report import results
- [ ] Step 2: Market Phase Determination (market-algorithm)
  - [ ] Read prompts/行情算法.md
  - [ ] Execute determine_all_current()
  - [ ] Verify determination results
- [ ] Step 3: Dashboard Display (dashboard-display)
  - [ ] Read prompts/展示绘图.md
  - [ ] Verify display layer
  - [ ] Confirm UI compliance
```

## 关联技能

本技能依赖以下子技能：

1. **data-import** - Data import skill
   - Responsible for market data acquisition and storage
   
2. **market-algorithm** - Market algorithm skill
   - Responsible for market phase determination and analysis
   
3. **dashboard-display** - Dashboard display skill
   - Responsible for dashboard UI and visualization

## 关联文件

### Prompts
- `prompts/数据导入.md` - 数据源规则和标的清单
- `prompts/行情算法.md` - 9阶段判定规则和阈值
- `prompts/展示绘图.md` - Notion配色和布局规范

### 代码
- `kb/data_fetcher.py` - 数据获取逻辑（含智能增量）
- `kb/volume_analyzer.py` - 行情判定算法
- `dashboard/components.py` - UI组件和样式
- `dashboard/pages/信号仪表盘.py` - 页面布局

### 常量
- `kb/market_constants.py` - 标的清单、阶段定义、配色表

### 存储
- `data/*.db` - SQLite数据库（行情数据、判定结果）

## 最佳实践

1. **定期执行**: 建议每个交易日收盘后执行一次完整流程
   - 首次运行：全量导入120天数据（耗时3-5分钟）
   - 日常更新：自动增量模式（耗时1-2秒）
2. **检查失败**: 关注数据导入失败的标的，适时重试
3. **监控异常**: 如果某阶段标的数量突变，检查算法或数据
4. **保持同步**: 任何代码修改都要同步更新对应的 prompt
5. **备份数据**: 重大更新前备份数据库文件
6. **查看状态**: 使用 `print_db_status()` 随时查看数据库健康度

## 性能对比

| 场景 | API调用次数 | 耗时 | 说明 |
|------|------------|------|------|
| 首次全量导入 | ~3000次 | 3-5分钟 | 25标的×120天 |
| 日常增量更新 | ~25次 | 1-2秒 | 25标的×1天 |
| 性能提升 | **99%** | **99%** | 增量模式优势明显 |

## 快速参考

| Phase | Skill | Main Operation | Key Function |
|------|------|----------|----------|
| 1 | data-import | Data import (auto incremental) | `batch_fetch_and_store()` |
| 2 | market-algorithm | Market phase determination | `determine_all_current()` |
| 3 | dashboard-display | Display verification | `init_page_style()` |

## 注意事项

⚠️ **重要提醒**:
- 美股数据可能受API限频影响，失败时等待10秒重试
- 行情判定结果依赖数据质量，确保Step 1成功后再执行Step 2
- 展示层修改必须同步更新 prompt，保持代码和文档一致
- 如需调整判定阈值或规则，优先修改 prompt 再改代码
- **增量更新是默认行为**，无需额外配置
