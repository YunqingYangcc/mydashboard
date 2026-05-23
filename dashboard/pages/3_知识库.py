"""知识库 - PC阅读器：左侧列表单击即读"""
import sys
from pathlib import Path
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature, render_notes_list
from kb.storage import fetch_latest_documents, init_db, list_claims, search_documents, update_document_metadata

init_db()
init_page_style()

CHAPTERS = ["全部","未分类",
    "P0-基础设施/AI芯片","P0-基础设施/存储与内存/HBM",
    "P0-基础设施/高速互联/800G光模块","P0-基础设施/云计算/CapEx",
    "P1-能源/电力需求","P1-制造/晶圆代工"]

# ===== 左侧固定栏 =====
with st.sidebar:
    st.markdown("### 📝 知识库")
    q = st.text_input("搜索", placeholder="关键词...", label_visibility="collapsed")
    ch = st.selectbox("章节", CHAPTERS, index=0, label_visibility="collapsed")
    
    docs = search_documents(q, limit=200) if q else fetch_latest_documents(limit=500)
    if ch=="未分类": docs=[d for d in docs if not (d.get("metadata_json")or{}).get("layer")]
    elif ch!="全部": docs=[d for d in docs if (d.get("metadata_json")or{}).get("layer")==ch]
    docs.sort(key=lambda d: d.get("created_at",""), reverse=True)
    
    st.divider()
    st.caption(f"{len(docs)} 篇")
    
    for d in docs:
        m = d.get("metadata_json") or {}
        title = d.get("title","?")
        lay = (m.get("layer") or "未分类").split("/")[-1]
        dt = (d.get("created_at","")or"")[:10]
        active = st.session_state.get("sel_id") == d["id"]
        
        bg = "rgba(99,102,241,.08)" if active else "transparent"
        bc = "rgba(99,102,241,.22)" if active else "rgba(99,102,241,.06)"
        fw = "600" if active else "400"
        
        st.markdown(
            f'<div style="border:1px solid {bc}; border-radius:8px; padding:8px 10px; margin-bottom:4px; background:{bg};">'
            f'<div style="font-size:0.82rem; color:#e0e7ff; font-weight:{fw}; line-height:1.35; margin-bottom:4px;">'
            f'{"📌" if m.get("starred") else ""} {title}</div>'
            f'<div style="display:flex; justify-content:space-between;">'
            f'<span style="font-size:0.62rem; color:#7178a0; background:rgba(99,102,241,.06); padding:1px 5px; border-radius:3px;">{lay}</span>'
            f'<span style="font-size:0.62rem; color:#555;">{dt[5:]}</span>'
            f'</div></div>', unsafe_allow_html=True)
        
        if st.button("读", key=f"s_{d['id']}", type="primary" if active else "secondary"):
            st.session_state["sel_id"] = d["id"]
            st.session_state["sel_doc"] = d
            st.rerun()
    
    render_signature()

# ===== 右侧阅读区 =====
sel = st.session_state.get("sel_doc")
if not sel:
    st.title("📝 知识库")
    st.info("← 从左侧选文章")
else:
    m = sel.get("metadata_json") or {}
    layer = m.get("layer") or "未分类"
    title = sel.get("title","?")
    is_starred = m.get("starred", False)
    
    st.title(title)
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: st.caption(f"{(sel.get('created_at','')or'')[:10]} · {layer}")
    with c2:
        nl = st.selectbox("章节", ["未分类"]+CHAPTERS[2:],
            index=0 if layer=="未分类" else (CHAPTERS[2:].index(layer)+1 if layer in CHAPTERS[2:] else 0),
            label_visibility="collapsed", key="nl")
        if nl!=layer:
            m["layer"] = None if nl=="未分类" else nl
            update_document_metadata(sel["id"], m); st.rerun()
    with c3:
        if st.button("📌 取消" if is_starred else "📌 标记", use_container_width=True):
            m["starred"] = not is_starred; update_document_metadata(sel["id"], m); st.rerun()
    
    st.divider()
    from dashboard.components import render_document_preview
    render_document_preview(sel)
    
    # 笔记区
    if m.get("user_note") or st.checkbox("📝 写笔记", key="show_note"):
        nt = st.text_area("", value=m.get("user_note",""), placeholder="读完的想法...", label_visibility="collapsed")
        c1, c2, c3 = st.columns([1,1,3])
        if c1.button("保存", use_container_width=True):
            m["user_note"]=nt; update_document_metadata(sel["id"], m); st.rerun()
        if c2.button("清空", use_container_width=True):
            m.pop("user_note",None); update_document_metadata(sel["id"], m); st.rerun()
    
    # 关联知识点
    if layer and layer!="未分类":
        cl = list_claims(chapter=layer)
        if cl:
            st.divider()
            with st.expander(f"🧠 {layer} · {len(cl)}条知识点", expanded=False):
                render_notes_list(cl)
