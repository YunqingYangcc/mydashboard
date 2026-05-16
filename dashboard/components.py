from pathlib import Path

import pandas as pd
import streamlit as st

from kb.constants import (
    RENDER_MODE_IMAGE,
    RENDER_MODE_MARKDOWN,
    RENDER_MODE_TEXT,
    WATERMARK_TEXT,
)


def init_page_style(watermark_text: str = WATERMARK_TEXT) -> None:
    """
    统一的页面样式初始化，必须在每个页面的开头调用。
    """
    st.set_page_config(
        page_title="杨云清 Dashboard",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .yyq-card {
            border: 1px solid rgba(120, 120, 140, 0.18);
            border-radius: 16px;
            padding: 16px 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
            min-height: 112px;
        }
        .yyq-card-title {
            font-size: 0.92rem;
            color: #9aa0aa;
            margin-bottom: 8px;
        }
        .yyq-card-value {
            font-size: 1.9rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 8px;
        }
        .yyq-card-desc {
            font-size: 0.88rem;
            color: #b6bac4;
        }
        .yyq-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            margin-right: 6px;
            margin-bottom: 6px;
            border: 1px solid rgba(120, 120, 140, 0.24);
        }
        .yyq-panel {
            border: 1px solid rgba(120, 120, 140, 0.18);
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 14px;
        }
        .yyq-watermark {
            position: fixed;
            right: 18px;
            bottom: 10px;
            font-size: 11px;
            color: rgba(148, 163, 184, 0.15);
            letter-spacing: 0.2em;
            z-index: 9999;
            pointer-events: none;
            user-select: none;
        }
        .yyq-signature {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(139, 92, 246, 0.08));
            border: 1px solid rgba(139, 92, 246, 0.15);
            border-radius: 12px;
            padding: 14px 16px;
            margin-top: 24px;
            text-align: center;
        }
        .yyq-signature-name {
            font-size: 0.95rem;
            font-weight: 600;
            color: #a5b4fc;
            letter-spacing: 0.15em;
            margin-bottom: 4px;
        }
        .yyq-signature-desc {
            font-size: 0.72rem;
            color: rgba(165, 180, 252, 0.5);
            letter-spacing: 0.08em;
        }
        .yyq-divider {
            border: none;
            border-top: 1px solid rgba(139, 92, 246, 0.12);
            margin: 16px 0;
        }
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


def render_document_preview(document: dict | None) -> None:
    if not document:
        st.info("请选择一篇文档")
        return

    metadata = document.get("metadata_json", {}) or {}
    tags = document.get("tags_json", []) or []

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
