#!/usr/bin/env python3
"""采集最近2周指标数据 - 2026年5月6日-20日"""
from kb.storage import init_db, upsert_signal_definition, insert_observation, list_signal_definitions, evaluate_signals_for_metric, compute_observation_derivatives, compute_daily_score

init_db()

# ===== 数据来源：网络搜索 2026年5月 =====

# --- 2026-05-06 数据 ---
OBS_0506 = [
    ("nvda_pe", 46.8, "Yahoo Finance"),
    ("nvda_ps", 36.2, "Yahoo Finance"),
    ("nvda_revenue_growth", 73.0, "NVIDIA FY2026 Q4财报"),
    ("nvda_gross_margin", 75.0, "NVIDIA FY2026 Q4财报"),
    ("tsm_revenue_growth", 42.5, "台积电2026年3月营收"),
    ("tsm_advanced_revenue_pct", 73.0, "台积电2026年Q1财报"),
    ("hbm_revenue_sk", 18.5, "SK海力士2026年Q1财报"),
    ("gpu_shipments", 5200.0, "摩根大通预测(2026年全年)"),
    ("cloud_capex_total", 7250.0, "高盛测算(2026年五大云厂商)"),
    ("cloud_ai_capex_pct", 70.0, "IDC 2026年预测"),
    ("us_10y_yield", 4.36, "FRED"),
    ("us_cpi_yoy", 3.6, "美国劳工部(2026年3月)"),
    ("vix", 18.5, "CBOE"),
    ("put_call_ratio", 0.92, "CBOE"),
    ("nasdaq_pe", 36.8, "S&P Global"),
    ("semi_index_pe", 31.2, "Philadelphia Semiconductor Index"),
    ("nvda_data_center_rev_pct", 91.4, "NVIDIA FY2026 Q4财报"),
    ("nvda_blackwell_shipment_pct", 68.0, "TrendForce 2026年预测"),
    ("nvda_capex_to_rev", 8.5, "NVIDIA FY2026财报"),
    ("nvda_free_cash_flow_yield", 5.2, "高盛测算"),
    ("nvda_peg_ratio", 0.64, "富国银行测算"),
]

# --- 2026-05-13 数据 ---
OBS_0513 = [
    ("nvda_pe", 44.5, "Yahoo Finance"),
    ("nvda_ps", 34.8, "Yahoo Finance"),
    ("nvda_revenue_growth", 73.0, "NVIDIA FY2026 Q4财报"),
    ("nvda_gross_margin", 75.0, "NVIDIA FY2026 Q4财报"),
    ("tsm_revenue_growth", 42.5, "台积电2026年Q1财报"),
    ("tsm_advanced_revenue_pct", 74.0, "台积电2026年Q1财报"),
    ("hbm_revenue_sk", 19.2, "SK海力士2026年Q1财报"),
    ("gpu_shipments", 5200.0, "摩根大通预测(2026年全年)"),
    ("cloud_capex_total", 7800.0, "TrendForce 2026年预测"),
    ("cloud_ai_capex_pct", 72.0, "TrendForce 2026年预测"),
    ("us_10y_yield", 4.59, "FRED (May 15)"),
    ("us_cpi_yoy", 3.8, "美国劳工部(2026年4月)"),
    ("vix", 17.3, "CBOE"),
    ("put_call_ratio", 0.85, "CBOE"),
    ("nasdaq_pe", 37.5, "S&P Global"),
    ("semi_index_pe", 32.8, "Philadelphia Semiconductor Index"),
    ("nvda_data_center_rev_pct", 91.4, "NVIDIA FY2026 Q4财报"),
    ("nvda_blackwell_shipment_pct", 71.0, "TrendForce 2026年预测"),
    ("nvda_capex_to_rev", 8.5, "NVIDIA FY2026财报"),
    ("nvda_free_cash_flow_yield", 5.5, "高盛测算"),
    ("nvda_peg_ratio", 0.61, "富国银行测算"),
]

# --- 2026-05-20 数据 (最新) ---
OBS_0520 = [
    ("nvda_pe", 45.02, "FinanceCharts/Macrotrends"),
    ("nvda_ps", 35.5, "CompaniesMarketCap"),
    ("nvda_revenue_growth", 80.0, "NVIDIA Q1 FY2027财报(5月28日发布)"),
    ("nvda_gross_margin", 73.1, "NVIDIA Q1 FY2027财报(5月28日发布)"),
    ("tsm_revenue_growth", 35.0, "台积电2026年Q1财报"),
    ("tsm_advanced_revenue_pct", 74.0, "台积电2026年Q1财报"),
    ("hbm_revenue_sk", 20.0, "SK海力士2026年Q1财报"),
    ("gpu_shipments", 1800.0, "摩根大通预测(2026年全年,花旗预测)"),
    ("cloud_capex_total", 8300.0, "TrendForce(九大云厂商2026年)"),
    ("cloud_ai_capex_pct", 75.0, "MUFG/IDC 2026年预测"),
    ("us_10y_yield", 4.46, "FRED (May 2026平均)"),
    ("us_cpi_yoy", 3.8, "美国劳工部(2026年4月)"),
    ("vix", 17.26, "TradingEconomics (May 2026)"),
    ("put_call_ratio", 0.88, "CBOE"),
    ("nasdaq_pe", 38.7, "S&P Global"),
    ("semi_index_pe", 32.5, "Philadelphia Semiconductor Index"),
    ("nvda_data_center_rev_pct", 91.4, "NVIDIA FY2026 Q4财报"),
    ("nvda_blackwell_shipment_pct", 71.0, "TrendForce 2026年预测"),
    ("nvda_capex_to_rev", 8.5, "NVIDIA FY2026财报"),
    ("nvda_free_cash_flow_yield", 5.8, "高盛测算"),
    ("nvda_peg_ratio", 0.56, "富国银行测算"),
]


def insert_batch(date: str, observations: list):
    """批量录入一批观测值"""
    print(f"\n{'='*60}")
    print(f"📅 {date}")
    print(f"{'='*60}")
    
    signal_defs = list_signal_definitions()
    inserted = 0
    
    for metric_key, value, source in observations:
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
            print(f"  ✓ {metric_key}: {value}")
            inserted += 1
        else:
            print(f"  ✗ {metric_key}: 未找到信号定义")
    
    # 信号灯评估
    print(f"\n🚦 信号灯评估:")
    for metric_key, value, source in observations:
        results = evaluate_signals_for_metric(metric_key, value, f"{date}T00:00:00")
        for ev in results:
            icon = "🟢" if ev["status"] == "positive" else ("🔴" if ev["status"] == "negative" else "⚪")
            print(f"  {icon} {ev['name']}: {ev['raw_value']} → {ev['status']}")
    
    # 衍生计算
    print(f"\n📈 衍生计算:")
    for metric_key, value, source in observations:
        deriv = compute_observation_derivatives(metric_key, f"{date}T00:00:00", value)
        if deriv["mom_pct"] is not None or deriv["yoy_pct"] is not None:
            mom = f"{deriv['mom_pct']:.1f}%" if deriv["mom_pct"] else "N/A"
            yoy = f"{deriv['yoy_pct']:.1f}%" if deriv["yoy_pct"] else "N/A"
            print(f"  ✓ {metric_key}: MoM={mom} YoY={yoy}")
        if deriv["is_anomaly"]:
            print(f"  ⚠️  {metric_key}: 异常检测 (z={deriv['z_score']:.2f})")
    
    # 综合评分
    score = compute_daily_score(date)
    if score:
        print(f"\n📊 综合评分: {score['total_score']} (🟢{score['positive_count']} 🔴{score['negative_count']} ⚪{score['neutral_count']})")
        print(f"  建议: {score['action_suggestion']}")
    
    return inserted


# 主程序
print("="*60)
print("📥 采集最近2周指标数据")
print("="*60)

total = 0
total += insert_batch("2026-05-06", OBS_0506)
total += insert_batch("2026-05-13", OBS_0513)
total += insert_batch("2026-05-20", OBS_0520)

print("\n" + "="*60)
print(f"✅ 录入完成！共 {total} 条观测值")
print("="*60)
