import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, list_claims, update_claim_validation

init_db()
init_page_style()

st.title("🧠 认知闭环")
st.caption("个人断言笔记的展示、统计、修改、筛选与分类")

# ===== 筛选栏 =====
st.divider()
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    status_filter = st.selectbox(
        "状态",
        ["全部", "✅ 已验证", "❌ 已驳回", "⏳ 待验证"],
        index=0
    )

with filter_col2:
    type_filter = st.selectbox(
        "类型",
        ["全部", "belief", "prediction", "observation"],
        index=0
    )

with filter_col3:
    sort_by = st.selectbox(
        "排序",
        ["最新更新", "最早更新", "主题"],
        index=0
    )

# ===== 统计数据 =====
all_claims = list_claims(limit=500)
total = len(all_claims)

status_map = {"✅ 已验证": "validated", "❌ 已驳回": "invalidated", "⏳ 待验证": "pending"}
type_map = {"belief": "belief", "prediction": "prediction", "observation": "observation"}

filtered_claims = all_claims

# 按状态筛选
if status_filter != "全部":
    status_value = status_map[status_filter]
    filtered_claims = [c for c in filtered_claims if c.get("validation_status") == status_value]

# 按类型筛选
if type_filter != "全部":
    type_value = type_map[type_filter]
    filtered_claims = [c for c in filtered_claims if c.get("claim_type") == type_value]

# 排序
if sort_by == "最新更新":
    filtered_claims.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
elif sort_by == "最早更新":
    filtered_claims.sort(key=lambda x: x.get("updated_at", ""))
elif sort_by == "主题":
    filtered_claims.sort(key=lambda x: x.get("subject", ""))

# ===== 统计卡片 =====
st.divider()
stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

validated = len([c for c in all_claims if c.get("validation_status") == "validated"])
invalidated = len([c for c in all_claims if c.get("validation_status") == "invalidated"])
pending = len([c for c in all_claims if c.get("validation_status") == "pending"])

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
        status = claim.get("validation_status", "pending")
        claim_type = claim.get("claim_type", "")
        
        # 状态图标
        status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(status, "⏳")
        type_icon = {"belief": "💭", "prediction": "🔮", "observation": "👁️"}.get(claim_type, "📄")
        
        with st.expander(f"{status_icon} {type_icon} {claim.get('subject', '未知主题')} - {claim.get('updated_at', '')[:10]}", expanded=False):
            # 断言内容
            st.markdown(f"**陈述：** {claim.get('statement', '')}")
            
            # 验证状态与备注
            validate_col1, validate_col2 = st.columns([1, 2])
            
            with validate_col1:
                new_status = st.selectbox(
                    "验证状态",
                    ["pending", "validated", "invalidated"],
                    index=["pending", "validated", "invalidated"].index(status) if status in ["pending", "validated", "invalidated"] else 0,
                    key=f"status_{claim_id}",
                    label_visibility="collapsed"
                )
                
                if new_status != status:
                    if st.button("💾 保存状态", key=f"save_{claim_id}"):
                        note = st.session_state.get(f"note_{claim_id}", "")
                        update_claim_validation(claim_id, new_status, note if new_status == "invalidated" else None)
                        st.success("已保存")
                        st.rerun()
            
            with validate_col2:
                validation_note = st.text_input(
                    "备注",
                    value=claim.get("validation_note", ""),
                    placeholder="驳回原因或验证说明...",
                    key=f"note_{claim_id}",
                    label_visibility="collapsed"
                )
            
            # 元信息
            st.caption(f"类型: {claim_type} | 主题: {claim.get('subject', '-')} | 更新: {claim.get('updated_at', '')[:16]}")

# ===== 分类视图 =====
st.divider()
st.subheader("📂 按主题分类")

# 获取所有主题
subjects = {}
for c in all_claims:
    subject = c.get("subject", "未分类")
    if subject not in subjects:
        subjects[subject] = {"total": 0, "validated": 0, "invalidated": 0, "pending": 0}
    subjects[subject]["total"] += 1
    status = c.get("validation_status", "pending")
    if status in subjects[subject]:
        subjects[subject][status] += 1

# 按数量排序
sorted_subjects = sorted(subjects.items(), key=lambda x: x[1]["total"], reverse=True)

for subject, stats in sorted_subjects:
    with st.expander(f"**{subject}** ({stats['total']}) - ✅{stats['validated']} ❌{stats['invalidated']} ⏳{stats['pending']}"):
        subject_claims = [c for c in all_claims if c.get("subject") == subject]
        for c in subject_claims:
            status_icon = {"validated": "✅", "invalidated": "❌", "pending": "⏳"}.get(c.get("validation_status", "pending"), "⏳")
            st.markdown(f"- {status_icon} {c.get('statement', '')}")

# 侧边栏
with st.sidebar:
    render_signature()
