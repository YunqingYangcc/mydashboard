import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, metric_card, render_signature
from kb.storage import (
    init_db,
    insert_observation,
    latest_observation_map,
    list_signal_definitions,
    upsert_signal_definition,
    delete_signal_definition,
    list_recent_signal_values,
    list_observations_by_metric,
    evaluate_signals_for_metric,
    compute_daily_score,
    latest_signal_score,
    compute_observation_derivatives,
    list_derivatives_for_metric,
    list_anomaly_observations,
    list_signal_reports,
    link_claim_to_signal,
    unlink_claim_from_signal,
    get_claims_for_signal,
    get_signals_for_claim,
    check_claims_for_signal_change,
    list_claims,
)
from kb.utils import now_iso

init_db()
init_page_style()

st.title("🚦 信号仪表盘")
st.caption("通用数据跟踪与信号评估 · 支持任意领域")

# ========== 加载数据 ==========
signal_defs = list_signal_definitions()
obs_list = latest_observation_map()
obs_map = {o["metric_key"]: o for o in obs_list}  # 转为 dict 以 metric_key 为 key
latest_score = latest_signal_score()
dimensions = sorted({s["dimension"] for s in signal_defs}) if signal_defs else []

STATUS_STYLE = {
    "positive": ("🟢", "利好"),
    "negative": ("🔴", "利空"),
    "neutral":  ("🟡", "中性"),
}

ACTION_LABEL = {
    "strong_buy": "🟢 强烈看多",
    "buy": "📈 偏多",
    "hold": "⏸️ 观望",
    "sell": "📉 偏空",
    "strong_sell": "🔴 强烈看空",
}

# ========== 1. 综合评分 ==========
st.subheader("📊 综合评分")

if latest_score:
    total = latest_score.get("total_score", 0)
    pos = latest_score.get("positive_count", 0)
    neg = latest_score.get("negative_count", 0)
    neu = latest_score.get("neutral_count", 0)
    action = latest_score.get("action_suggestion", "hold")
    score_date = latest_score.get("score_date", "")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        score_color = "🟢" if total > 0 else ("🔴" if total < 0 else "🟡")
        metric_card(f"{score_color} 综合得分", f"{total:+.2f}", score_date)
    with col2:
        metric_card("🟢 利好", pos, "信号数")
    with col3:
        metric_card("🟡 中性", neu, "信号数")
    with col4:
        metric_card("🔴 利空", neg, "信号数")
    with col5:
        metric_card("动作建议", ACTION_LABEL.get(action, action), "")

    dim_breakdown = latest_score.get("dimension_breakdown_json", {})
    if isinstance(dim_breakdown, str):
        import json
        try:
            dim_breakdown = json.loads(dim_breakdown)
        except Exception:
            dim_breakdown = {}
    if dim_breakdown:
        dim_cols = st.columns(min(len(dim_breakdown), 5))
        for idx, (dim, stats) in enumerate(dim_breakdown.items()):
            with dim_cols[idx % len(dim_cols)]:
                d_pos = stats.get("positive", 0)
                d_neg = stats.get("negative", 0)
                d_neu = stats.get("neutral", 0)
                d_avg = stats.get("dim_avg_score", 0)
                dim_color = "🟢" if d_avg > 0 else ("🔴" if d_avg < 0 else "🟡")
                st.caption(f"**{dim}** {dim_color}{d_avg:+.2f}  🟢{d_pos} 🟡{d_neu} 🔴{d_neg}")
else:
    st.info("暂无评分数据，录入指标后点击「计算评分」生成")

# ========== 2. 信号灯矩阵 ==========
st.divider()
st.subheader("🚦 信号灯矩阵")

recent_values = list_recent_signal_values(limit=200)
sig_latest = {}
for rv in recent_values:
    key = rv["signal_key"]
    if key not in sig_latest or rv["observed_at"] > sig_latest[key]["observed_at"]:
        sig_latest[key] = rv

if not signal_defs:
    st.info("暂无信号定义，请在下方「信号配置」中添加")
else:
    for dim in dimensions:
        dim_sigs = [s for s in signal_defs if s["dimension"] == dim]
        st.markdown(f"**{dim}**")
        cols = st.columns(min(len(dim_sigs), 4))
        for idx, sig in enumerate(dim_sigs):
            with cols[idx % len(cols)]:
                sv = sig_latest.get(sig["signal_key"])
                if sv:
                    icon, label = STATUS_STYLE.get(sv.get("status", "neutral"), ("⚪", "无数据"))
                    raw = sv.get("raw_value", "-")
                    thr = sv.get("threshold", "-")
                    comp = ">" if sig["comparator"] == "gt" else "<"
                    score = sv.get("score", 0)
                    score_str = f"{score:+.2f}" if isinstance(score, float) else str(score)
                    st.markdown(
                        f"<div style='border:1px solid rgba(120,120,140,0.18);border-radius:12px;padding:10px 12px;margin-bottom:8px;'>"
                        f"<div style='font-size:0.82rem;color:#9aa0aa;'>{sig['name']}</div>"
                        f"<div style='font-size:1.3rem;font-weight:700;'>{icon} {raw}</div>"
                        f"<div style='font-size:0.78rem;color:#b6bac4;'>阈值 {comp}{thr} · {label} · 得分{score_str}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    obs = obs_map.get(sig["metric_key"])
                    val_str = obs.get('value', '-') if obs else '-'
                    sub_label = "尚未评估" if obs else "无数据"
                    st.markdown(
                        f"<div style='border:1px solid rgba(120,120,140,0.18);border-radius:12px;padding:10px 12px;margin-bottom:8px;'>"
                        f"<div style='font-size:0.82rem;color:#9aa0aa;'>{sig['name']}</div>"
                        f"<div style='font-size:1.3rem;font-weight:700;'>⚪ {val_str}</div>"
                        f"<div style='font-size:0.78rem;color:#b6bac4;'>{sub_label}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

# ========== 3. 异常数据提醒 ==========
anomalies = list_anomaly_observations(limit=10)
if anomalies:
    st.divider()
    st.subheader("⚠️ 异常数据提醒")
    for a in anomalies[:5]:
        z = a.get("z_score", 0) or 0
        direction = "↑" if z > 0 else "↓"
        st.warning(f"**{a['metric_key']}** 值={a['raw_value']} z-score={z:.1f}{direction} (偏离2个标准差)")

# ========== 4. 数据录入 ==========
st.divider()
with st.expander("📝 数据录入", expanded=False):
    st.markdown("**录入观测值**，系统自动评估关联信号 + 计算环比/异常")

    existing_keys = sorted({s["metric_key"] for s in signal_defs}) if signal_defs else []

    with st.form("obs_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            metric_key = st.text_input("指标Key", placeholder="如 nvda_pe, us_10y_yield")
        with col2:
            value = st.number_input("数值", step=0.1, format="%f")
        with col3:
            observed_at = st.text_input("观测时间（留空=当前）", placeholder="留空自动填充")

        col4, col5, col6 = st.columns(3)
        with col4:
            metric_name = st.text_input("指标名称", placeholder="如 NVDA PE(TTM)")
        with col5:
            unit = st.text_input("单位", placeholder="如 %, $, 倍")
        with col6:
            frequency = st.selectbox("频率", ["daily", "weekly", "monthly", "quarterly"], index=0)

        source = st.text_input("来源", placeholder="如 FMP, 手动录入")
        asset = st.text_input("资产/标的", placeholder="如 NVDA, SOX")

        if st.form_submit_button("💾 录入并评估", use_container_width=True):
            if not metric_key.strip():
                st.error("指标Key不能为空")
            else:
                obs_time = observed_at.strip() if observed_at.strip() else now_iso()
                insert_observation({
                    "metric_key": metric_key.strip(),
                    "metric_name": metric_name.strip() or metric_key.strip(),
                    "value": value,
                    "unit": unit.strip(),
                    "observed_at": obs_time,
                    "frequency": frequency,
                    "source": source.strip() or "manual",
                    "asset": asset.strip(),
                })
                # 自动评估关联信号
                results = evaluate_signals_for_metric(metric_key.strip(), value, obs_time)
                # 自动计算环比/异常
                deriv = compute_observation_derivatives(metric_key.strip(), obs_time, value)
                # 检查信号变化是否影响断言
                claim_alerts = []
                for r in (results or []):
                    alerts = check_claims_for_signal_change(r["signal_key"], r["status"])
                    claim_alerts.extend(alerts)

                msg = "✅ 已录入"
                if results:
                    msg += f" · 评估 {len(results)} 个信号"
                if deriv.get("is_anomaly"):
                    msg += f" · ⚠️ 异常(z={deriv.get('z_score', 0):.1f})"
                if claim_alerts:
                    msg += f" · 🧠 {len(claim_alerts)} 条断言待验证"
                st.success(msg)
                st.rerun()

    # 批量录入
    st.divider()
    st.markdown("**批量录入**（每行：`指标Key,数值`）")
    batch_text = st.text_area("批量数据", height=80, placeholder="nvda_pe,65.2\nus_10y_yield,4.5\nsox_pe,32.1")
    if st.button("📦 批量录入", use_container_width=True):
        now = now_iso()
        count = 0
        for line in batch_text.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    mk = parts[0].strip()
                    mv = float(parts[1].strip())
                    insert_observation({
                        "metric_key": mk, "metric_name": mk, "value": mv,
                        "observed_at": now, "frequency": "daily", "source": "batch",
                    })
                    evaluate_signals_for_metric(mk, mv, now)
                    compute_observation_derivatives(mk, now, mv)
                    count += 1
                except Exception:
                    pass
        if count:
            st.success(f"✅ 批量录入 {count} 条")
            st.rerun()

    st.divider()
    if st.button("📊 计算今日评分", use_container_width=True):
        result = compute_daily_score()
        if result:
            st.success(f"✅ 评分已更新：综合得分 {result['total_score']:+.2f}")
            st.rerun()
        else:
            st.warning("今日尚无信号数据，请先录入")

# ========== 5. 趋势图+衍生数据 ==========
with st.expander("📈 趋势图", expanded=False):
    all_metric_keys = sorted({s["metric_key"] for s in signal_defs} | {k for k in obs_map.keys()})
    if all_metric_keys:
        selected_metrics = st.multiselect("选择指标", all_metric_keys, default=all_metric_keys[:3])
        if selected_metrics:
            for mk in selected_metrics:
                history = list_observations_by_metric(mk, limit=60)
                if history:
                    df = pd.DataFrame(history)
                    df["observed_at"] = pd.to_datetime(df["observed_at"])
                    df = df.sort_values("observed_at")
                    chart_df = df[["observed_at", "value"]].set_index("observed_at")
                    unit_str = history[0].get("unit", "")
                    st.line_chart(chart_df, y_label=unit_str, use_container_width=True)

                    # 衍生数据
                    derivs = list_derivatives_for_metric(mk, limit=5)
                    if derivs:
                        d = derivs[0]
                        parts = [f"**{mk}** ({len(history)} 个数据点)"]
                        if d.get("mom_pct") is not None:
                            parts.append(f"环比 {d['mom_pct']:+.1f}%")
                        if d.get("yoy_pct") is not None:
                            parts.append(f"同比 {d['yoy_pct']:+.1f}%")
                        if d.get("z_score") is not None:
                            parts.append(f"z-score {d['z_score']:.1f}")
                        st.caption(" · ".join(parts))
                    else:
                        st.caption(f"**{mk}** ({len(history)} 个数据点)")
    else:
        st.info("暂无指标数据")

# ========== 6. AI 信号报告 ==========
with st.expander("🤖 AI 信号报告", expanded=False):
    st.markdown("AI 根据当前信号状态生成分析报告，含因果链解读和行动建议")

    # 历史报告
    reports = list_signal_reports(report_type="ai_weekly", limit=5)
    if reports:
        for r in reports:
            st.markdown(f"**{r['report_date']}** · 模型: {r.get('model', 'N/A')}")
            st.markdown(r["content"][:300] + "..." if len(r.get("content", "")) > 300 else r.get("content", ""))
            if st.button("📄 查看全文", key=f"report_{r['id']}"):
                st.markdown(r["content"])
            st.divider()

    # 生成新报告
    provider = st.selectbox("AI 模型", ["gold", "zhipu", "xiaomi", "siliconflow"], index=0)
    if st.button("🤖 生成 AI 报告", use_container_width=True):
        with st.spinner("AI 正在分析信号数据..."):
            from kb.ai import generate_signal_report
            result = generate_signal_report(provider=provider)
            if result["used_fallback"]:
                st.error(f"AI 调用失败: {result.get('reason', '未知')}")
            elif result["content"]:
                st.success(f"✅ 报告已生成 (模型: {result['model']})")
                st.markdown(result["content"])
                st.rerun()
            else:
                st.error("AI 返回为空")

# ========== 7. 断言-信号关联 ==========
with st.expander("🧠 断言-信号关联", expanded=False):
    st.markdown("关联断言到信号，信号变化时自动提醒验证断言")

    all_claims = list_claims(limit=50)

    if signal_defs and all_claims:
        col_a, col_b = st.columns(2)
        with col_a:
            claim_options = {f"#{c['id']} {c.get('subject', c.get('statement', '')[:30])}": c for c in all_claims}
            selected_claim = st.selectbox("选择断言", list(claim_options.keys()), key="link_claim_sel")
        with col_b:
            sig_options = {f"{s['signal_key']} - {s['name']}": s for s in signal_defs}
            selected_sig = st.selectbox("选择信号", list(sig_options.keys()), key="link_sig_sel")

        if st.button("🔗 关联断言与信号"):
            claim_id = claim_options[selected_claim]["id"]
            signal_key = sig_options[selected_sig]["signal_key"]
            link_claim_to_signal(claim_id, signal_key)
            st.success(f"✅ 已关联断言 #{claim_id} ↔ 信号 {signal_key}")
            st.rerun()

        # 显示已有断言-信号关联
        st.divider()
        st.markdown("**已有关联**")
        for sig in signal_defs:
            linked_claims = get_claims_for_signal(sig["signal_key"])
            if linked_claims:
                for c in linked_claims:
                    status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(
                        c.get("verification_status", "pending"), "⏳")
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.caption(f"  {status_icon} 断言#{c['id']} ↔ 信号 {sig['name']} · {c.get('subject', '')[:40]}")
                    with col2:
                        if st.button("❌", key=f"unlink_{c['id']}_{sig['signal_key']}", help="取消关联"):
                            unlink_claim_from_signal(c["id"], sig["signal_key"])
                            st.rerun()
    else:
        st.info("需要先有断言和信号定义才能关联")

# ========== 8. 信号配置 ==========
with st.expander("⚙️ 信号配置", expanded=False):
    st.markdown("信号 = **指标 + 阈值 + 比较器**，录入指标值后自动评估")

    with st.form("sig_form"):
        col1, col2 = st.columns(2)
        with col1:
            sig_key = st.text_input("信号Key", placeholder="如 nvda_pe_overvalued")
            sig_name = st.text_input("名称", placeholder="如 NVDA PE偏高")
            sig_dimension = st.text_input("维度/分组", placeholder="如 估值、需求、宏观")
        with col2:
            sig_metric_key = st.text_input("关联指标Key", placeholder="如 nvda_pe")
            sig_comparator = st.selectbox("比较器", ["gt", "lt"], index=0, help="gt=超过阈值不利, lt=低于阈值不利")
            sig_threshold = st.number_input("阈值", step=0.1, format="%f")
            sig_frequency = st.selectbox("频率", ["daily", "weekly", "monthly", "quarterly"], index=0)

        sig_desc = st.text_input("描述", placeholder="可选，信号含义说明")

        if st.form_submit_button("💾 保存信号", use_container_width=True):
            if not all([sig_key.strip(), sig_name.strip(), sig_dimension.strip(), sig_metric_key.strip()]):
                st.error("Key、名称、维度、指标Key 均不能为空")
            else:
                upsert_signal_definition({
                    "signal_key": sig_key.strip(), "name": sig_name.strip(),
                    "dimension": sig_dimension.strip(), "frequency": sig_frequency,
                    "comparator": sig_comparator, "threshold": sig_threshold,
                    "metric_key": sig_metric_key.strip(), "description": sig_desc.strip(),
                })
                st.success("✅ 信号已保存")
                st.rerun()

    if signal_defs:
        st.divider()
        st.markdown("**已有信号**")
        for dim in dimensions:
            dim_sigs = [s for s in signal_defs if s["dimension"] == dim]
            st.markdown(f"**{dim}** ({len(dim_sigs)})")
            for s in dim_sigs:
                col1, col2, col3 = st.columns([5, 2, 1])
                with col1:
                    comp_str = ">" if s["comparator"] == "gt" else "<"
                    st.caption(f"  {s['name']} — {s['metric_key']} {comp_str} {s['threshold']}")
                with col2:
                    st.caption(f"  {s.get('frequency', '')} · {s.get('description', '')}")
                with col3:
                    if st.button("🗑️", key=f"del_sig_{s['signal_key']}", help="删除"):
                        delete_signal_definition(s["signal_key"])
                        st.rerun()

# ========== 9. 最新观测值一览 ==========
with st.expander("📋 最新观测值", expanded=False):
    if obs_map:
        obs_list = list(obs_map.values()) if isinstance(obs_map, dict) else []
        if obs_list:
            df = pd.DataFrame(obs_list)
            show_cols = [c for c in ["metric_key", "metric_name", "value", "unit", "observed_at", "source", "asset"] if c in df.columns]
            st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("暂无观测数据")
    else:
        st.info("暂无观测数据")

# 侧边栏
with st.sidebar:
    render_signature()
