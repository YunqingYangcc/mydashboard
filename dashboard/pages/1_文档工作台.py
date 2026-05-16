import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, metric_card, render_document_preview, section_title, show_table
from kb.storage import (
    fetch_latest_documents,
    get_document_by_key,
    init_db,
    list_extracted_claims_by_document_key,
    list_extracted_relations_by_document_key,
    list_extracted_tasks_by_document_key,
    search_documents,
)


init_db()
init_page_style()

st.title("文档工作台")
st.caption("以文档为中心查看预览、自动抽取结果与后续动作")

# 侧边栏：文档选择与过滤区
with st.sidebar:
    st.header("文档导航")
    search_text = st.text_input("搜索文档", placeholder="如：NVDA、HBM、CapEx")
    documents = search_documents(search_text, limit=50) if search_text else fetch_latest_documents(limit=50)
    markdown_only = st.toggle("仅看 Markdown", value=True)
    
    if markdown_only:
        documents = [doc for doc in documents if (doc.get("metadata_json") or {}).get("render_mode") == "markdown"]
        
    doc_options = {
        f"{doc.get('title')} | {doc.get('source_name')}": doc.get("document_key") or doc.get("hash")
        for doc in documents
    }
    
    if not doc_options:
        st.info("当前没有可用文档")
        selected_doc = None
    else:
        selected_key = st.selectbox("选择文档", list(doc_options.keys()))
        selected_doc = get_document_by_key(doc_options[selected_key]) or documents[0]

# 主内容区：全宽展示
if not selected_doc:
    st.info("请在左侧侧边栏搜索并选择一篇文档。")
else:
    section_title("文档正文预览", "Markdown 会直接渲染，包含 Mermaid 动态图表")
    render_document_preview(selected_doc)
    
    st.divider()

    section_title("学习笔记", "在这里记录你对这篇文章的思考与补充")
    doc_metadata = selected_doc.get("metadata_json") or {}
    current_note = doc_metadata.get("user_note", "")
    
    with st.form("doc_note_form"):
        new_note = st.text_area("笔记内容", value=current_note, height=150, placeholder="写下你的理解、疑问或待验证的想法...")
        col_save, col_del, _ = st.columns([1, 1, 5])
        with col_save:
            submitted = st.form_submit_button("保存/修改笔记")
        with col_del:
            deleted = st.form_submit_button("删除笔记")
            
        if submitted:
            from kb.storage import update_document_metadata
            doc_metadata["user_note"] = new_note
            update_document_metadata(selected_doc["id"], doc_metadata)
            st.success("笔记已保存！")
            st.rerun()
            
        if deleted:
            from kb.storage import update_document_metadata
            if "user_note" in doc_metadata:
                del doc_metadata["user_note"]
            update_document_metadata(selected_doc["id"], doc_metadata)
            st.success("笔记已删除！")
            st.rerun()

    st.divider()

    document_key = selected_doc.get("document_key") or selected_doc.get("hash", "")
    claims = list_extracted_claims_by_document_key(document_key)
    relations = list_extracted_relations_by_document_key(document_key)
    tasks = list_extracted_tasks_by_document_key(document_key)

    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("抽取断言", len(claims), "来自这篇文档的判断")
    with col2:
        metric_card("抽取关系", len(relations), "来自这篇文档的图谱边")
    with col3:
        metric_card("抽取任务", len(tasks), "来自这篇文档的后续动作")

    tab1, tab2, tab3 = st.tabs(["Claims", "Relations", "Tasks"])

    with tab1:
        show_table(
            [
                {
                    "subject": item.get("subject"),
                    "statement": item.get("statement"),
                    "cycle": item.get("review_cycle"),
                    "状态": item.get("validation_status", "pending"),
                }
                for item in claims
            ],
            height=280,
        )

    with tab2:
        show_table(
            [
                {
                    "subject": item.get("subject_name"),
                    "relation": item.get("relation_type"),
                    "object": item.get("object_name"),
                    "note": item.get("note"),
                }
                for item in relations
            ],
            height=280,
        )

    with tab3:
        show_table(
            [
                {
                    "title": item.get("title"),
                    "priority": item.get("priority"),
                    "status": item.get("status"),
                    "source": item.get("source"),
                }
                for item in tasks
            ],
            height=280,
        )
