import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, list_claims, update_claim, insert_claim, delete_claim
from kb.utils import now_iso

init_db()
init_page_style()

# 读取跳转参数（从其他页面通过 session_state 传递，如知识库页面点击关联笔记）
jump_chapter = st.session_state.get("jump_chapter", None)
# 使用后清除，避免重复触发
if "jump_chapter" in st.session_state:
    del st.session_state["jump_chapter"]

st.title("🔄 学习笔记")
st.caption("个人断言笔记的展示、统计、修改、筛选与分类")

# ===== 章节选项 =====
CHAPTER_OPTIONS = [
    "全部章节",
    "未分类",
    "P0-基础设施/AI芯片",
    "P0-基础设施/AI芯片/GPU训练",
    "P0-基础设施/AI芯片/GPU推理",
    "P0-基础设施/AI芯片/存算一体",
    "P0-基础设施/AI芯片/Chiplet",
    "P0-基础设施/AI芯片/光互联",
    "P0-基础设施/云计算",
    "P0-基础设施/边缘计算",
    "P1-能源/新能源",
    "P1-能源/储能",
    "P1-制造/半导体",
    "P1-制造/机器人",
    "P2-应用/自动驾驶",
    "P2-应用/具身智能",
    "P2-应用/AI Agent",
    "P3-认知/思维模型",
    "P3-认知/投资框架",
    "P3-认知/学习方法",
]

# 录入时可选的章节（不含"未分类"和"全部章节"）
CHAPTER_OPTIONS_FOR_INPUT = CHAPTER_OPTIONS[2:]

CLAIM_TYPES = ["belief", "prediction", "observation"]
STATUS_OPTIONS = ["pending", "validated", "invalidated"]

# ===== 录入新断言 =====
st.divider()
with st.expander("➕ 录入新断言", expanded=True):
    with st.form("new_claim_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            new_type = st.selectbox("类型", CLAIM_TYPES, index=0)
            new_chapter = st.selectbox("章节", CHAPTER_OPTIONS_FOR_INPUT, index=0)
            new_subject = st.text_input("主题", placeholder="例如：NVDA GPU架构")
        with col2:
            new_statement = st.text_area("陈述", height=100, placeholder="你的断言内容...")
        
        col3, col4 = st.columns(2)
        with col3:
            new_source = st.text_input("来源", placeholder="信息来源（如有）")
        with col4:
            new_status = st.selectbox("初始状态", STATUS_OPTIONS, index=2)
        
        if st.form_submit_button("💾 保存断言", use_container_width=True):
            if not new_statement.strip():
                st.error("❌ 陈述不能为空！")
            else:
                payload = {
                    "claim_type": new_type,
                    "chapter": new_chapter,
                    "subject": new_subject.strip() or None,
                    "statement": new_statement.strip(),
                    "verification_status": new_status,
                    "source": new_source.strip() or None,
                }
                insert_claim(payload)
                st.success("✅ 断言已保存！")
                st.rerun()

# ===== 筛选栏 =====
st.divider()
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    # 如果从其他页面跳转过来并携带 chapter 参数，自动选中
    if jump_chapter and jump_chapter in CHAPTER_OPTIONS:
        chapter_idx = CHAPTER_OPTIONS.index(jump_chapter)
    else:
        chapter_idx = 0
    chapter_filter = st.selectbox("章节", CHAPTER_OPTIONS, index=chapter_idx)

with filter_col2:
    status_filter = st.selectbox("状态", ["全部", "✅ 已验证", "❌ 已驳回", "⏳ 待验证"], index=0)

with filter_col3:
    type_filter = st.selectbox("类型", ["全部"] + CLAIM_TYPES, index=0)

with filter_col4:
    sort_by = st.selectbox("排序", ["最新更新", "最早更新", "章节/主题"], index=0)

# ===== 统计数据 =====
all_claims = list_claims(limit=500)
total = len(all_claims)

status_map = {"✅ 已验证": "validated", "❌ 已驳回": "invalidated", "⏳ 待验证": "pending"}

filtered_claims = all_claims

# 按章节筛选
if chapter_filter != "全部章节":
    if chapter_filter == "未分类":
        filtered_claims = [c for c in filtered_claims if not c.get("chapter")]
    else:
        filtered_claims = [c for c in filtered_claims if c.get("chapter") == chapter_filter]

# 按状态筛选
if status_filter != "全部":
    status_value = status_map[status_filter]
    filtered_claims = [c for c in filtered_claims if c.get("verification_status") == status_value]

# 按类型筛选
if type_filter != "全部":
    filtered_claims = [c for c in filtered_claims if c.get("claim_type") == type_filter]

# 排序
if sort_by == "最新更新":
    filtered_claims.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
elif sort_by == "最早更新":
    filtered_claims.sort(key=lambda x: x.get("updated_at", ""))
elif sort_by == "章节/主题":
    filtered_claims.sort(key=lambda x: (x.get("chapter") or "zzz", x.get("subject") or ""))

# ===== 统计卡片 =====
st.divider()
stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

validated = len([c for c in all_claims if c.get("verification_status") == "validated"])
invalidated = len([c for c in all_claims if c.get("verification_status") == "invalidated"])
pending = len([c for c in all_claims if c.get("verification_status") == "pending"])

stat_col1.metric("总数", total)
stat_col2.metric("✅ 已验证", validated)
stat_col3.metric("❌ 已驳回", invalidated)
stat_col4.metric("⏳ 待验证", pending)

st.divider()

# ===== 断言列表 =====
st.subheader(f"📝 断言笔记 ({len(filtered_claims)})")

if not filtered_claims:
    st.info("暂无断言笔记")
else:
    for claim in filtered_claims:
        claim_id = claim.get("id")
        status = claim.get("verification_status", "pending")
        claim_type = claim.get("claim_type", "")
        
        # 状态图标
        status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(status, "⏳")
        type_icon = {"belief": "💭", "prediction": "🔮", "observation": "👁️"}.get(claim_type, "📄")
        
        with st.expander(f"{status_icon} {type_icon} {claim.get('subject', claim.get('statement', '')[:30])} - {claim.get('updated_at', '')[:10]}", expanded=False):
            # 编辑表单
            with st.form(f"edit_claim_{claim_id}"):
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    edit_type = st.selectbox("类型", CLAIM_TYPES, index=CLAIM_TYPES.index(claim_type) if claim_type in CLAIM_TYPES else 0, key=f"type_{claim_id}")
                    edit_chapter = st.selectbox("章节", CHAPTER_OPTIONS[1:], index=0 if not claim.get("chapter") else (CHAPTER_OPTIONS[1:].index(claim.get("chapter")) + 1 if claim.get("chapter") in CHAPTER_OPTIONS[1:] else 0), key=f"chapter_{claim_id}")
                    edit_subject = st.text_input("主题", value=claim.get("subject") or "", key=f"subject_{claim_id}")
                with edit_col2:
                    edit_status = st.selectbox("状态", STATUS_OPTIONS, index=STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 2, key=f"status_{claim_id}")
                    edit_statement = st.text_area("陈述", value=claim.get("statement", ""), height=80, key=f"statement_{claim_id}")
                
                edit_col3, edit_col4 = st.columns(2)
                with edit_col3:
                    edit_source = st.text_input("来源", value=claim.get("source") or "", key=f"source_{claim_id}")
                    edit_validation_note = st.text_input("验证备注", value=claim.get("validation_note") or "", key=f"val_note_{claim_id}")
                with edit_col4:
                    edit_topic = st.text_input("话题标签", value=claim.get("topic") or "", key=f"topic_{claim_id}")
                
                if st.form_submit_button("💾 保存修改", use_container_width=True):
                    payload = {
                        "claim_type": edit_type,
                        "chapter": edit_chapter if edit_chapter != "未分类" else None,
                        "subject": edit_subject.strip() or None,
                        "statement": edit_statement.strip(),
                        "verification_status": edit_status,
                        "source": edit_source.strip() or None,
                        "validation_note": edit_validation_note.strip() or None,
                        "topic": edit_topic.strip() or None,
                    }
                    update_claim(claim_id, payload)
                    st.success("✅ 已保存修改")
                    st.rerun()
            
            # 删除按钮（放在表单外面）
            st.divider()
            if st.button("🗑️ 删除此断言", key=f"delete_{claim_id}"):
                delete_claim(claim_id)
                st.success("✅ 已删除")
                st.rerun()
            
            # 元信息
            st.caption(f"章节: {claim.get('chapter', '-')} | 更新: {claim.get('updated_at', '')[:16]}")

# ===== 分类视图 =====
st.divider()
st.subheader("📂 按章节分类")

# 获取所有章节
chapters = {}
for c in all_claims:
    chapter = c.get("chapter") or "未分类"
    if chapter not in chapters:
        chapters[chapter] = {"total": 0, "validated": 0, "invalidated": 0, "pending": 0}
    chapters[chapter]["total"] += 1
    status = c.get("verification_status", "pending")
    if status in chapters[chapter]:
        chapters[chapter][status] += 1

# 按章节层级排序
def chapter_sort_key(x):
    parts = x[0].split("/")
    return (len(parts), parts)

sorted_chapters = sorted(chapters.items(), key=chapter_sort_key)

for chapter, stats in sorted_chapters:
    with st.expander(f"**{chapter}** ({stats['total']}) - ✅{stats['validated']} ❌{stats['invalidated']} ⏳{stats['pending']}"):
        chapter_claims = [c for c in all_claims if (c.get("chapter") or "未分类") == chapter]
        
        # 按主题分组
        subjects = {}
        for c in chapter_claims:
            subject = c.get("subject") or "未分类主题"
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(c)
        
        # 按主题排序
        for subject in sorted(subjects.keys()):
            subject_claims = subjects[subject]
            v = len([x for x in subject_claims if x.get("verification_status") == "validated"])
            inv = len([x for x in subject_claims if x.get("verification_status") == "invalidated"])
            p = len([x for x in subject_claims if x.get("verification_status") == "pending"])
            st.markdown(f"**├ 📁 {subject}** ({len(subject_claims)}) - ✅{v} ❌{inv} ⏳{p}")
            for c in subject_claims:
                status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(c.get("verification_status", "pending"), "⏳")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└ {status_icon} {c.get('statement', '')}")

# 侧边栏
with st.sidebar:
    render_signature()
