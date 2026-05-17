"""断言来源追溯 - 查看断言的证据和来源"""
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style
from kb.storage import init_db, list_claims, fetch_latest_documents

init_db()
init_page_style()

st.title("🔍 断言来源追溯")
st.caption("追踪每个判断的证据和来源")

# 获取断言和文档
claims = list_claims(limit=100)
docs = fetch_latest_documents(limit=200)

# 构建文档索引
doc_map = {str(d.get("id", "")): d for d in docs}

# 筛选
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.multiselect(
        "状态",
        options=["verified", "pending", "rejected"],
        default=["verified", "pending", "rejected"],
        format_func=lambda x: {"verified": "✅ 已验证", "pending": "⏳ 待验证", "rejected": "❌ 已驳回"}.get(x, x)
    )
with col2:
    claim_type = st.selectbox("类型", ["全部"] + list(set(c.get("claim_type", "") for c in claims if c.get("claim_type"))))
with col3:
    sort_by = st.selectbox("排序", ["最新", "状态", "类型"])

# 过滤断言
filtered_claims = [c for c in claims if c.get("verification_status", "pending") in status_filter]
if claim_type != "全部":
    filtered_claims = [c for c in filtered_claims if c.get("claim_type") == claim_type]

# 统计
col1, col2, col3, col4 = st.columns(4)
col1.metric("总数", len(filtered_claims))
col2.metric("✅ 已验证", len([c for c in filtered_claims if c.get("verification_status") == "verified"]))
col3.metric("⏳ 待验证", len([c for c in filtered_claims if c.get("verification_status") == "pending"]))
col4.metric("❌ 已驳回", len([c for c in filtered_claims if c.get("verification_status") == "rejected"]))

st.divider()

# 断言列表
st.subheader(f"📋 断言列表 ({len(filtered_claims)} 条)")

for claim in filtered_claims:
    status = claim.get("verification_status", "pending")
    status_icon = {"verified": "✅", "pending": "⏳", "rejected": "❌"}.get(status, "❓")
    
    with st.expander(f"{status_icon} {claim.get('statement', '')[:60]}...", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 基本信息
            st.markdown(f"**📝 断言内容**")
            st.text(claim.get("statement", ""))
            
            # 元信息
            meta = claim.get("metadata_json", {}) or {}
            
            if claim.get("source"):
                st.markdown(f"**📌 来源**: {claim.get('source')}")
            
            if claim.get("notes"):
                st.markdown(f"**📝 备注**: {claim.get('notes')}")
            
            if claim.get("topic"):
                st.markdown(f"**🏷️ 主题**: {claim.get('topic')}")
            
            if meta.get("evidence"):
                st.markdown(f"**📊 证据**: {meta.get('evidence')}")
            
            if meta.get("confidence"):
                st.markdown(f"**🎯 置信度**: {meta.get('confidence')}")
                
        with col2:
            st.caption(f"**类型**: {claim.get('claim_type', '未分类')}")
            st.caption(f"**状态**: {status_icon}")
            st.caption(f"**创建**: {str(claim.get('created_at', ''))[:10]}")
            if claim.get("updated_at"):
                st.caption(f"**更新**: {str(claim.get('updated_at', ''))[:10]}")
            
            # 关联文档
            source_doc_id = claim.get("source_document_id")
            if source_doc_id and str(source_doc_id) in doc_map:
                doc = doc_map[str(source_doc_id)]
                st.markdown("---")
                st.markdown(f"**📄 来源文档**")
                st.caption(doc.get("title", "未知文档"))
                st.text(doc.get("content", "")[:150] + "...")

# 图谱视角
st.divider()
st.subheader("🕸️ 断言关联图谱")

# 按主题分组统计
topic_stats = {}
for c in filtered_claims:
    topic = c.get("topic", "未分类")
    if topic not in topic_stats:
        topic_stats[topic] = {"total": 0, "verified": 0, "pending": 0, "rejected": 0}
    topic_stats[topic]["total"] += 1
    topic_stats[topic][c.get("verification_status", "pending")] += 1

if topic_stats:
    for topic, stats in sorted(topic_stats.items(), key=lambda x: -x[1]["total"]):
        with st.expander(f"🏷️ {topic} ({stats['total']}条)", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总数", stats["total"])
            col2.metric("✅", stats["verified"])
            col3.metric("⏳", stats["pending"])
            col4.metric("❌", stats["rejected"])
