import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, insert_progress_log, list_progress_logs, delete_progress_log
from kb.utils import now_iso

init_db()
init_page_style()

st.title("📍 进度跟踪")
st.caption("记录你的学习/工作进度，支持文本和时间")

# ===== 新增进度记录 =====
with st.expander("➕ 新增进度", expanded=True):
    with st.form("new_progress_form", clear_on_submit=True):
        content = st.text_area(
            "进度内容",
            height=100,
            placeholder="记录你完成的任务、学到的知识点...",
            key="progress_content"
        )
        col1, col2 = st.columns([2, 1])
        with col1:
            log_time = st.text_input(
                "时间（留空自动使用当前时间）",
                value="",
                placeholder="例如：2026-05-17 23:56 或留空",
                key="progress_time"
            )
        with col2:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("💾 保存进度", use_container_width=True)

        if submitted:
            if not content.strip():
                st.error("❌ 进度内容不能为空！")
            else:
                insert_progress_log(
                    content=content,
                    log_time=log_time.strip() if log_time.strip() else None
                )
                st.success("✅ 进度已保存！")
                st.rerun()

# ===== 进度列表 =====
st.divider()
st.subheader("📋 进度记录")

logs = list_progress_logs(limit=200)

if not logs:
    st.info("暂无进度记录，快来添加第一条吧！")
else:
    st.caption(f"共 {len(logs)} 条记录，最新在上面")

    for log in logs:
        log_id = log["id"]
        content = log["content"]
        log_time = log["log_time"]
        created_at = log["created_at"]

        # 显示每条记录
        col1, col2, col3 = st.columns([6, 3, 1])
        with col1:
            # 截取内容预览（前100字符）
            preview = content[:100] + "..." if len(content) > 100 else content
            st.markdown(f"**{preview}**")
        with col2:
            # 显示时间
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(log_time.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = log_time[:16] if len(log_time) >= 16 else log_time
            st.caption(f"🕐 {time_str}")
        with col3:
            # 删除按钮
            if st.button("🗑️", key=f"delete_{log_id}", help="删除此记录"):
                delete_progress_log(log_id)
                st.success("✅ 已删除")
                st.rerun()

        # 展开查看完整内容
        with st.expander("查看完整内容", expanded=False):
            st.write(content)
            st.caption(f"记录时间：{log_time} | 创建于：{created_at}")

        st.divider()

# 清空所有记录（危险操作）
st.divider()
with st.expander("⚠️ 危险操作", expanded=False):
    st.warning("清空后无法恢复！")
    if st.button("🗑️ 清空所有进度记录", use_container_width=True, type="primary"):
        from kb.storage import clear_progress_logs
        clear_progress_logs()
        st.success("✅ 已清空所有记录")
        st.rerun()

# 侧边栏
with st.sidebar:
    render_signature()
