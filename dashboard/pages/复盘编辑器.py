"""复盘编辑器 - 周报/月报撰写"""
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style
from kb.storage import init_db, list_reviews, insert_review
from kb.utils import now_iso

init_db()
init_page_style()

st.title("📝 复盘编辑器")
st.caption("记录认知迭代，追踪成长轨迹")

# 复盘类型和周期
review_type = st.selectbox("复盘类型", ["周报", "月报", "季度复盘", "专项复盘"])
review_period = st.text_input("复盘周期", placeholder="如: 2025年第25周 或 2025年5月")

col1, col2 = st.columns([3, 1])

with col1:
    # 摘要
    summary = st.text_area("📌 本期摘要", placeholder="本期主要做了什么？有哪些关键进展？", height=100)

with col2:
    # 自评分
    score = st.slider("自我评分", 1, 10, 7)

# 反思
reflection = st.text_area("🤔 反思", placeholder="哪里做得好？哪里可以改进？学到了什么？", height=150)

# 下一步行动
next_actions = st.text_area("🎯 下一步行动", placeholder="接下来要做什么？有什么计划？", height=100)

# 提交按钮
if st.button("💾 保存复盘", type="primary"):
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
    else:
        st.warning("⚠️ 请填写复盘周期和摘要")

st.divider()

# 历史复盘列表
st.subheader("📚 历史复盘")

reviews = list_reviews(limit=50)
if not reviews:
    st.info("暂无复盘记录，开始撰写你的第一篇复盘吧！")
else:
    for r in reviews:
        with st.expander(f"{r['review_type']} | {r['review_period']} | ⭐ {r.get('score', '-')}", expanded=False):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**📌 摘要**")
                st.text(r.get("summary", ""))
                if r.get("reflection"):
                    st.markdown(f"**🤔 反思**")
                    st.text(r.get("reflection", ""))
                if r.get("next_actions"):
                    st.markdown(f"**🎯 下一步**")
                    st.text(r.get("next_actions", ""))
            with col2:
                st.caption(r.get("created_at", "")[:10])
