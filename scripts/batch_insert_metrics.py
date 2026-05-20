#!/usr/bin/env python3
"""批量录入指标数据"""
from kb.storage import init_db, upsert_signal_definition, insert_observation, list_signal_definitions, evaluate_signals_for_metric, compute_observation_derivatives, compute_daily_score

init_db()

# ===== 1. 定义缺失的信号 =====
NEW_SIGNALS = [
    {"signal_key": "nvda_revenue_growth", "name": "NVDA营收增速", "dimension": "基本面",
     "frequency": "quarterly", "comparator": "lt", "threshold": 20.0,
     "metric_key": "nvda_revenue_growth", "description": "营收增速<20%预警增长放缓"},
    {"signal_key": "nvda_data_center_rev_pct", "name": "NVDA数据中心营收占比", "dimension": "基本面",
     "frequency": "quarterly", "comparator": "lt", "threshold": 75.0,
     "metric_key": "nvda_data_center_rev_pct", "description": "占比<75%多云化风险"},
    {"signal_key": "nvda_blackwell_shipment_pct", "name": "NVDA Blackwell出货占比", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 50.0,
     "metric_key": "nvda_blackwell_shipment_pct", "description": "新品占比<50%换代周期偏慢"},
    {"signal_key": "nvda_capex_to_rev", "name": "NVDA CapEx占营收比", "dimension": "基本面",
     "frequency": "quarterly", "comparator": "gt", "threshold": 15.0,
     "metric_key": "nvda_capex_to_rev", "description": ">15%资本开支压力较大"},
    {"signal_key": "nvda_free_cash_flow_yield", "name": "NVDA自由现金流收益率", "dimension": "估值",
     "frequency": "quarterly", "comparator": "lt", "threshold": 3.0,
     "metric_key": "nvda_free_cash_flow_yield", "description": "<3%现金流创造能力偏弱"},
    {"signal_key": "nvda_peg_ratio", "name": "NVDA PEG估值比", "dimension": "估值",
     "frequency": "daily", "comparator": "gt", "threshold": 2.0,
     "metric_key": "nvda_peg_ratio", "description": ">2增长消化估值难度大"},
    {"signal_key": "tsm_revenue_growth", "name": "台积电营收增速", "dimension": "需求",
     "frequency": "monthly", "comparator": "lt", "threshold": 20.0,
     "metric_key": "tsm_revenue_growth", "description": "增速<20%半导体需求走弱"},
    {"signal_key": "tsm_advanced_revenue_pct", "name": "台积电先进制程营收占比", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 60.0,
     "metric_key": "tsm_advanced_revenue_pct", "description": "<60%先进制程需求疲软"},
    {"signal_key": "hbm_revenue_sk", "name": "SK海力士HBM年化收入", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 15.0,
     "metric_key": "hbm_revenue_sk", "description": "年化收入<15B韩元需求不足"},
    {"signal_key": "gpu_shipments", "name": "AI GPU年度出货量", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 800.0,
     "metric_key": "gpu_shipments", "description": "<800万片出货量低于预期"},
    {"signal_key": "cloud_capex_total", "name": "云厂商总CapEx", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 5000.0,
     "metric_key": "cloud_capex_total", "description": "<500亿美元资本开支收缩"},
    {"signal_key": "cloud_ai_capex_pct", "name": "AI CapEx占比", "dimension": "需求",
     "frequency": "quarterly", "comparator": "lt", "threshold": 50.0,
     "metric_key": "cloud_ai_capex_pct", "description": "<50%AI投入意愿下降"},
    {"signal_key": "us_cpi_yoy", "name": "美国CPI同比", "dimension": "宏观",
     "frequency": "monthly", "comparator": "gt", "threshold": 4.0,
     "metric_key": "us_cpi_yoy", "description": ">4%通胀压力持续"},
    {"signal_key": "put_call_ratio", "name": "市场Put/Call比率", "dimension": "情绪",
     "frequency": "daily", "comparator": "gt", "threshold": 1.0,
     "metric_key": "put_call_ratio", "description": ">1空头情绪偏重"},
    {"signal_key": "nasdaq_pe", "name": "纳斯达克综合指数PE", "dimension": "估值",
     "frequency": "daily", "comparator": "gt", "threshold": 35.0,
     "metric_key": "nasdaq_pe", "description": ">35纳指估值偏高"},
    {"signal_key": "semi_index_pe", "name": "费城半导体指数PE", "dimension": "估值",
     "frequency": "daily", "comparator": "gt", "threshold": 30.0,
     "metric_key": "semi_index_pe", "description": ">30半导体估值偏贵"},
]

print("📝 正在定义新信号...")
for sig in NEW_SIGNALS:
    upsert_signal_definition(sig)
    print(f"  ✓ {sig['signal_key']}")
print(f"\n✅ 已定义 {len(NEW_SIGNALS)} 个新信号")

# ===== 2. 录入观测值 =====
OBSERVATIONS = [
    ("nvda_pe", 45.31, "2026-05-20", "Yahoo Finance"),
    ("nvda_ps", 24.74, "2026-05-20", "同花顺金融数据库"),
    ("nvda_revenue_growth", 79.5, "2026-05-20", "华尔街一致预期（FY27Q1）"),
    ("nvda_gross_margin", 75.0, "2026-05-20", "公司指引（FY26年末目标）"),
    ("tsm_revenue_growth", 31.6, "2026-05-20", "台积电2025财年财报"),
    ("tsm_advanced_revenue_pct", 74.0, "2026-05-20", "台积电2025Q4财报（7nm及以下）"),
    ("hbm_revenue_sk", 20.0, "2026-05-20", "SK海力士2025财年HBM年化收入"),
    ("gpu_shipments", 1120.0, "2026-05-20", "花旗预测（FY27财年GPU总出货量，万片）"),
    ("cloud_capex_total", 8300.0, "2026-05-20", "TrendForce（九大云厂商2026年合计）"),
    ("cloud_ai_capex_pct", 65.0, "2026-05-20", "IDC 2026年AI资本开支占比预测"),
    ("us_10y_yield", 4.60, "2026-05-20", "FRED"),
    ("us_cpi_yoy", 3.8, "2026-05-20", "美国劳工部（2026年4月）"),
    ("vix", 19.2, "2026-05-20", "CBOE"),
    ("put_call_ratio", 0.88, "2026-05-20", "CBOE"),
    ("nasdaq_pe", 38.7, "2026-05-20", "S&P Global"),
    ("semi_index_pe", 32.5, "2026-05-20", "Philadelphia Semiconductor Index"),
    ("nvda_data_center_rev_pct", 88.5, "2026-05-20", "公司FY26Q4财报"),
    ("nvda_blackwell_shipment_pct", 45.0, "2026-05-20", "摩根士丹利预测"),
    ("nvda_capex_to_rev", 12.8, "2026-05-20", "公司FY26Q4财报"),
    ("nvda_free_cash_flow_yield", 4.8, "2026-05-20", "高盛测算"),
    ("nvda_peg_ratio", 0.63, "2026-05-20", "富国银行测算"),
]

print("\n📊 正在录入观测值...")
inserted_metrics = []
signal_defs = list_signal_definitions()
for metric_key, value, date, source in OBSERVATIONS:
    sig_def = next((s for s in signal_defs if s["metric_key"] == metric_key), None)
    if sig_def:
        insert_observation({
            "metric_key": metric_key,
            "metric_name": sig_def["name"],
            "value": value,
            "observed_at": f"{date}T00:00:00",
            "frequency": sig_def["frequency"],
            "source": source,
            "asset": "NVDA" if "nvda" in metric_key else ("TSMC" if "tsm" in metric_key else None),
        })
        inserted_metrics.append((metric_key, value))
        print(f"  ✓ {metric_key}: {value}")
    else:
        print(f"  ✗ {metric_key}: 未找到信号定义")

print(f"\n✅ 已录入 {len(inserted_metrics)} 条观测值")

# ===== 3. 信号灯评估 =====
print("\n🚦 正在评估信号灯...")
evaluations = []
for metric_key, value in inserted_metrics:
    results = evaluate_signals_for_metric(metric_key, value, f"2026-05-20T00:00:00")
    evaluations.extend(results)

for ev in evaluations:
    status_icon = "🟢" if ev["status"] == "positive" else ("🔴" if ev["status"] == "negative" else "⚪")
    print(f"  {status_icon} {ev['name']}: {ev['raw_value']} → {ev['status']}")
print(f"\n✅ 已评估 {len(evaluations)} 个信号")

# ===== 4. 衍生计算 =====
print("\n📈 正在计算衍生指标...")
for metric_key, value in inserted_metrics:
    deriv = compute_observation_derivatives(metric_key, f"2026-05-20T00:00:00", value)
    if deriv["mom_pct"] or deriv["yoy_pct"]:
        print(f"  ✓ {metric_key}: MoM={deriv['mom_pct']:.1f}% YoY={deriv['yoy_pct']:.1f}%")
    if deriv["is_anomaly"]:
        print(f"  ⚠️  {metric_key}: 检测到异常 (z={deriv['z_score']:.2f})")
print("✅ 衍生计算完成")

# ===== 5. 综合评分 =====
print("\n📊 正在计算综合评分...")
score_result = compute_daily_score("2026-05-20")
if score_result:
    print(f"  综合评分: {score_result['total_score']}")
    print(f"  (正向:{score_result['positive_count']} 负向:{score_result['negative_count']} 中性:{score_result['neutral_count']})")
    print(f"  建议动作: {score_result['action_suggestion']}")
    print(f"  维度分解:")
    for dim, breakdown in score_result['dimension_breakdown'].items():
        print(f"    {dim}: 🟢{breakdown.get('positive',0)} 🔴{breakdown.get('negative',0)} ⚪{breakdown.get('neutral',0)}")
print("\n✅ 综合评分完成")

print("\n" + "="*60)
print("📋 录入汇总")
print("="*60)
print(f"新定义信号: {len(NEW_SIGNALS)} 个")
print(f"观测值录入: {len(inserted_metrics)} 条")
print(f"信号灯评估: {len(evaluations)} 条")
print(f"评估日期: 2026-05-20")
