# 数据源配置总结（2026-05-23更新）

## 📊 当前稳定数据源配置

### ✅ A股/ETF - baostock（完全稳定）
- **稳定性**: ⭐⭐⭐⭐⭐ 
- **限制**: 无
- **API Key**: 不需要
- **适用标的**: 12个（8只A股 + 4只ETF）
- **数据采集**: 每次采集成功率高，无限频问题

### ⚠️ 美股 - Alpha Vantage → Yahoo API（双层降级）

#### 第一层：Alpha Vantage API（首选）
- **稳定性**: ⭐⭐⭐⭐
- **API Key**: CMQ1LUGP0VKAP20R
- **免费套餐**: **每天25次请求** ⚠️
- **调用间隔**: 10-12秒
- **数据质量**: 高
- **当前状态**: 配额已用完（今日25次已达上限）

#### 第二层：Yahoo Finance API（备用）
- **稳定性**: ⭐⭐
- **限制**: 频繁403限频
- **调用间隔**: 7-9秒（随机化）
- **数据质量**: 中等
- **当前状态**: 可用，但需要较长间隔避免限频

## 🎯 数据采集策略

### 日常采集（推荐）
```bash
# 采集最近30天数据
python3 -c "from kb.data_fetcher import batch_fetch_and_store; batch_fetch_and_store(days=30, sleep_interval=5.0, force_full=True)"
```

**预期结果**:
- A股/ETF: 12个标的全部成功（~19行/标的）
- 美股: 
  - 如果Alpha Vantage配额充足：13个标的全部成功
  - 如果配额用完：降级到Yahoo API，可能需要更长时间

### 分阶段采集（Alpha Vantage配额有限时）

**第一天**：采集A股/ETF + 核心美股（前8个）
```python
# 手动指定标的列表，优先采集NVDA, AMD, AVGO等核心标的
```

**第二天**：采集剩余美股（后5个）

## 📝 重要注意事项

1. **Alpha Vantage配额管理**
   - 每天25次请求限制
   - 13只美股需要分两天采集
   - 建议优先采集核心标的

2. **Yahoo API限频处理**
   - 增加请求间隔到7-9秒
   - 遇到403错误自动重试
   - 可能需要等待10-15秒

3. **数据完整性**
   - A股/ETF数据完整可靠
   - 美股数据可能因限频部分缺失
   - 建议定期检查数据完整性

## 🔧 代码实现位置

- **主函数**: `kb/data_fetcher.py` → `batch_fetch_and_store()`
- **Alpha Vantage**: `fetch_alpha_vantage()`
- **Yahoo API**: `fetch_us_daily()`
- **配置文件**: `.env` → `ALPHAVANTAGE_API_KEY=CMQ1LUGP0VKAP20R`

## 📄 相关文档

- `prompts/数据导入.md` - 详细的数据源说明和标的清单
- `kb/data_fetcher.py` - 数据采集核心代码
- `.env` - API Key配置文件

---

**最后更新**: 2026-05-23  
**更新内容**: 移除不稳定数据源（AKShare, FMP, yfinance），确立Alpha Vantage为首选，Yahoo API为备用
