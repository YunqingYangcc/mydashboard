import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, metric_card, render_document_preview, render_notes_list, render_signature, section_title, show_table
from kb.storage import (
    fetch_latest_documents,
    get_document_by_key,
    fetch_quizzes_by_document_key,
    init_db,
    list_claims,
    search_documents,
    update_document_metadata,
)

init_db()
init_page_style()

st.title("📝 知识库")
st.caption("管理你的学习文档，支持章节筛选和收藏")

# ===== 章节筛选选项 =====
CHAPTER_OPTIONS = [
    "全部文章",
    "未分类",
    # P0 基础设施层
    "P0-基础设施/AI芯片",
    "P0-基础设施/AI芯片/GPU训练",
    "P0-基础设施/AI芯片/GPU推理",
    "P0-基础设施/AI芯片/ASIC定制",
    "P0-基础设施/AI芯片/NPU端侧",
    "P0-基础设施/存储与内存/HBM",
    "P0-基础设施/存储与内存/DRAM",
    "P0-基础设施/AI服务器/整机",
    "P0-基础设施/AI服务器/液冷",
    "P0-基础设施/高速互联/800G光模块",
    "P0-基础设施/高速互联/1.6T光模块",
    "P0-基础设施/云计算/CapEx",
    # P0 数据层
    "P0-数据/训练数据",
    "P0-数据/标注与RLHF",
    # P0 软件层
    "P0-软件/CUDA生态",
    "P0-软件/AI框架",
    "P0-软件/Agent框架",
    # P1 能源电力层
    "P1-能源/电力需求",
    "P1-能源/电力供给",
    # P1 半导体制造
    "P1-制造/晶圆代工",
    "P1-制造/封装测试",
]

# ===== 侧边栏：文档选择 =====
with st.sidebar:
    st.header("文档导航")
    
    # 收藏筛选
    if "show_starred_only" not in st.session_state:
        st.session_state.show_starred_only = False
    
    show_starred = st.toggle("📌 仅看已归类", value=st.session_state.show_starred_only)
    st.session_state.show_starred_only = show_starred
    
    # 章节筛选
    selected_chapter = st.selectbox("📂 筛选章节", CHAPTER_OPTIONS)
    
    # 搜索
    search_text = st.text_input("🔍 搜索", placeholder="如：NVDA、HBM", label_visibility="collapsed")
    
    docs = search_documents(search_text, limit=100) if search_text else fetch_latest_documents(limit=100)
    display_docs = docs
    
    # 应用归类筛选
    if show_starred:
        display_docs = [d for d in display_docs if (d.get("metadata_json") or {}).get("starred", False)]
    
    # 应用章节筛选（章节存在 metadata_json["layer"] 中）
    if selected_chapter == "未分类":
        display_docs = [d for d in display_docs if not (d.get("metadata_json") or {}).get("layer")]
    elif selected_chapter != "全部文章":
        display_docs = [d for d in display_docs if (d.get("metadata_json") or {}).get("layer") == selected_chapter]
    
    # 统计
    starred_count = len([d for d in docs if (d.get("metadata_json") or {}).get("starred", False)])
    st.caption(f"📌 已归类 {starred_count} | 📄 共 {len(display_docs)} 篇")
    
    # 选择文档列表
    
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
    # 文档打标
    section_title("文档打标")
    
    # 收藏按钮和层级标签
    doc_id = selected_doc["id"]
    meta = selected_doc.get("metadata_json") or {}
    is_starred = meta.get("starred", False)
    current_layer = meta.get("layer", "未分类")
    
    col1, col2, col3 = st.columns([1, 3, 20])
    with col1:
        if st.button("📌" if not is_starred else "📌", type="primary" if is_starred else "secondary", help="归类此文档"):
            meta["starred"] = not is_starred
            update_document_metadata(doc_id, meta)
            st.rerun()
    with col2:
        new_layer = st.selectbox(
            "📂 层级",
            CHAPTER_OPTIONS,
            index=CHAPTER_OPTIONS.index(current_layer) if current_layer in CHAPTER_OPTIONS else 0,
            label_visibility="collapsed"
        )
        if new_layer != current_layer:
            meta["layer"] = new_layer
            update_document_metadata(doc_id, meta)
            st.rerun()
    with col3:
        if is_starred:
            st.caption(f"📌 已归类 · {current_layer}")
    
    # 显示文档标题作为标识
    st.caption(f"📄 {selected_doc.get('title', '未命名文档')}")
    
    # 文档预览
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

    # 关联的学习笔记（断言）
    # 从 metadata_json 里取 layer 作为章节
    meta = selected_doc.get("metadata_json") or {}
    doc_chapter = meta.get("layer") or selected_doc.get("chapter")
    
    if doc_chapter and doc_chapter != "未分类":
        chapter_claims = list_claims(chapter=doc_chapter)
        st.subheader(f"🧠 关联的学习笔记（{doc_chapter}）")
        if chapter_claims:
            # 使用改进的卡片式布局（纯展示）
            render_notes_list(chapter_claims)
            
            # 统一的跳转按钮（只有一个）
            if st.button(f"📖 查看 {doc_chapter} 全部笔记", use_container_width=True, type="primary"):
                st.session_state["jump_chapter"] = doc_chapter
                st.switch_page("pages/学习笔记.py")
        else:
            st.info(f"该章节暂无学习笔记，请在「学习笔记」页面为 {doc_chapter} 添加断言。")
    else:
        st.info("📂 请先在上方选择章节（📂 层级），即可自动关联该章节的学习笔记。")

    # 关联的试题
    st.divider()
    doc_key = selected_doc.get("document_key")
    if doc_key:
        quizzes = fetch_quizzes_by_document_key(doc_key)
        if quizzes:
            st.subheader(f"📝 关联试题（{len(quizzes)}题）")
            st.info(f"本文档已录入 {len(quizzes)} 道试题，点击下方按钮开始答题")
            if st.button(f"📝 开始答题", use_container_width=True, type="primary"):
                st.session_state["quiz_document_key"] = doc_key
                st.switch_page("pages/试题.py")
        else:
            st.info("📝 本文档暂无关联试题，可在「试题管理」页面录入。")
