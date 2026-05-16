import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, metric_card, render_document_preview, render_signature, section_title, show_table
from kb.storage import (
    fetch_latest_documents,
    get_document_by_key,
    init_db,
    list_extracted_claims_by_document_key,
    list_extracted_relations_by_document_key,
    list_extracted_tasks_by_document_key,
    search_documents,
    update_document_metadata,
)

init_db()
init_page_style()

st.title("📝 知识库")
st.caption("管理你的学习文档，支持层级筛选和收藏")

# ===== 层级筛选选项 =====
LAYER_OPTIONS = [
    "全部",
    "🪨 原材料层",
    "🔧 设备层", 
    "🏭 制造层",
    "💻 芯片层",
    "🖥️ 系统层",
    "📡 云层",
    "📊 数据层",
    "🔧 软件层",
    "🤖 模型层",
    "🚗 应用层",
    "⚡ 能源层",
]

# ===== 侧边栏：文档选择 =====
with st.sidebar:
    st.header("文档导航")
    
    # 收藏筛选
    if "show_starred_only" not in st.session_state:
        st.session_state.show_starred_only = False
    
    show_starred = st.toggle("⭐ 仅看收藏", value=st.session_state.show_starred_only)
    st.session_state.show_starred_only = show_starred
    
    # 层级筛选
    selected_layer = st.selectbox("📂 筛选层级", LAYER_OPTIONS)
    
    # 搜索
    search_text = st.text_input("🔍 搜索", placeholder="如：NVDA、HBM", label_visibility="collapsed")
    
    docs = search_documents(search_text, limit=100) if search_text else fetch_latest_documents(limit=100)
    markdown_docs = [d for d in docs if (d.get("metadata_json") or {}).get("render_mode") == "markdown"]
    
    # 默认只看 Markdown
    if "show_all_docs" not in st.session_state:
        st.session_state.show_all_docs = False
    
    show_all = st.toggle("显示全部文档", value=st.session_state.show_all_docs)
    st.session_state.show_all_docs = show_all
    
    display_docs = docs if show_all else markdown_docs
    
    # 应用收藏筛选
    if show_starred:
        display_docs = [d for d in display_docs if (d.get("metadata_json") or {}).get("starred", False)]
    
    # 应用层级筛选
    if selected_layer != "全部":
        display_docs = [d for d in display_docs if (d.get("metadata_json") or {}).get("layer") == selected_layer]
    
    # 统计
    starred_count = len([d for d in docs if (d.get("metadata_json") or {}).get("starred", False)])
    st.caption(f"⭐ 收藏 {starred_count} | 📄 共 {len(display_docs)} 篇")
    
    if not display_docs:
        st.info("没有匹配的文档")
        selected_doc = None
    else:
        options = {f"{d.get('title')}": d for d in display_docs}
        selected_title = st.selectbox("选择文档", list(options.keys()))
        selected_doc = options[selected_title]
    
    st.divider()
    render_signature()

# ===== 主内容 =====
if not selected_doc:
    st.info("👈 请在左侧选择一篇文档")
else:
    # 文档预览
    section_title("文档预览")
    
    # 收藏按钮和层级标签
    doc_id = selected_doc["id"]
    meta = selected_doc.get("metadata_json") or {}
    is_starred = meta.get("starred", False)
    current_layer = meta.get("layer", "未分类")
    
    col1, col2, col3 = st.columns([1, 3, 20])
    with col1:
        if st.button("⭐" if not is_starred else "⭐", type="primary" if is_starred else "secondary", help="收藏此文档"):
            meta["starred"] = not is_starred
            update_document_metadata(doc_id, meta)
            st.rerun()
    with col2:
        new_layer = st.selectbox(
            "📂 层级",
            LAYER_OPTIONS,
            index=LAYER_OPTIONS.index(current_layer) if current_layer in LAYER_OPTIONS else 0,
            label_visibility="collapsed"
        )
        if new_layer != current_layer:
            meta["layer"] = new_layer
            update_document_metadata(doc_id, meta)
            st.rerun()
    with col3:
        if is_starred:
            st.caption(f"⭐ 已收藏 · {current_layer}")
    
    render_document_preview(selected_doc)
    
    st.divider()
    
    # 学习笔记
    note = meta.get("user_note", "")
    
    section_title("学习笔记", "记录你的思考与验证想法")
    
    new_note = st.text_area(
        "笔记",
        value=note,
        height=120,
        placeholder="写下你的理解、疑问或待验证的想法...",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 保存笔记", use_container_width=True):
            meta["user_note"] = new_note
            update_document_metadata(doc_id, meta)
            st.success("笔记已保存")
            st.rerun()
        if note and st.button("🗑️ 删除笔记", use_container_width=True):
            if "user_note" in meta:
                del meta["user_note"]
            update_document_metadata(doc_id, meta)
            st.success("笔记已删除")
            st.rerun()
    
    st.divider()
    
    # 抽取统计
    doc_key = selected_doc.get("document_key") or selected_doc.get("hash", "")
    claims = list_extracted_claims_by_document_key(doc_key)
    relations = list_extracted_relations_by_document_key(doc_key)
    tasks = list_extracted_tasks_by_document_key(doc_key)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("断言", len(claims), "判断")
    with col2:
        metric_card("关系", len(relations), "图谱边")
    with col3:
        metric_card("任务", len(tasks), "后续动作")
    
    # 详情 Tab
    tab1, tab2, tab3 = st.tabs(["断言 Claims", "关系 Relations", "任务 Tasks"])
    
    with tab1:
        if claims:
            show_table(
                [{"主体": c.get("subject"), "判断": c.get("statement"), "周期": c.get("review_cycle")} 
                 for c in claims],
                height=280,
            )
        else:
            st.info("暂无断言")
    
    with tab2:
        if relations:
            show_table(
                [{"主体": r.get("subject_name"), "关系": r.get("relation_type"), "客体": r.get("object_name")} 
                 for r in relations],
                height=280,
            )
        else:
            st.info("暂无关系")
    
    with tab3:
        if tasks:
            show_table(
                [{"标题": t.get("title"), "优先级": t.get("priority"), "状态": t.get("status")} 
                 for t in tasks],
                height=280,
            )
        else:
            st.info("暂无任务")
