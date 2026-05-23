"""UI组件库 - Notion暗色主题 + 行情阶段可视化

📋 Prompt绑定: prompts/展示绘图.md
修改本文件前必须先阅读该 prompt，确保改动符合区块布局、配色规范和组件接口定义。
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from kb.constants import (
    RENDER_MODE_IMAGE,
    RENDER_MODE_MARKDOWN,
    RENDER_MODE_TEXT,
    WATERMARK_TEXT,
)
from kb.market_constants import (
    PHASE_CONFIG, ALL_PHASES, BULLISH_PHASES, BEARISH_PHASES, NEUTRAL_PHASES,
    CHAIN_FLOW, CHAIN_COLORS, CHAIN_TARGETS, SYMBOL_MAP,
    TARGET_STOCKS, A_SHARE_SYMBOLS, US_SHARE_SYMBOLS, ETF_SYMBOLS,
)


def init_page_style(watermark_text: str = WATERMARK_TEXT) -> None:
    """
    统一的页面样式初始化，必须在每个页面的开头调用。
    """
    st.set_page_config(
        page_title="杨云清的个人知识库",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(
        """
        <style>
        /* ===== Notion风格 全局 ===== */
        .block-container { padding-top: 4rem; padding-bottom: 2rem; max-width: 96rem; }
        .stApp { background: #1a1a1a; }

        /* ===== 卡片 ===== */
        .yyq-card {
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 6px;
            padding: 16px 20px;
            background: #242424;
        }
        .yyq-card:hover { background: #2a2a2a; }
        .yyq-card-title {
            font-size: 2rem;
            color: #8c8c8c;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .yyq-card-value {
            font-size: 4.8rem;
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: 6px;
            color: #dfdfdf;
        }
        .yyq-card-desc { font-size: 2rem; color: #8c8c8c; }

        /* ===== 标签 ===== */
        .yyq-chip {
            display: inline-block; padding: 3px 8px; border-radius: 4px;
            font-size: 0.78rem; margin-right: 6px; margin-bottom: 6px;
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
            color: #bfbfbf;
        }

        /* ===== 面板 ===== */
        .yyq-panel {
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 6px; padding: 14px 16px; margin-bottom: 10px;
            background: #242424;
        }
        .yyq-panel:hover { background: #2a2a2a; }

        /* ===== 签名 ===== */
        .yyq-signature {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 6px; padding: 14px 16px; margin-top: 20px; text-align: center;
        }
        .yyq-signature-name {
            font-size: 0.85rem; font-weight: 600; color: #bfbfbf;
            letter-spacing: 0.08em; margin-bottom: 4px;
        }
        .yyq-signature-desc {
            font-size: 0.68rem; color: rgba(191,191,191,0.4); letter-spacing: 0.05em;
        }

        /* ===== Streamlit 原生元素 ===== */
        h1 { font-weight: 600 !important; color: #e6e6e6 !important; }
        h2 { font-weight: 600 !important; color: #dfdfdf !important; }
        h3 { font-weight: 500 !important; color: #bfbfbf !important; font-size: 1rem !important; }
        hr { border-color: rgba(255,255,255,0.06) !important; margin: 1rem 0 !important; }
        [data-testid="stMetricValue"] { color: #dfdfdf !important; font-weight: 600 !important; }
        [data-testid="stMetricLabel"] { color: #8c8c8c !important; }

        /* 侧边栏 */
        [data-testid="stSidebar"] {
            background: #1d1d1d !important;
            border-right: 1px solid rgba(255,255,255,0.05) !important;
        }

        /* 输入框 */
        input, textarea {
            border-radius: 6px !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            font-size: 0.9rem !important;
            padding: 10px 12px !important;
            background: #242424 !important;
            color: #e6e6e6 !important;
        }
        input:focus, textarea:focus {
            border-color: rgba(100,130,150,0.5) !important;
            box-shadow: none !important;
        }
        input[type="text"] { min-height: 40px !important; }
        textarea { min-height: 120px !important; line-height: 1.6 !important; }
        ::placeholder { color: #5a5a5a !important; }

        /* 按钮 */
        .stButton > button {
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-size: 0.85rem !important;
        }

        /* 选择框 */
        .stSelectbox [data-baseweb="select"] { border-radius: 6px !important; }
        [data-testid="stDataFrame"] { border-radius: 6px !important; overflow: hidden !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_signature() -> None:
    """渲染侧边栏签名卡片"""
    st.markdown("---", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="yyq-signature">
            <div class="yyq-signature-name">杨云清</div>
            <div class="yyq-signature-desc">认知升级 · 投资精进</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


def metric_card(title: str, value, desc: str = "") -> None:
    st.markdown(
        f"""
        <div class="yyq-card">
            <div class="yyq-card-title">{title}</div>
            <div class="yyq-card-value">{value}</div>
            <div class="yyq-card-desc">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chips(items: list[str]) -> None:
    if not items:
        st.caption("暂无标签")
        return
    html = "".join([f'<span class="yyq-chip">{item}</span>' for item in items])
    st.markdown(html, unsafe_allow_html=True)


def show_table(rows: list[dict], height: int | None = None) -> None:
    if not rows:
        st.info("暂无数据")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=height)


def render_signal_summary(score: dict) -> None:
    positive = score.get("positive_count", 0)
    negative = score.get("negative_count", 0)
    neutral = score.get("neutral_count", 0)
    action = score.get("action_suggestion", "尚未生成")
    st.markdown('<div class="yyq-panel">', unsafe_allow_html=True)
    st.markdown(f"**动作建议**: {action}")
    col1, col2, col3 = st.columns(3)
    col1.metric("正向", positive)
    col2.metric("负向", negative)
    col3.metric("中性", neutral)
    st.markdown("</div>", unsafe_allow_html=True)


def render_notes_list(notes: list[dict], chapter: str = "") -> None:
    """
    渲染笔记列表，使用卡片式布局（纯展示，不包含跳转按钮）
    notes: 笔记列表，每个笔记包含 id, subject, statement, created_at 等字段
    chapter: 章节名称（可选，用于显示）
    """
    if not notes:
        st.info("暂无笔记")
        return
    
    for note in notes:
        subject = note.get("subject") or note.get("statement", "")[:40]
        statement = note.get("statement", "")[:100]  # 预览前100个字符
        created_at = note.get("created_at", "")
        
        # 使用卡片样式渲染每条笔记（纯展示）
        st.markdown(
            f"""
            <div class="yyq-panel" style="margin-bottom: 10px;">
                <div style="font-size: 0.9rem; font-weight: 600; color: #e2e8f0; margin-bottom: 6px;">
                    📝 {subject}
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px; line-height: 1.4;">
                    {statement}...
                </div>
                <div style="font-size: 0.75rem; color: #64748b;">
                    📅 {created_at}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_document_preview(document: dict | None) -> None:
    if not document:
        st.info("请选择一篇文档")
        return

    metadata = document.get("metadata_json", {}) or {}
    tags = document.get("tags_json", []) or {}

    st.markdown(f"### {document.get('title', '未命名文档')}")

    render_mode = metadata.get("render_mode", RENDER_MODE_TEXT)
    absolute_path = metadata.get("absolute_path")

    if render_mode == RENDER_MODE_MARKDOWN:
        content = document.get("content", "")
        # 分离出 Mermaid 图表并利用 streamlit_mermaid 渲染
        import re
        from streamlit_mermaid import st_mermaid
        
        parts = re.split(r'```mermaid(.*?)```', content, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if i % 2 == 1:
                # 这是 mermaid 代码块
                try:
                    st_mermaid(part.strip(), height=400)
                except Exception as e:
                    st.error(f"渲染 Mermaid 图表失败: {e}")
            else:
                # 普通 markdown 文本，修复 $ 符号渲染问题
                if part.strip():
                    st.markdown(part.replace('$', r'\$'))
                    
    elif render_mode == RENDER_MODE_IMAGE and absolute_path and Path(absolute_path).exists():
        st.image(absolute_path, use_container_width=True)
        st.caption(absolute_path)
    else:
        st.text_area("正文", document.get("content", ""), height=360)


# ===== 行情阶段组件 =====

def render_phase_badge(phase: str, size: str = "normal") -> str:
    """渲染行情阶段色标徽章HTML

    Args:
        phase: 行情阶段名称
        size: small/normal/large
    """
    config = PHASE_CONFIG.get(phase, PHASE_CONFIG.get("震荡", {}))
    emoji = config.get("emoji", "⚖️")
    bg = config.get("bg_color", "#2D2D2D")
    text_color = config.get("text_color", "#9CA3AF")
    label = config.get("label", phase)

    if size == "small":
        return (f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;'
                f'background:{bg};color:{text_color};font-size:0.72rem;font-weight:600;">'
                f'{emoji} {label}</span>')
    elif size == "large":
        return (f'<span style="display:inline-block;padding:8px 16px;border-radius:12px;'
                f'background:{bg};color:{text_color};font-size:1.1rem;font-weight:700;">'
                f'{emoji} {phase}</span>')
    else:
        return (f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;'
                f'background:{bg};color:{text_color};font-size:0.85rem;font-weight:600;">'
                f'{emoji} {label}</span>')


def render_phase_matrix_cell(phase: str) -> str:
    """渲染行情阶段矩阵单元格HTML"""
    config = PHASE_CONFIG.get(phase, PHASE_CONFIG.get("震荡", {}))
    emoji = config.get("emoji", "⚖️")
    bg = config.get("bg_color", "#2D2D2D")
    text_color = config.get("text_color", "#9CA3AF")

    return (f'<td style="text-align:center;padding:14px 10px;background:{bg};'
            f'border-radius:10px;min-width:96px;">'
            f'<span style="font-size:3rem;">{emoji}</span><br/>'
            f'<span style="font-size:1.6rem;color:{text_color};">{phase[:2]}</span>'
            f'</td>')


def render_chain_card(target: dict, phase_data: dict = None) -> str:
    """渲染产业链中的标的卡片HTML

    Args:
        target: 标的配置 dict (from TARGET_STOCKS)
        phase_data: 行情阶段判定结果 dict
    """
    symbol = target["symbol"]
    name = target["name"]
    market = target["market"]
    chain = target["chain"]

    # 行情阶段
    if phase_data:
        phase = phase_data.get("phase", "震荡")
        config = PHASE_CONFIG.get(phase, PHASE_CONFIG.get("震荡", {}))
        emoji = config.get("emoji", "⚖️")
        bg = config.get("bg_color", "#2D2D2D")
        text_color = config.get("text_color", "#9CA3AF")
        label = config.get("label", phase)
        vol_ratio = phase_data.get("vol_ratio", "-")
        change_pct = phase_data.get("price_change_pct")
        change_str = f"{change_pct:+.1f}%" if isinstance(change_pct, (int, float)) else "-"

        vol_ratio_str = f"{vol_ratio:.1f}x" if isinstance(vol_ratio, (int, float)) else "-"
    else:
        emoji = "⚪"
        bg = "#1A1D23"
        text_color = "#6B7280"
        label = "无数据"
        vol_ratio_str = "-"
        change_str = "-"

    # 市场标签颜色
    market_badge = {
        "A股": ("#1E3A5F", "#60A5FA"),
        "美股": ("#1B4332", "#34D399"),
        "ETF": ("#3B2F1E", "#FBBF24"),
    }.get(market, ("#2D2D2D", "#9CA3AF"))

    return (
        f'<div style="border:1px solid rgba(120,120,140,0.18);border-radius:14px;padding:18px 20px;'
        f'margin-bottom:10px;background:linear-gradient(135deg,{bg}22,rgba(255,255,255,0.01));'
        f'min-height:120px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'<span style="font-size:2.8rem;font-weight:700;color:#e2e8f0;">{emoji} {name}</span>'
        f'<span style="font-size:1.3rem;padding:4px 12px;border-radius:6px;background:{market_badge[0]};color:{market_badge[1]};">{market}</span>'
        f'</div>'
        f'<div style="font-size:2.3rem;color:{text_color};font-weight:600;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:1.8rem;color:#94a3b8;">量比 {vol_ratio_str} · 涨跌 {change_str}</div>'
        f'</div>'
    )


def render_chain_map(phases: dict) -> None:
    """渲染产业链行情地图 - 横向流程图

    Args:
        phases: {symbol: phase_result} from determine_all_current
    """
    chain_flow = CHAIN_FLOW

    for chain in chain_flow:
        targets = CHAIN_TARGETS.get(chain, [])
        if not targets:
            continue

        chain_color = CHAIN_COLORS.get(chain, "#6B7280")

        # 计算环节整体状态
        chain_phases = []
        for t in targets:
            sym = t["symbol"]
            if sym in phases:
                chain_phases.append(phases[sym]["phase"])

        bullish = sum(1 for p in chain_phases if p in BULLISH_PHASES)
        bearish = sum(1 for p in chain_phases if p in BEARISH_PHASES)
        overall = "🟢" if bullish > bearish else ("🔴" if bearish > bullish else "🟡")

        # 环节标题
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;margin-top:14px;">'
            f'<span style="font-size:3rem;font-weight:700;color:{chain_color};">'
            f'{overall} {chain}</span>'
            f'<span style="font-size:1.8rem;color:#64748b;">多{bullish} 空{bearish}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        # 标的卡片 - 分A股/美股两排
        a_targets = [t for t in targets if t["market"] == "A股"]
        us_targets = [t for t in targets if t["market"] == "美股"]
        etf_targets = [t for t in targets if t["market"] == "ETF"]

        all_groups = []
        if a_targets:
            all_groups.append(("A股", a_targets))
        if us_targets:
            all_groups.append(("美股", us_targets))
        if etf_targets:
            all_groups.append(("ETF", etf_targets))

        for group_name, group_targets in all_groups:
            cards_html = ""
            for t in group_targets:
                phase_data = phases.get(t["symbol"])
                cards_html += render_chain_card(t, phase_data)

            st.markdown(
                f'<div style="margin-bottom:4px;">'
                f'<span style="font-size:0.7rem;color:#64748b;margin-left:4px;">{group_name}</span>'
                f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px;">'
                f'{cards_html}'
                f'</div></div>',
                unsafe_allow_html=True
            )


def render_phase_time_matrix(phases: dict, history_phases: dict = None) -> None:
    """渲染行情阶段时序矩阵

    行=标的(按产业链分组), 列=最近5个交易日

    Args:
        phases: {symbol: phase_result}
        history_phases: {symbol: [phase_result_5d]} 最近5天的阶段数据
    """
    if history_phases is None:
        history_phases = {}

    # 收集最近5个交易日
    all_dates = set()
    for sym, phase_list in history_phases.items():
        for p in phase_list:
            if p.get("trade_date"):
                all_dates.add(p["trade_date"])
    dates = sorted(all_dates)[-5:]

    if not dates:
        st.info("暂无历史行情阶段数据")
        return

    # 构建矩阵数据
    for chain in CHAIN_FLOW:
        targets = CHAIN_TARGETS.get(chain, [])
        if not targets:
            continue

        st.markdown(f'<span style="font-size:0.85rem;font-weight:600;color:{CHAIN_COLORS.get(chain, "#6B7280")};">{chain}</span>', unsafe_allow_html=True)

        # 表头
        header_html = '<tr><td style="padding:6px 10px;font-size:1.6rem;color:#94a3b8;font-weight:600;">标的</td>'
        for d in dates:
            short_date = d[5:] if len(d) >= 10 else d  # MM-DD
            header_html += f'<td style="text-align:center;padding:6px;font-size:1.5rem;color:#94a3b8;">{short_date}</td>'
        header_html += '</tr>'

        # 数据行
        rows_html = ""
        for t in targets:
            sym = t["symbol"]
            name = t["name"]
            market_tag = {"A股": "🇨🇳", "美股": "🇺🇸", "ETF": "📊"}.get(t["market"], "")

            row_html = f'<tr><td style="padding:6px 10px;font-size:1.7rem;color:#e2e8f0;white-space:nowrap;">{market_tag}{name}</td>'

            sym_history = history_phases.get(sym, [])
            for d in dates:
                # 找到该日期的阶段
                day_phase = None
                for ph in sym_history:
                    if ph.get("trade_date") == d:
                        day_phase = ph.get("phase", "震荡")
                        break

                if day_phase:
                    row_html += render_phase_matrix_cell(day_phase)
                else:
                    row_html += '<td style="text-align:center;padding:6px 4px;color:#374151;">—</td>'

            row_html += '</tr>'
            rows_html += row_html

        st.markdown(
            f'<div style="overflow-x:auto;margin-bottom:12px;">'
            f'<table style="width:100%;border-collapse:separate;border-spacing:3px;">'
            f'{header_html}{rows_html}'
            f'</table></div>',
            unsafe_allow_html=True
        )


def render_volume_price_chart(df: pd.DataFrame, symbol: str) -> None:
    """渲染量价趋势双轴图

    上半区: 价格折线 + MA5/MA20
    下半区: 成交量柱状图 + 20日均量线

    Args:
        df: DataFrame with OHLCV data (from compute_indicators)
        symbol: 标的代码
    """
    if df is None or len(df) < 5:
        st.info("数据不足，无法绘制量价图")
        return

    from kb.volume_analyzer import compute_indicators

    df = compute_indicators(df)

    target = SYMBOL_MAP.get(symbol, {})
    name = target.get("name", symbol)

    # 取最近60天
    plot_df = df.tail(60).copy()

    if len(plot_df) == 0:
        st.info("无可用数据")
        return

    # === 价格图 ===
    price_data = {}
    if "close" in plot_df.columns:
        price_data["收盘价"] = plot_df["close"].values
    if "ma5" in plot_df.columns:
        ma5_vals = plot_df["ma5"].values
        price_data["MA5"] = ma5_vals
    if "ma20" in plot_df.columns:
        price_data["MA20"] = plot_df["ma20"].values

    if price_data:
        price_chart_df = pd.DataFrame(price_data, index=plot_df["trade_date"].values)
        st.line_chart(price_chart_df, use_container_width=True, height=220)

    # === 成交量图 ===
    vol_data = {}
    if "volume" in plot_df.columns:
        vol_data["成交量"] = plot_df["volume"].values
    if "vol_ma20" in plot_df.columns:
        vol_data["20日均量"] = plot_df["vol_ma20"].values

    if vol_data:
        vol_chart_df = pd.DataFrame(vol_data, index=plot_df["trade_date"].values)
        st.line_chart(vol_chart_df, use_container_width=True, height=160)

    # 量能异动日标注
    if "vol_ratio" in plot_df.columns:
        anomaly_days = plot_df[plot_df["vol_ratio"] > 2.0]
        if len(anomaly_days) > 0:
            dates_str = ", ".join(anomaly_days["trade_date"].values[-5:])
            st.caption(f"⚡ 近期放量异动日: {dates_str}")


def render_phase_detail(phase_data: dict) -> None:
    """渲染行情阶段详情面板

    Args:
        phase_data: 行情阶段判定结果
    """
    phase = phase_data.get("phase", "震荡")
    config = PHASE_CONFIG.get(phase, PHASE_CONFIG.get("震荡", {}))

    # 大字展示当前阶段
    st.markdown(
        f'<div style="text-align:center;padding:20px;margin-bottom:16px;'
        f'background:{config.get("bg_color", "#2D2D2D")};border-radius:16px;'
        f'border:1px solid {config.get("text_color", "#9CA3AF")}33;">'
        f'<div style="font-size:2.5rem;">{config.get("emoji", "⚖️")}</div>'
        f'<div style="font-size:1.5rem;font-weight:700;color:{config.get("text_color", "#9CA3AF")};">{phase}</div>'
        f'<div style="font-size:0.9rem;color:#b6bac4;margin-top:6px;">{config.get("label", "")}</div>'
        f'<div style="font-size:0.82rem;color:#9aa0aa;margin-top:4px;">口诀: {config.get("formula", "")}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # 判定依据
    st.markdown("**📋 判定依据**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"量能条件: {phase_data.get('vol_condition', '—')}")
    with col2:
        st.markdown(f"价格条件: {phase_data.get('price_condition', '—')}")

    # 中间指标
    st.markdown("**📊 量能指标**")
    vol_ratio = phase_data.get("vol_ratio")
    price_pos = phase_data.get("price_position")
    change_pct = phase_data.get("price_change_pct")

    col1, col2, col3 = st.columns(3)
    with col1:
        vr_str = f"{vol_ratio:.1f}x" if isinstance(vol_ratio, (int, float)) else "—"
        vr_color = "🟢" if isinstance(vol_ratio, (int, float)) and vol_ratio > 1.5 else (
            "🔴" if isinstance(vol_ratio, (int, float)) and vol_ratio < 0.5 else "🟡"
        )
        st.metric("量比", f"{vr_color} {vr_str}")
    with col2:
        pp_str = f"{price_pos:.0%}" if isinstance(price_pos, (int, float)) else "—"
        st.metric("价格位置(60日)", pp_str)
    with col3:
        ch_str = f"{change_pct:+.1f}%" if isinstance(change_pct, (int, float)) else "—"
        st.metric("当日涨跌", ch_str)

    # 操作建议
    st.markdown("**🎯 操作建议**")
    st.info(f"👉 {config.get('action', '观望')}")

    # 投资者关注点
    st.markdown("**👁️ 投资者关注**")
    st.caption(phase_data.get("attention", config.get("attention", "")))

    # 判定理由
    reasoning = phase_data.get("reasoning", "")
    if reasoning:
        st.markdown("**🔍 判定理由**")
        st.caption(reasoning)
