"""知识点 - PC高效：大框即写，表格式速览"""
import sys
from pathlib import Path
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, list_claims, insert_claim, update_claim, delete_claim

init_db()
init_page_style()

st.title("🧠 知识点")

# ===== 置顶大输入框，Ctrl+Enter 即存 =====
with st.form("inp", clear_on_submit=True):
    c1, c2 = st.columns([9, 1.5])
    with c1:
        txt = st.text_area("", placeholder="NVDA 推理卡提前半年... 半导体周期见顶... HBM4 良率突破...",
                           label_visibility="collapsed")
    with c2:
        ch = st.selectbox("分类", ["AI芯片","半导体","能源","认知","应用","制造","投资","未分类"], index=7, label_visibility="collapsed")
        btn = st.form_submit_button("保存", use_container_width=True, type="primary")
    if btn and txt.strip():
        insert_claim({"claim_type":"observation","chapter":None if ch=="未分类" else ch,"statement":txt.strip()})
        st.rerun()

# ===== 过滤行 =====
notes = list_claims(limit=500)
f1, f2, f3 = st.columns([1.5, 1.2, 0.6])
with f1: chf = st.selectbox("分类", ["全部","未分类","AI芯片","半导体","能源","认知","应用","制造","投资"], index=0, label_visibility="collapsed")
with f2: sf = st.selectbox("状态", ["全部","⏳待验证","✅已验证","❌驳回"], index=0, label_visibility="collapsed")
with f3: st.caption(f"{len(notes)}条")

sm = {"⏳待验证":"pending","✅已验证":"validated","❌驳回":"invalidated"}
if chf!="全部": notes=[c for c in notes if (c.get("chapter")or"未分类")==chf]
if sf!="全部": notes=[c for c in notes if c.get("verification_status")==sm[sf]]
notes.sort(key=lambda c: c.get("updated_at",""), reverse=True)

# ===== 紧凑列表 =====
st.divider()
if not notes:
    st.info("还没有笔记")
else:
    # 表头
    cols = st.columns([0.4, 0.55, 2.5, 0.6, 0.4, 0.35])
    cols[0].caption("状态")
    cols[1].caption("分类")
    cols[2].caption("内容")
    cols[3].caption("日期")
    cols[4].caption("编辑")
    cols[5].caption("删除")
    
    for n in notes:
        cid, stt, chn, txt2, upd = n["id"], n.get("verification_status","pending"), n.get("chapter")or"未分类", n.get("statement",""), (n.get("updated_at","")or"")[:10]
        icon = "✅" if stt=="validated" else ("❌" if stt=="invalidated" else "⏳")
        
        r = st.columns([0.4, 0.55, 2.5, 0.6, 0.4, 0.35])
        with r[0]:
            ns = st.radio("", ["⏳","✅","❌"], horizontal=True, key=f"s_{cid}",
                         index=["pending","validated","invalidated"].index(stt), label_visibility="collapsed")
            sm2 = {"⏳":"pending","✅":"validated","❌":"invalidated"}
            if ns and sm2[ns] != stt:
                update_claim(cid, {"verification_status": sm2[ns]})
                st.rerun()
        with r[1]: st.caption(chn[:4])
        with r[2]: st.markdown(f'<span style="color:#e0e7ff;font-size:0.88rem;">{txt2}</span>', unsafe_allow_html=True)
        with r[3]: st.caption(upd[5:] if len(upd)>5 else upd)
        with r[4]:
            with st.popover("✏️"):
                et = st.text_area("修改", value=txt2, key=f"e_{cid}", label_visibility="collapsed")
                if st.button("保存修改", key=f"save_{cid}"):
                    update_claim(cid, {"statement": et.strip()})
                    st.rerun()
        with r[5]:
            if st.button("🗑", key=f"del_{cid}"): delete_claim(cid); st.rerun()

with st.sidebar: render_signature()
