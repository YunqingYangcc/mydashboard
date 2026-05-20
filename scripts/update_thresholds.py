#!/usr/bin/env python3
"""
阈值校准脚本 - 基于多AI专家建议
生成时间: 2026-05-20
"""
from kb.storage import init_db, get_knowledge_db

init_db()

# ========== 阈值更新清单 ==========
# 格式: (signal_key, 当前阈值, 新阈值, 专家建议来源)
UPDATES = [
    # ===== 估值专家建议 =====
    ("nvda_pe", 60.0, 50.0, "估值专家: PE 50约对应NVDA近3年75%分位"),
    ("nvda_ps", 25.0, 30.0, "估值专家: PS 30约对应历史70-80%分位"),
    ("nvda_peg_ratio", 2.0, 1.5, "估值专家: PEG>1.5即增长难以消化估值"),
    ("nvda_free_cash_flow_yield", 3.0, 3.5, "估值专家: 3.5可更早发现现金流恶化"),
    ("nasdaq_pe", 35.0, 37.0, "估值专家: 37约对应历史80%分位"),
    ("semi_index_pe", 30.0, 32.0, "估值专家: 32约对应历史75%分位"),
    
    # ===== 基本面专家建议 =====
    ("nvda_revenue_growth", 20.0, 40.0, "基本面专家: 40%区分普通增长与超强增长"),
    ("nvda_gross_margin", 70.0, 72.0, "基本面专家: 72%保留Blackwell爬坡缓冲"),
    ("nvda_data_center_rev_pct", 75.0, 80.0, "基本面专家: 80%更好监测多元化风险"),
    ("nvda_capex_to_rev", 15.0, 18.0, "基本面专家: 18%区分正常与过度投资"),
    ("nvda_qoq_growth", 5.0, 8.0, "基本面专家: 8%与高增长环境匹配"),
    ("nvda_analyst_spread", 20.0, 25.0, "基本面专家: 减少噪音信号"),
    
    # ===== 需求专家建议 =====
    ("tsm_revenue_growth", 20.0, 28.0, "需求专家: 28%作为AI需求边际放缓预警线"),
    ("tsm_advanced_revenue_pct", 60.0, 70.0, "需求专家: 70%反映先进制程结构性变化"),
    ("hbm_revenue_sk", 15.0, 18.0, "需求专家: 18B作为HBM需求下限"),
    ("gpu_shipments", 800.0, 1000.0, "需求专家: 千万片新平台分水岭"),
    ("cloud_capex_total", 5000.0, 7500.0, "需求专家: 7500亿反映2026年新常态"),
    ("cloud_ai_capex_pct", 50.0, 60.0, "需求专家: 60%区分AI投入意愿"),
    ("cloud_capex_growth", 15.0, 25.0, "需求专家: 25%作为需求拐点预警"),
    ("hbm_supply_gap", 5.0, 3.0, "需求专家: 3%更早捕捉供需平衡转折"),
    ("nvda_blackwell_shipment_pct", 50.0, 40.0, "需求专家: 40%避免换代爬坡期误判"),
    
    # ===== 宏观情绪专家建议 =====
    ("us_10y_yield", 4.5, 4.3, "宏观专家: 4.3%反映限制性利率实际压力位"),
    ("vix", 25.0, 20.0, "宏观专家: VIX>20即市场开始紧张"),
    ("nvda_put_call", 1.5, 1.2, "宏观专家: 个股PutCall波动更大"),
]

print("=" * 70)
print("阈值校准更新")
print("=" * 70)

with get_knowledge_db() as db:
    for signal_key, old_threshold, new_threshold, reason in UPDATES:
        # 更新阈值
        db.execute(
            "UPDATE signal_definitions SET threshold = ? WHERE signal_key = ?",
            (new_threshold, signal_key)
        )
        print(f"✓ {signal_key}: {old_threshold} → {new_threshold}")
        print(f"  理由: {reason}")

    db.commit()
    print("\n" + "=" * 70)
    print(f"✅ 已更新 {len(UPDATES)} 个阈值")
    print("=" * 70)

    # 验证更新
    print("\n验证更新结果:")
    cursor = db.execute("SELECT signal_key, threshold FROM signal_definitions ORDER BY signal_key")
    sigs = cursor.fetchall()
    for s in sigs:
        print(f"  {s['signal_key']}: {s['threshold']}")
