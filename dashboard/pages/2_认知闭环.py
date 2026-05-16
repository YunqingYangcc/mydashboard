import sys
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import chips, init_page_style, metric_card, section_title, show_table
from kb.storage import (
    fetch_latest_documents, 
    init_db, 
    list_extracted_claims_by_document_key,
    list_extracted_relations_by_document_key
)

init_page_style()
init_db()

st.title("认知闭环 (Cognitive Loop)")
st.caption("没有测验和输出的输入是无效的。在这里回顾你的输入，并自动生成给 AI 导师的测验 Prompt。")

# Fetch documents
all_docs = fetch_latest_documents(limit=100)
today_str = datetime.now().strftime("%Y-%m-%d")

today_docs = []
historical_docs = []
notes_docs = []

for doc in all_docs:
    # Use created_at or doc_date
    created_at = doc.get("created_at", "")
    if created_at.startswith(today_str):
        today_docs.append(doc)
    else:
        historical_docs.append(doc)
        
    metadata = doc.get("metadata_json") or {}
    if metadata.get("user_note"):
        notes_docs.append(doc)

tab1, tab2, tab3, tab4 = st.tabs(["当日认知输入", "历史认知沉淀", "汇总与出题闭环 (AI 测验)", "我的学习笔记"])

with tab1:
    section_title("今日新增", "你今天输入了哪些高质量文档")
    if not today_docs:
        st.info("今天还没有新增的文档。赶快去 inbox 里丢点新思考吧！")
    else:
        for doc in today_docs:
            with st.expander(f"📄 {doc.get('title')} ({doc.get('source_name')})"):
                doc_key = doc.get("document_key") or doc.get("hash", "")
                claims = list_extracted_claims_by_document_key(doc_key)
                if claims:
                    st.markdown("**抽取的判断：**")
                    for c in claims:
                        st.markdown(f"- {c.get('statement')}")
                else:
                    st.write((doc.get("summary") or doc.get("content") or "")[:200] + "...")

with tab2:
    section_title("历史沉淀", "你过去积累的研究文档")
    if not historical_docs:
        st.info("暂无历史文档。")
    else:
        show_table(
            [
                {
                    "Title": doc.get("title"),
                    "Source": doc.get("source_name"),
                    "Date": doc.get("created_at", "")[:10]
                }
                for doc in historical_docs[:20]
            ],
            height=400
        )

with tab3:
    section_title("生成 AI 测验 Prompt", "拿汇总去考自己，完成认知的最后一步闭环")
    
    time_range = st.selectbox("选择汇总范围", ["今日 (Today)", "近 3 天", "近 7 天", "全部 (All)"])
    
    # Filter docs based on time range
    filter_docs = []
    now = datetime.now()
    if time_range.startswith("今日"):
        filter_docs = today_docs
    elif time_range.startswith("近 3 天"):
        cutoff = (now - timedelta(days=3)).strftime("%Y-%m-%d")
        filter_docs = [d for d in all_docs if d.get("created_at", "") >= cutoff]
    elif time_range.startswith("近 7 天"):
        cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        filter_docs = [d for d in all_docs if d.get("created_at", "") >= cutoff]
    else:
        filter_docs = all_docs[:20] # Limit to 20 to avoid massive prompts

    if not filter_docs:
        st.warning("该时间段内没有认知输入，无法生成汇总。")
    else:
        st.success(f"已选中 {len(filter_docs)} 篇文档，提取底层逻辑与判断。")
        
        # Aggregate claims and relations
        aggregated_claims = []
        aggregated_relations = []
        
        for doc in filter_docs:
            doc_key = doc.get("document_key") or doc.get("hash", "")
            claims = list_extracted_claims_by_document_key(doc_key)
            relations = list_extracted_relations_by_document_key(doc_key)
            aggregated_claims.extend([c.get("statement") for c in claims if c.get("statement")])
            aggregated_relations.extend([
                f"{r.get('subject_name')} -> {r.get('relation_type')} -> {r.get('object_name')}"
                for r in relations
            ])
            
        # De-duplicate
        aggregated_claims = list(set(aggregated_claims))
        aggregated_relations = list(set(aggregated_relations))
        
        prompt_text = "作为我的严厉导师，我需要你检验我的认知深度。请根据以下我最近总结的核心逻辑和判断，给我出 3 道极其尖锐、具有挑战性的【深度思考题】，以及 2 道【情景假设题】。不要出简单的死记硬背题，要考查我对因果关系的推演能力。\n\n"
        
        prompt_text += "【我的核心判断】\n"
        if aggregated_claims:
            for c in aggregated_claims:
                prompt_text += f"- {c}\n"
        else:
            prompt_text += "- （暂无结构化判断）\n"
            
        prompt_text += "\n【我的认知图谱与关系推演】\n"
        if aggregated_relations:
            for r in aggregated_relations:
                prompt_text += f"- {r}\n"
        else:
            prompt_text += "- （暂无结构化关系）\n"
            
        prompt_text += "\n请直接开始出题，并要求我回答。在我回答之后，你再给出你的点评和标准逻辑框架。"
        
        st.markdown("👇 **一键复制下方的 Prompt，发送给 Cursor、Trae、ChatGPT 或 Claude 进行自我测验：**")
        st.code(prompt_text, language="markdown")

with tab4:
    section_title("学习笔记汇总", "你在文档工作台中记录的所有思考与验证想法")
    if not notes_docs:
        st.info("暂无笔记。去【文档工作台】阅读文章并写下你的思考吧！")
    else:
        for doc in notes_docs:
            metadata = doc.get("metadata_json") or {}
            note = metadata.get("user_note", "")
            with st.expander(f"📝 笔记：{doc.get('title')}", expanded=True):
                st.caption(f"文档来源: {doc.get('source_name')} | 记录时间: {doc.get('updated_at', '')[:10]}")
                st.markdown(f"**我的思考：**\n\n{note}")
                
                # Provide a direct edit interface here as well
                with st.form(f"quick_edit_note_{doc.get('id')}"):
                    new_note = st.text_area("快速修改", value=note, height=100, label_visibility="collapsed")
                    col_save, col_del, _ = st.columns([1, 1, 5])
                    with col_save:
                        if st.form_submit_button("保存修改"):
                            from kb.storage import update_document_metadata
                            metadata["user_note"] = new_note
                            update_document_metadata(doc["id"], metadata)
                            st.success("修改已保存！")
                            st.rerun()
                    with col_del:
                        if st.form_submit_button("删除笔记"):
                            from kb.storage import update_document_metadata
                            del metadata["user_note"]
                            update_document_metadata(doc["id"], metadata)
                            st.success("笔记已删除！")
                            st.rerun()
