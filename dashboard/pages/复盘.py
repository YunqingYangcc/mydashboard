"""复盘 - 记录认知迭代，追踪成长轨迹"""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, list_reviews, insert_review
from kb.utils import now_iso

init_db()
init_page_style()

st.title("🔄 复盘")
st.caption("记录认知迭代，追踪成长轨迹")

# ===== 创建新复盘 =====
st.markdown("### 📝 撰写复盘")

with st.form("review_form", clear_on_submit=True):
    # 复盘类型和周期
    col1, col2 = st.columns([2, 1])
    with col1:
        review_type = st.selectbox("复盘类型", ["周报", "月报", "季度复盘", "专项复盘"])
    with col2:
        score = st.slider("自我评分", 1, 10, 7, help="1=需要大幅改进，10=非常满意")
    
    review_period = st.text_input("复盘周期", placeholder="如: 2025年第25周 或 2025年5月", help="标识这次复盘的时间范围")
    
    st.divider()
    
    # 三个核心区域
    summary = st.text_area(
        "📌 本期摘要",
        placeholder="本期主要做了什么？有哪些关键进展和成果？",
        height=100,
        help="简要总结本期的核心内容和进展"
    )
    
    reflection = st.text_area(
        "🤔 深度反思",
        placeholder="• 哪些做得好？为什么？\n• 哪些可以改进？如何改进？\n• 学到了什么关键认知？",
        height=120,
        help="这是复盘的核心价值所在"
    )
    
    next_actions = st.text_area(
        "🎯 下一步行动",
        placeholder="• 接下来要做什么？\n• 有什么明确的计划和deadline？",
        height=80,
        help="将认知转化为行动"
    )
    
    st.divider()
    
    # 提交按钮
    submitted = st.form_submit_button("💾 保存复盘", type="primary", use_container_width=True)
    if submitted:
        if review_period and summary:
            insert_review({
                "review_type": review_type,
                "review_period": review_period,
                "summary": summary,
                "reflection": reflection,
                "next_actions": next_actions,
                "score": score
            })
            st.success("✅ 复盘已保存！")
            st.balloons()
            st.rerun()
        elif not review_period:
            st.error("⚠️ 请填写复盘周期")
        elif not summary:
            st.error("⚠️ 请填写本期摘要")

st.divider()

# ===== 历史复盘列表 =====
st.markdown("### 📚 历史复盘")

reviews = list_reviews(limit=50)
if not reviews:
    st.info("📝 暂无复盘记录，开始撰写你的第一篇复盘吧！")
else:
    # 统计信息
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("总复盘数", len(reviews))
    with col_stats2:
        avg_score = sum(r.get('score', 0) for r in reviews if r.get('score')) / len(reviews) if reviews else 0
        st.metric("平均评分", f"{avg_score:.1f}" if avg_score else "-")
    with col_stats3:
        latest = reviews[0].get('created_at', '')[:10] if reviews else "-"
        st.metric("最近复盘", latest)
    
    st.divider()
    
    # 复盘卡片列表
    for i, r in enumerate(reviews):
        # 根据评分设置颜色
        score = r.get('score', 0) or 0  # 处理None值
        if score >= 8:
            score_color = "#10b981"  # 绿色
        elif score >= 6:
            score_color = "#fbbf24"  # 黄色
        else:
            score_color = "#ef4444"  # 红色
        
        # 卡片布局
        with st.container():
            col_card1, col_card2 = st.columns([4, 1])
            
            with col_card1:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 4px;">
                        <span style="font-size: 1rem; font-weight: 600; color: #e2e8f0;">
                            {r['review_type']}
                        </span>
                        <span style="color: #64748b; margin: 0 8px;">·</span>
                        <span style="font-size: 0.95rem; color: #cbd5e1;">
                            {r['review_period']}
                        </span>
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 8px;">
                        📅 {r.get('created_at', '')[:10]}
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.5;">
                        {r.get('summary', '')[:100]}{'...' if len(r.get('summary', '')) > 100 else ''}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col_card2:
                st.markdown(
                    f"""
                    <div style="text-align: center; padding-top: 20px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: {score_color};">
                            {score if score else '-'}
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b;">
                            评分
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        # 展开详情按钮
        review_id = r.get('id') or i  # 获取ID，如果为None则使用索引
        if st.button("查看完整内容", key=f"view_{review_id}", use_container_width=True):
            st.session_state[f"show_review_{review_id}"] = not st.session_state.get(f"show_review_{review_id}", False)
        
        # 显示完整内容
        if st.session_state.get(f"show_review_{review_id}", False):
            with st.container():
                st.markdown("**📌 摘要**")
                st.write(r.get("summary", ""))
                
                if r.get("reflection"):
                    st.markdown("**🤔 反思**")
                    st.write(r.get("reflection", ""))
                
                if r.get("next_actions"):
                    st.markdown("**🎯 下一步行动**")
                    st.write(r.get("next_actions", ""))
        
        st.divider()

# 侧边栏签名
with st.sidebar:
    st.markdown("### 🔄 复盘指南")
    st.markdown(
        """
        **好的复盘应该包含：**
        
        1. **📌 摘要**：客观记录做了什么
        2. **🤔 反思**：深度思考和改进点
        3. **🎯 行动**：明确的下一步计划
        
        **频率建议：**
        - 周报：每周日晚上
        - 月报：每月最后一天
        - 季度复盘：每季度末
        """
    )
    st.divider()
    render_signature()
