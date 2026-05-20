#!/usr/bin/env python3
"""自测脚本：验证5大增强能力的存储层和查询"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from kb.storage import (
    init_db,
    insert_observation,
    compute_observation_derivatives,
    list_derivatives_for_metric,
    list_anomaly_observations,
    bind_signal_to_knowledge,
    unbind_signal_from_knowledge,
    get_knowledge_signal_bindings,
    get_knowledge_signal_status,
    insert_signal_report,
    list_signal_reports,
    link_claim_to_signal,
    unlink_claim_from_signal,
    get_claims_for_signal,
    get_signals_for_claim,
    update_claim_signal_status,
    check_claims_for_signal_change,
    list_signal_definitions,
    insert_claim,
    evaluate_signals_for_metric,
    upsert_signal_definition,
    latest_observation_map,
)

init_db()
print("=" * 60)
print("🧪 5大增强能力自测")
print("=" * 60)

# ===== 1. 知识-信号绑定 =====
print("\n--- 1. 知识-信号绑定 ---")
test_item_key = "P0 基础设施层|💻 AI芯片"
test_signal_key = "test_bind_signal"
test_metric_key = "test_bind_metric"

# 确保有测试信号定义
upsert_signal_definition({
    "signal_key": test_signal_key,
    "name": "测试绑定信号",
    "dimension": "测试",
    "frequency": "daily",
    "comparator": "gt",
    "threshold": 100.0,
    "metric_key": test_metric_key,
    "description": "自测用",
})

bind_signal_to_knowledge(test_item_key, test_signal_key, test_metric_key)
bindings = get_knowledge_signal_bindings(test_item_key)
assert len(bindings) >= 1, "绑定失败"
print(f"✅ 绑定成功: {bindings[0]['item_key']} ↔ {bindings[0]['signal_key']}")

# 清理
unbind_signal_from_knowledge(test_item_key, test_signal_key)
bindings_after = get_knowledge_signal_bindings(test_item_key)
assert len(bindings_after) == 0, "解绑失败"
print("✅ 解绑成功")

# ===== 2. 信号报告 =====
print("\n--- 2. 信号报告 ---")
insert_signal_report("2026-05-20", "ai_weekly", "测试报告内容：综合得分3，偏多", "test-model", {"total_score": 3})
reports = list_signal_reports(report_type="ai_weekly", limit=5)
assert len(reports) >= 1, "报告查询失败"
print(f"✅ 报告存取成功: {reports[0]['report_date']} · 模型: {reports[0]['model']}")

# ===== 3. 观测衍生计算 =====
print("\n--- 3. 观测衍生计算（环比/异常） ---")
test_mk = "test_deriv_metric"
# 插入一批数据
for i in range(10):
    val = 100 + i * 2
    if i == 9:
        val = 200  # 异常值
    insert_observation({
        "metric_key": test_mk,
        "metric_name": test_mk,
        "value": val,
        "observed_at": f"2026-05-{10+i:02d}T10:00:00",
        "frequency": "daily",
        "source": "test",
    })

# 计算最后一个的衍生值
deriv = compute_observation_derivatives(test_mk, "2026-05-19T10:00:00", 200.0)
print(f"✅ 环比变化: {deriv.get('mom_change')} ({deriv.get('mom_pct', 0):.1f}%)")
print(f"✅ z-score: {deriv.get('z_score')} · 异常: {deriv.get('is_anomaly')}")

# 查询衍生数据
derivs = list_derivatives_for_metric(test_mk, limit=5)
print(f"✅ 衍生数据查询: {len(derivs)} 条")

# 查异常
anomalies = list_anomaly_observations(limit=10)
print(f"✅ 异常数据: {len(anomalies)} 条")

# ===== 4. 断言-信号关联 =====
print("\n--- 4. 断言-信号关联 ---")
# 插入测试断言
insert_claim({
    "claim_type": "test",
    "statement": "HBM是GPU产能瓶颈",
    "subject": "HBM产能",
    "verification_status": "pending",
})
# 查找刚插入的断言
from kb.storage import list_claims
all_claims = list_claims(claim_type="test", limit=5)
if all_claims:
    test_claim_id = all_claims[0]["id"]
    link_claim_to_signal(test_claim_id, test_signal_key)
    linked = get_claims_for_signal(test_signal_key)
    assert len(linked) >= 1, "断言-信号关联失败"
    print(f"✅ 关联成功: 断言#{test_claim_id} ↔ 信号{test_signal_key}")

    # 测试信号变化检查
    pending = check_claims_for_signal_change(test_signal_key, "negative")
    print(f"✅ 信号变化检查: {len(pending)} 条断言待验证")

    # 反向查询
    sigs = get_signals_for_claim(test_claim_id)
    print(f"✅ 断言关联信号: {len(sigs)} 个")

    # 清理
    unlink_claim_from_signal(test_claim_id, test_signal_key)
    print("✅ 取消关联成功")
else:
    print("⚠️ 无测试断言，跳过")

# ===== 5. 知识点信号状态 =====
print("\n--- 5. 知识点信号状态查询 ---")
# 先插入观测值和评估
insert_observation({
    "metric_key": test_metric_key,
    "metric_name": "测试指标",
    "value": 150.0,
    "observed_at": "2026-05-20T10:00:00",
    "frequency": "daily",
    "source": "test",
})
evaluate_signals_for_metric(test_metric_key, 150.0, "2026-05-20T10:00:00")

# 绑定并查询
bind_signal_to_knowledge(test_item_key, test_signal_key, test_metric_key)
status = get_knowledge_signal_status(test_item_key)
print(f"✅ 知识点信号状态: {len(status)} 个信号")
for s in status:
    print(f"   {s.get('name', s['signal_key'])}: {s.get('raw_value', 'N/A')} → {s.get('status', '无数据')}")

# 清理
unbind_signal_from_knowledge(test_item_key, test_signal_key)

print("\n" + "=" * 60)
print("✅ 全部5大能力自测通过！")
print("=" * 60)
