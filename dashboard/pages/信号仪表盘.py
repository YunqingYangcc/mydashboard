import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import (
    init_page_style, metric_card, render_signature,
    render_chain_map, render_phase_time_matrix, render_volume_price_chart,
    render_phase_detail, render_phase_badge,
)
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
from kb.market_constants import (
    PHASE_CONFIG, ALL_PHASES, BULLISH_PHASES, BEARISH_PHASES, NEUTRAL_PHASES,
    CHAIN_FLOW, CHAIN_COLORS, CHAIN_TARGETS, SYMBOL_MAP,
    TARGET_STOCKS, A_SHARE_SYMBOLS, US_SHARE_SYMBOLS, ETF_SYMBOLS,
)
from kb.volume_analyzer import (
    determine_market_phase, batch_determine_phases, determine_all_current,
    compute_chain_phase_summary, save_phases_to_db, get_phases_from_db,
)
from kb.data_fetcher import get_quotes_from_db, fetch_single_latest, batch_fetch_and_store
from kb.utils import now_iso

init_db()
init_page_style()

st.title("🚦 AI产业链行情阶段仪表盘")
st.caption("量在价先 · 8种可枚举行情阶段 · 20只标的全覆盖")

# ========== 加载行情阶段数据 ==========
@st.cache_data(ttl=300)
def load_all_phases():
    """加载所有标的的当前行情阶段"""
    return determine_all_current()

@st.cache_data(ttl=300)
def load_history_phases():
    """加载所有标的的最近5天行情阶段"""
    result = {}
    for target in TARGET_STOCKS:
        sym = target["symbol"]
        phases = get_phases_from_db(sym, days=5)
        if phases:
            result[sym] = phases
    return result

phases = load_all_phases()
history_phases = load_history_phases()
chain_summary = compute_chain_phase_summary(phases)

# ========== 区块1: 行情总览栏 ==========
st.subheader("📊 行情总览")

# 统计各阶段数量
phase_counts = {}
for sym, p in phases.items():
    phase = p.get("phase", "震荡")
    phase_counts[phase] = phase_counts.get(phase, 0) + 1

bullish_count = sum(phase_counts.get(p, 0) for p in BULLISH_PHASES)
bearish_count = sum(phase_counts.get(p, 0) for p in BEARISH_PHASES)
neutral_count = sum(phase_counts.get(p, 0) for p in NEUTRAL_PHASES)

# 整体行情判断
if bullish_count > bearish_count + neutral_count:
    overall_phase = "🟢 多头主导"
    overall_desc = "多数标的处于吸筹/拉升阶段"
elif bearish_count > bullish_count + neutral_count:
    overall_phase = "🔴 空头主导"
    overall_desc = "多数标的处于派发/下跌阶段"
else:
    overall_phase = "🟡 震荡分化"
    overall_desc = "多空分歧，结构性机会"

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("产业链行情", overall_phase, overall_desc)
with col2:
    metric_card("🟢 利好标的", bullish_count, f"吸筹/拉升/恐慌见底")
with col3:
    metric_card("🔴 利空标的", bearish_count, f"派发/见顶/下跌")
with col4:
    metric_card("🟡 中性标的", neutral_count, f"筑底/洗盘/震荡")
with col5:
    # 主导阶段
    if phase_counts:
        dominant = max(phase_counts, key=phase_counts.get)
        dom_config = PHASE_CONFIG.get(dominant, {})
        metric_card("主导阶段", f"{dom_config.get('emoji', '⚖️')} {dominant}",
                    f"共{phase_counts[dominant]}只标的")
    else:
        metric_card("主导阶段", "—", "无数据")

# 产业链维度得分
st.markdown("")
chain_cols = st.columns(len(CHAIN_FLOW))
for idx, chain in enumerate(CHAIN_FLOW):
    with chain_cols[idx % len(chain_cols)]:
        cs = chain_summary.get(chain, {})
        bullish = cs.get("bullish_count", 0)
        bearish = cs.get("bearish_count", 0)
        color = "#10B981" if bullish > bearish else ("#EF4444" if bearish > bullish else "#F59E0B")
        emoji = "🟢" if bullish > bearish else ("🔴" if bearish > bullish else "🟡")
        st.markdown(
            f'<div style="text-align:center;padding:8px;border-radius:10px;'
            f'background:{color}11;border:1px solid {color}33;">'
            f'<div style="font-size:0.75rem;color:#94a3b8;">{chain}</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{color};">{emoji} {cs.get("phase", "—")}</div>'
            f'<div style="font-size:0.68rem;color:#64748b;">多{bullish} 空{bearish}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# ========== 区块2: 产业链行情地图 ==========
st.divider()
st.subheader("🗺️ 产业链行情地图")

render_chain_map(phases)

# ========== 区块3: 行情阶段时序矩阵 ==========
st.divider()
st.subheader("📋 行情阶段时序矩阵")
st.caption("行=标的，列=最近5个交易日，观察行情阶段变化与产业链传导")

render_phase_time_matrix(phases, history_phases)

# ========== 区块4: 标的详情(交互) ==========
st.divider()
st.subheader("🔍 标的详情")

# 选择标的
all_options = {}
for t in TARGET_STOCKS:
    sym = t["symbol"]
    name = t["name"]
    market = t["market"]
    phase = phases.get(sym, {}).get("phase", "—")
    all_options[f"{t['chain']} | {market} | {name}({sym}) | {phase}"] = sym

selected_label = st.selectbox("选择标的", list(all_options.keys()), index=0)
selected_symbol = all_options[selected_label]

if selected_symbol:
    phase_data = phases.get(selected_symbol, {})

    col_detail, col_chart = st.columns([2, 3])

    with col_detail:
        render_phase_detail(phase_data)

    with col_chart:
        # 量价趋势图
        df = get_quotes_from_db(selected_symbol, days=120)
        if df is not None and len(df) >= 10:
            render_volume_price_chart(df, selected_symbol)
        else:
            st.info("暂无行情数据，请先获取历史数据")

# ========== 区块5: 产业景气信号(原有) ==========
st.divider()
st.subheader("📈 产业景气信号")
st.caption("CapEx/TSMC营收等产业景气指标，作为行情判定的辅助参考")

signal_defs = list_signal_definitions()
obs_list = latest_observation_map()
obs_map = {o["metric_key"]: o for o in obs_list}
latest_score = latest_signal_score()
dimensions = sorted({s["dimension"] for s in signal_defs}) if signal_defs else []

STATUS_STYLE = {
    "positive": ("🟢", "利好"),
    "negative": ("🔴", "利空"),
    "neutral":  ("🟡", "中性"),
}

if latest_score:
    with st.expander("📊 综合评分(产业景气)", expanded=False):
        total = latest_score.get("total_score", 0)
        action = latest_score.get("action_suggestion", "hold")
        dim_breakdown = latest_score.get("dimension_breakdown_json", {})
        if isinstance(dim_breakdown, str):
            import json
            try:
                dim_breakdown = json.loads(dim_breakdown)
            except Exception:
                dim_breakdown = {}

        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("产业景气得分", f"{total:+.2f}")
        with col2:
            if dim_breakdown:
                for dim, stats in dim_breakdown.items():
                    d_avg = stats.get("dim_avg_score", 0)
                    dim_color = "🟢" if d_avg > 0 else ("🔴" if d_avg < 0 else "🟡")
                    st.caption(f"**{dim}** {dim_color}{d_avg:+.2f}")

# 信号灯矩阵（保留原有）
recent_values = list_recent_signal_values(limit=200)
sig_latest = {}
for rv in recent_values:
    key = rv["signal_key"]
    if key not in sig_latest or rv["observed_at"] > sig_latest[key]["observed_at"]:
        sig_latest[key] = rv

if signal_defs:
    with st.expander("🚦 信号灯矩阵", expanded=False):
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
                        st.markdown(
                            f"<div style='border:1px solid rgba(120,120,140,0.18);border-radius:12px;padding:10px 12px;margin-bottom:8px;'>"
                            f"<div style='font-size:0.82rem;color:#9aa0aa;'>{sig['name']}</div>"
                            f"<div style='font-size:1.3rem;font-weight:700;'>⚪ {val_str}</div>"
                            f"<div style='font-size:0.78rem;color:#b6bac4;'>尚未评估</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

# ========== 区块6: 数据管理 ==========
st.divider()
with st.expander("⚙️ 数据管理", expanded=False):
    st.markdown("**行情数据管理** — 获取/刷新行情数据并判定行情阶段")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📡 刷新所有标的行情(120天)", use_container_width=True, type="primary"):
            with st.spinner("正在批量获取行情数据..."):
                results = batch_fetch_and_store(days=120, sleep_interval=0.5)
                total = sum(results.values())
                st.success(f"✅ 已获取 {len(results)} 只标的，共 {total} 条数据")
                # 重新判定行情阶段
                new_phases = determine_all_current()
                save_phases_to_db(new_phases)
                st.cache_data.clear()
                st.rerun()

    with col2:
        if st.button("🔍 重新判定所有行情阶段", use_container_width=True):
            with st.spinner("正在判定行情阶段..."):
                new_phases = determine_all_current()
                count = save_phases_to_db(new_phases)
                st.success(f"✅ 已判定 {count} 只标的的行情阶段")
                st.cache_data.clear()
                st.rerun()

    st.divider()
    st.markdown("**单只标的刷新**")
    refresh_options = {f"{t['name']}({t['symbol']})": t["symbol"] for t in TARGET_STOCKS}
    refresh_sel = st.selectbox("选择标的", list(refresh_options.keys()), key="refresh_sel")
    if st.button("🔄 刷新选中标的"):
        sym = refresh_options[refresh_sel]
        with st.spinner(f"正在刷新 {refresh_sel}..."):
            fetch_count = fetch_single_latest(sym, days=10)
            # 重新判定
            df = get_quotes_from_db(sym, days=120)
            if df is not None and len(df) >= 20:
                result = determine_market_phase(df)
                result["symbol"] = sym
                result["name"] = SYMBOL_MAP.get(sym, {}).get("name", sym)
                result["market"] = SYMBOL_MAP.get(sym, {}).get("market", "")
                result["chain"] = SYMBOL_MAP.get(sym, {}).get("chain", "")
                save_phases_to_db({sym: result})
                st.success(f"✅ {refresh_sel}: {result['emoji']} {result['phase']} - {result.get('reasoning', '')[:40]}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("数据不足，无法判定")

    # 原有数据录入
    st.divider()
    st.markdown("**指标录入** (原有信号系统)")
    with st.form("obs_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            metric_key = st.text_input("指标Key", placeholder="如 nvda_pe, us_10y_yield")
        with col2:
            value = st.number_input("数值", step=0.1, format="%f")
        with col3:
            observed_at = st.text_input("观测时间", placeholder="留空自动填充")

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
                results = evaluate_signals_for_metric(metric_key.strip(), value, obs_time)
                deriv = compute_observation_derivatives(metric_key.strip(), obs_time, value)
                claim_alerts = []
                for r in (results or []):
                    alerts = check_claims_for_signal_change(r["signal_key"], r["status"])
                    claim_alerts.extend(alerts)
                msg = "✅ 已录入"
                if results:
                    msg += f" · 评估 {len(results)} 个信号"
                if deriv.get("is_anomaly"):
                    msg += f" · ⚠️ 异常(z={deriv.get('z_score', 0):.1f})"
                st.success(msg)
                st.rerun()

# 侧边栏
with st.sidebar:
    render_signature()
