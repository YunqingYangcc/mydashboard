"""🧠 零散记忆章节 - 时间线+章节分组"""
import sys
from pathlib import Path
from datetime import datetime
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, list_claims, insert_claim, update_claim, delete_claim

init_db()
init_page_style()

st.title("🧠 零散记忆")

# ===== 顶栏统计 =====
all_notes = list_claims(limit=999)
total = len(all_notes)
chapters_all = set()
for c in all_notes:
    ch = c.get("chapter") or "未分类"
    chapters_all.add(ch)
chapter_list = sorted(chapters_all, key=lambda x: ("未分类" if x == "未分类" else x))

col1, col2, col3 = st.columns([1, 1, 4])
with col1: st.metric("记忆条数", total)
with col2: st.metric("章节数", len(chapter_list))
with col3: st.caption("")  # spacer

# ===== 快速录入框（Always on top）=====
with st.expander("✍️ 记一条碎片记忆", expanded=False):
    with st.form("quick_memo", clear_on_submit=True):
        c1, c2 = st.columns([8, 1.2])
        with c1:
            txt = st.text_area("", placeholder="「NVDA 推理卡提前半年...」「AI 应用最大卡点是大模型幻觉...」「美光 HBM 定价权正在向 supplier 转移...」",
                               label_visibility="collapsed", height=80)
        with c2:
            ch = st.selectbox("章", chapter_list if chapter_list else ["未分类"],
                            index=0 if "未分类" not in chapter_list else chapter_list.index("未分类"),
                            label_visibility="collapsed")
            btn = st.form_submit_button("📥 记下", use_container_width=True, type="primary")
        if btn and txt.strip():
            insert_claim({
                "claim_type": "observation",
                "chapter": None if ch == "未分类" else ch,
                "statement": txt.strip()
            })
            st.rerun()

st.divider()

# ===== 章节分组展示（时间线风格）=====
if not all_notes:
    st.info("🧠 还没有记忆碎片，点击上方「记一条碎片记忆」开始")
else:
    # 按章节分组
    notes_by_chapter = {}
    for n in all_notes:
        ch = n.get("chapter") or "未分类"
        notes_by_chapter.setdefault(ch, []).append(n)

    # 按更新时间排序：有最新笔记的章节排前面
    chapter_order = sorted(notes_by_chapter.keys(),
                          key=lambda ch: max(n.get("updated_at", "") or "" for n in notes_by_chapter[ch]),
                          reverse=True)

    for ch_name in chapter_order:
        notes = notes_by_chapter[ch_name]
        # 章内按更新时间倒序
        notes.sort(key=lambda n: n.get("updated_at", "") or "", reverse=True)
        last_updated = notes[0].get("updated_at", "")[:10] if notes[0].get("updated_at") else ""

        with st.expander(f"📂 {ch_name}  ·  {len(notes)}条", expanded=False):
            st.caption(f"最近更新：{last_updated}")
            st.markdown("<br>", unsafe_allow_html=True)

            for i, n in enumerate(notes):
                cid = n["id"]
                stt = n.get("verification_status", "pending")
                txt2 = n.get("statement", "")
                upd = (n.get("updated_at", "") or "")[:16]

                # 状态图标
                icon = "✅" if stt == "validated" else ("❌" if stt == "invalidated" else "⏳")

                # 卡片容器
                card_html = f"""
                <div style="background:#f8f9fa;border-left:3px solid {'#22c55e' if stt=='validated' else '#ef4444' if stt=='invalidated' else '#eab308'};
                            padding:12px 16px;margin-bottom:10px;border-radius:0 8px 8px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div style="flex:1;font-size:0.95rem;line-height:1.6;color:#1e293b;">{txt2}</div>
                        <div style="display:flex;gap:6px;margin-left:12px;flex-shrink:0;">
                            <span style="font-size:0.8rem;color:#94a3b8;white-space:nowrap;">{upd}</span>
                            <span style="font-size:0.9rem;">{icon}</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

                # 行内操作（状态切换+编辑+删除）
                op_col1, op_col2, op_col3, op_col4 = st.columns([1, 1, 1, 6])
                with op_col1:
                    if st.button("✅ 验证", key=f"val_{cid}", use_container_width=True):
                        update_claim(cid, {"verification_status": "validated"})
                        st.rerun()
                with op_col2:
                    if st.button("❌ 驳回", key=f"inv_{cid}", use_container_width=True):
                        update_claim(cid, {"verification_status": "invalidated"})
                        st.rerun()
                with op_col3:
                    if st.button("⏳ 待定", key=f"pen_{cid}", use_container_width=True):
                        update_claim(cid, {"verification_status": "pending"})
                        st.rerun()
                with op_col4:
                    with st.popover("✏️ 编辑"):
                        et = st.text_area("修改内容", value=txt2, key=f"e_{cid}", label_visibility="collapsed", height=100)
                        c_save, c_del = st.columns([1, 1])
                        if c_save.button("💾 保存", key=f"save_{cid}", use_container_width=True):
                            update_claim(cid, {"statement": et.strip()})
                            st.rerun()
                        if c_del.button("🗑 删除", key=f"del_{cid}", use_container_width=True):
                            delete_claim(cid)
                            st.rerun()

                # 非最后一条加分隔
                if i < len(notes) - 1:
                    st.markdown(
                        '<div style="height:1px;background:#e2e8f0;margin:4px 0 8px 0;"></div>',
                        unsafe_allow_html=True
                    )

with st.sidebar:
    render_signature()

    # 侧边栏快速浏览：各章节条数一览
    st.markdown("### 📊 记忆分布")
    total_all = len(all_notes)
    for ch_name in chapter_order:
        cnt = len(notes_by_chapter[ch_name])
        pct = cnt / total_all * 100 if total_all > 0 else 0
        bar_color = "#3b82f6"
        st.markdown(
            f"""
            <div style="margin-bottom:4px;">
                <div style="display:flex;justify-content:space-between;font-size:0.8rem;">
                    <span>{ch_name}</span>
                    <span>{cnt}条</span>
                </div>
                <div style="background:#e2e8f0;height:6px;border-radius:3px;">
                    <div style="background:{bar_color};height:6px;border-radius:3px;width:{pct}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
