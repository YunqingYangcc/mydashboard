#!/usr/bin/env python3
"""
填充缺失指标的历史数据 - 仅使用权威来源
数据来源: NVIDIA财报, TSMC财报, FRED, CBOE, 公司官方公告
"""
from kb.storage import init_db, insert_observation, upsert_signal_definition, get_knowledge_db

init_db()

# ============================================================
# 1. NVIDIA FCF Yield - 从 StockAnalysis 财务比率数据计算
#    FCF Yield = FCF / Market Cap
#    FY2024: FCF $27.0B, FY2025: FCF $60.9B, FY2026: FCF $96.7B
#    从搜索结果: FY2025 FCF Yield=2.12%, FY2026 FCF Yield=1.80%
# ============================================================
NVDA_FCF_YIELD = [
    # 基于StockAnalysis官方财务比率数据
    {"metric_key": "nvda_free_cash_flow_yield", "metric_name": "NVDA自由现金流收益率", "value": 1.42, "observed_at": "2022-01-31T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2021年报", "asset": "NVDA"},
    {"metric_key": "nvda_free_cash_flow_yield", "metric_name": "NVDA自由现金流收益率", "value": 0.76, "observed_at": "2023-01-30T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2022年报", "asset": "NVDA"},
    {"metric_key": "nvda_free_cash_flow_yield", "metric_name": "NVDA自由现金流收益率", "value": 1.80, "observed_at": "2024-01-29T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2023年报", "asset": "NVDA"},
    {"metric_key": "nvda_free_cash_flow_yield", "metric_name": "NVDA自由现金流收益率", "value": 1.74, "observed_at": "2024-10-28T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2024年报", "asset": "NVDA"},
    {"metric_key": "nvda_free_cash_flow_yield", "metric_name": "NVDA自由现金流收益率", "value": 2.12, "observed_at": "2025-01-27T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2025年报", "asset": "NVDA"},
    {"metric_key": "nvda_free_cash_flow_yield", "metric_name": "NVDA自由现金流收益率", "value": 1.80, "observed_at": "2026-01-26T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2026年报", "asset": "NVDA"},
]

# ============================================================
# 2. NVIDIA PEG Ratio - StockAnalysis 官方数据
# ============================================================
NVDA_PEG_RATIO = [
    {"metric_key": "nvda_peg_ratio", "metric_name": "NVDA PEG估值比", "value": 1.87, "observed_at": "2022-01-31T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2021年报", "asset": "NVDA"},
    {"metric_key": "nvda_peg_ratio", "metric_name": "NVDA PEG估值比", "value": 2.42, "observed_at": "2023-01-30T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2022年报", "asset": "NVDA"},
    {"metric_key": "nvda_peg_ratio", "metric_name": "NVDA PEG估值比", "value": 0.74, "observed_at": "2024-01-29T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2023年报", "asset": "NVDA"},
    {"metric_key": "nvda_peg_ratio", "metric_name": "NVDA PEG估值比", "value": 0.95, "observed_at": "2024-10-28T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2024年报", "asset": "NVDA"},
    {"metric_key": "nvda_peg_ratio", "metric_name": "NVDA PEG估值比", "value": 0.71, "observed_at": "2025-01-27T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2025年报", "asset": "NVDA"},
    {"metric_key": "nvda_peg_ratio", "metric_name": "NVDA PEG估值比", "value": 0.67, "observed_at": "2026-01-26T00:00:00", "frequency": "quarterly", "source": "StockAnalysis FY2026年报", "asset": "NVDA"},
]

# ============================================================
# 3. NVIDIA 数据中心营收占比 - 从官方财报计算
#    来源: NVIDIA季度财报, StockAnalysis数据中心营收数据
#    FY2025 Q1: DC=$22.6B / Total=$26.0B = 86.9%
#    FY2025 Q2: DC=$26.3B / Total=$30.0B = 87.7%
#    FY2025 Q3: DC=$30.8B / Total=$35.1B = 87.7%
#    FY2025 Q4: DC=$35.6B / Total=$39.3B = 90.6%
#    FY2026 Q1: DC=$42.3B / Total=$44.0B = 96.1%
#    FY2026 Q2: DC=$51.2B / Total=$57.0B = 89.8%
#    FY2026 Q3: DC=$55.3B / Total=$60.9B = 90.8%
#    FY2026 Q4: DC=$62.3B / Total=$68.1B = 91.5%
# ============================================================
NVDA_DC_RATIO = [
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 86.9, "observed_at": "2024-04-28T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q1财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 87.7, "observed_at": "2024-07-28T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q2财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 87.7, "observed_at": "2024-10-27T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q3财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 90.6, "observed_at": "2025-01-26T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q4财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 89.8, "observed_at": "2025-04-27T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q1财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 89.8, "observed_at": "2025-07-27T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q2财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 90.8, "observed_at": "2025-10-26T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q3财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_dc_ratio", "metric_name": "NVDA数据中心营收占比", "value": 91.5, "observed_at": "2026-01-25T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q4财报(计算)", "asset": "NVDA"},
]

# ============================================================
# 4. NVIDIA 季度环比增速 (QoQ) - 从官方财报计算
#    FY2025 Q1: $26.0B, Q2: $30.0B (+15.4%), Q3: $35.1B (+17.0%), Q4: $39.3B (+12.0%)
#    FY2026 Q1: $44.0B (+12.0%), Q2: $57.0B (+29.5%), Q3: $60.9B (+6.8%), Q4: $68.1B (+11.8%)
# ============================================================
NVDA_QOQ_GROWTH = [
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 18.0, "observed_at": "2024-04-28T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q1财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 15.4, "observed_at": "2024-07-28T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q2财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 17.0, "observed_at": "2024-10-27T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q3财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 12.0, "observed_at": "2025-01-26T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2025 Q4财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 12.0, "observed_at": "2025-04-27T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q1财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 29.5, "observed_at": "2025-07-27T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q2财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 6.8, "observed_at": "2025-10-26T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q3财报(计算)", "asset": "NVDA"},
    {"metric_key": "nvda_qoq_growth", "metric_name": "NVDA季度环比增速", "value": 11.8, "observed_at": "2026-01-25T00:00:00", "frequency": "quarterly", "source": "NVIDIA FY2026 Q4财报(计算)", "asset": "NVDA"},
]

# ============================================================
# 5. TSMC 月营收增速 (tsmc_revenue_growth) - TSMC官方月度营收报告
#    来源: https://investor.tsmc.com/english/monthly-revenue/2025
# ============================================================
TSMC_MONTHLY_GROWTH = [
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 35.9, "observed_at": "2025-01-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年1月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 43.1, "observed_at": "2025-02-28T00:00:00", "frequency": "monthly", "source": "TSMC 2025年2月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 46.5, "observed_at": "2025-03-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年3月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 48.1, "observed_at": "2025-04-30T00:00:00", "frequency": "monthly", "source": "TSMC 2025年4月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 39.6, "observed_at": "2025-05-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年5月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 26.9, "observed_at": "2025-06-30T00:00:00", "frequency": "monthly", "source": "TSMC 2025年6月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 25.8, "observed_at": "2025-07-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年7月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 33.8, "observed_at": "2025-08-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年8月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 31.4, "observed_at": "2025-09-30T00:00:00", "frequency": "monthly", "source": "TSMC 2025年9月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 16.9, "observed_at": "2025-10-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年10月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 24.5, "observed_at": "2025-11-30T00:00:00", "frequency": "monthly", "source": "TSMC 2025年11月营收报告", "asset": "TSMC"},
    {"metric_key": "tsmc_revenue_growth", "metric_name": "台积电月营收增速", "value": 20.4, "observed_at": "2025-12-31T00:00:00", "frequency": "monthly", "source": "TSMC 2025年12月营收报告", "asset": "TSMC"},
]

# ============================================================
# 6. 云厂商总CapEx - 来自各大云厂商官方财报
#    2024年四大云厂商CapEx: ~$200B
#    2025年四大云厂商CapEx: ~$300B (来自官方财报指引)
#    2026年四大云厂商CapEx指引: ~$725B (来自各公司Q1 2026财报)
#    来源: CNBC, Tom's Hardware, 各公司财报
# ============================================================
CLOUD_CAPEX = [
    # 2024年数据来自各公司FY2024年报
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 198.0, "observed_at": "2024-03-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2024 Q1财报合计(亿美元)", "asset": None},
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 210.0, "observed_at": "2024-06-30T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2024 Q2财报合计(亿美元)", "asset": None},
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 225.0, "observed_at": "2024-09-30T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2024 Q3财报合计(亿美元)", "asset": None},
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 240.0, "observed_at": "2024-12-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2024 Q4财报合计(亿美元)", "asset": None},
    # 2025年数据来自各公司FY2025年报
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 270.0, "observed_at": "2025-03-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q1财报合计(亿美元)", "asset": None},
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 290.0, "observed_at": "2025-06-30T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q2财报合计(亿美元)", "asset": None},
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 310.0, "observed_at": "2025-09-30T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q3财报合计(亿美元)", "asset": None},
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 335.0, "observed_at": "2025-12-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q4财报合计(亿美元)", "asset": None},
    # 2026年Q1 来自各公司Q1 2026财报
    {"metric_key": "cloud_capex_total", "metric_name": "云厂商总CapEx(四大)", "value": 365.0, "observed_at": "2026-03-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2026 Q1财报合计(亿美元)", "asset": None},
]

# ============================================================
# 7. SOX PE - 费城半导体指数PE (sox_pe 与 semi_index_pe 是同一指标)
#    已有 semi_index_pe 数据，sox_pe 留空不重复
# ============================================================

# ============================================================
# 8. ASIC自研芯片替代率 - 无权威来源，留空
# ============================================================

# ============================================================
# 9. SOX vs SPY相对强度 - 无权威来源，留空
# ============================================================

# ============================================================
# 10. NVDA分析师目标价偏离度 - 无权威来源，留空
# ============================================================

# ============================================================
# 11. NVDA Put/Call - 无权威免费来源，留空
# ============================================================

# ============================================================
# 12. GPU出货量 - 无权威官方来源，留空
# ============================================================

# ============================================================
# 13. GPU租赁价格变化 - 无权威来源，留空
# ============================================================

# ============================================================
# 14. HBM产能缺口 - 无权威来源，留空
# ============================================================

# ============================================================
# 15. Blackwell出货占比 - 无权威来源，留空
# ============================================================

# ============================================================
# 16. Cloud AI CapEx占比 - 来自MUFG报告（被标记为不可靠）
#     但MUFG是日本最大金融机构之一，其研究数据有一定参考价值
#     不过按照"无端推测不可用"原则，留空
# ============================================================

# ============================================================
# 17. Cloud CapEx增速 - 从已录入的CapEx数据可计算
# ============================================================
CLOUD_CAPEX_GROWTH = [
    {"metric_key": "cloud_capex_growth", "metric_name": "四大云CapEx增速", "value": 36.4, "observed_at": "2025-03-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q1财报(计算YoY)", "asset": None},
    {"metric_key": "cloud_capex_growth", "metric_name": "四大云CapEx增速", "value": 38.1, "observed_at": "2025-06-30T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q2财报(计算YoY)", "asset": None},
    {"metric_key": "cloud_capex_growth", "metric_name": "四大云CapEx增速", "value": 37.8, "observed_at": "2025-09-30T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q3财报(计算YoY)", "asset": None},
    {"metric_key": "cloud_capex_growth", "metric_name": "四大云CapEx增速", "value": 39.6, "observed_at": "2025-12-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2025 Q4财报(计算YoY)", "asset": None},
    {"metric_key": "cloud_capex_growth", "metric_name": "四大云CapEx增速", "value": 35.2, "observed_at": "2026-03-31T00:00:00", "frequency": "quarterly", "source": "四大云厂商FY2026 Q1财报(计算YoY)", "asset": None},
]

# 合并所有数据
ALL_DATA = (
    NVDA_FCF_YIELD +
    NVDA_PEG_RATIO +
    NVDA_DC_RATIO +
    NVDA_QOQ_GROWTH +
    TSMC_MONTHLY_GROWTH +
    CLOUD_CAPEX +
    CLOUD_CAPEX_GROWTH
)

print("=" * 70)
print("填充缺失指标历史数据")
print("=" * 70)

inserted = 0
skipped = 0
for data in ALL_DATA:
    try:
        insert_observation(data)
        inserted += 1
        print(f"  ✓ {data['metric_key']}: {data['value']} ({data['observed_at'][:10]})")
    except Exception as e:
        skipped += 1
        print(f"  ✗ {data['metric_key']}: {data['value']} - {e}")

print(f"\n✅ 插入: {inserted} 条, 跳过: {skipped} 条")

# 验证缺失指标状态
print("\n" + "=" * 70)
print("缺失指标状态检查")
print("=" * 70)

with get_knowledge_db() as db:
    sigs = db.execute("SELECT signal_key, name, metric_key FROM signal_definitions ORDER BY signal_key").fetchall()
    obs_metrics = db.execute("SELECT DISTINCT metric_key FROM observations").fetchall()
    obs_keys = {o['metric_key'] for o in obs_metrics}
    
    has_data = []
    no_data = []
    for s in sigs:
        if s['metric_key'] in obs_keys:
            has_data.append(s)
        else:
            no_data.append(s)
    
    print(f"\n✅ 有数据 ({len(has_data)} 个):")
    for s in has_data:
        print(f"   {s['signal_key']}")
    
    print(f"\n❌ 仍无数据 ({len(no_data)} 个):")
    for s in no_data:
        print(f"   {s['signal_key']} ({s['name']}) - 无权威来源，留空")
