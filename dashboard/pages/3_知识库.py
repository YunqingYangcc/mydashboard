"""知识库 - PC阅读器：左侧列表单击即读"""
import sys
from pathlib import Path
import streamlit as st
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature, render_notes_list
from kb.storage import fetch_latest_documents, init_db, list_claims, search_documents, update_document_metadata

init_db()
init_page_style()

NOTES_DIR = ROOT_DIR / "data" / "inbox"

def parse_date_folder(name):
    """解析日期目录名，返回排序用的日期对象"""
    try:
        if len(name) == 10 and name[4] == '-' and name[7] == '-':
            return datetime.strptime(name, "%Y-%m-%d")
        else:
            parts = name.split('-')
            if len(parts) == 3:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
    except:
        pass
    return datetime.min

def get_daily_notes():
    """获取按日期分类的笔记"""
    notes_by_date = {}
    if NOTES_DIR.exists():
        date_dirs = [d for d in NOTES_DIR.iterdir() if d.is_dir()]
        date_dirs.sort(key=lambda d: parse_date_folder(d.name), reverse=True)
        
        for date_dir in date_dirs:
            date_str = date_dir.name
            notes = []
            for f in sorted(date_dir.glob("*.md")):
                notes.append({
                    "name": f.stem,
                    "path": str(f),
                    "date": date_str
                })
            if notes:
                notes_by_date[date_str] = notes
    return notes_by_date

def read_note_content(file_path):
    """读取笔记内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取失败: {e}"

CHAPTERS = ["全部","未分类",
    "P0-基础设施/AI芯片","P0-基础设施/存储与内存/HBM",
    "P0-基础设施/高速互联/800G光模块","P0-基础设施/云计算/CapEx",
    "P1-能源/电力需求","P1-制造/晶圆代工"]

tab1, tab2 = st.tabs(["📚 文档库", "📅 每日笔记"])

with tab1:
    with st.sidebar:
        st.markdown("### 📝 知识库")
        q = st.text_input("搜索", placeholder="关键词...", label_visibility="collapsed")
        
        st.caption("📅 日期筛选")
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("开始", value=None, key="start_date", label_visibility="collapsed")
        with date_col2:
            end_date = st.date_input("结束", value=None, key="end_date", label_visibility="collapsed")
        
        ch = st.selectbox("章节", CHAPTERS, index=0, label_visibility="collapsed")
        
        docs = search_documents(q, limit=200) if q else fetch_latest_documents(limit=500)
        if ch=="未分类": docs=[d for d in docs if not (d.get("metadata_json")or{}).get("layer")]
        elif ch!="全部": docs=[d for d in docs if (d.get("metadata_json")or{}).get("layer")==ch]
        
        if start_date:
            docs = [d for d in docs if (d.get("created_at","")or"")[:10] >= str(start_date)]
        if end_date:
            docs = [d for d in docs if (d.get("created_at","")or"")[:10] <= str(end_date)]
        
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
        
        if m.get("user_note") or st.checkbox("📝 写笔记", key="show_note"):
            nt = st.text_area("", value=m.get("user_note",""), placeholder="读完的想法...", label_visibility="collapsed")
            c1, c2, c3 = st.columns([1,1,3])
            if c1.button("保存", use_container_width=True):
                m["user_note"]=nt; update_document_metadata(sel["id"], m); st.rerun()
            if c2.button("清空", use_container_width=True):
                m.pop("user_note",None); update_document_metadata(sel["id"], m); st.rerun()
        
        if layer and layer!="未分类":
            cl = list_claims(chapter=layer)
            if cl:
                st.divider()
                with st.expander(f"🧠 {layer} · {len(cl)}条知识点", expanded=False):
                    render_notes_list(cl)

with tab2:
    st.title("📅 每日学习笔记")
    st.caption(f"笔记目录: data/inbox/")
    
    notes_by_date = get_daily_notes()
    
    if not notes_by_date:
        st.info("暂无笔记。请将学习笔记保存到 data/inbox/YYYY-MM-DD/ 目录")
        today = datetime.now().strftime("%Y-%m-%d")
        st.code(f"mkdir -p data/inbox/{today}\n# 然后在该目录下创建 .md 文件", language="bash")
    else:
        total_notes = sum(len(n) for n in notes_by_date.values())
        st.caption(f"共 {len(notes_by_date)} 天，{total_notes} 篇笔记")
        
        st.divider()
        
        for date_str, notes in notes_by_date.items():
            with st.expander(f"📆 {date_str} ({len(notes)}篇)", expanded=(date_str == list(notes_by_date.keys())[0])):
                cols = st.columns(min(len(notes), 4))
                for idx, note in enumerate(notes):
                    with cols[idx % len(cols)]:
                        if st.button(f"📄 {note['name']}", key=f"note_{note['path']}", use_container_width=True):
                            st.session_state["reading_note"] = note["path"]
        
        reading_path = st.session_state.get("reading_note")
        if reading_path:
            st.divider()
            note_name = Path(reading_path).stem
            note_date = Path(reading_path).parent.name
            st.subheader(f"📄 {note_name}")
            st.caption(f"📅 {note_date}")
            
            content = read_note_content(reading_path)
            st.markdown(content)
