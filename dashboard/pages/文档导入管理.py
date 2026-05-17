"""文档导入管理 - 上传、RSS订阅、文件夹导入"""
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style
from kb.storage import init_db, fetch_latest_documents, upsert_document
from kb.ingest import ingest_folder
from kb.utils import now_iso
import hashlib

init_db()
init_page_style()

st.title("📥 文档导入管理")
st.caption("将外部内容导入知识库")

tab1, tab2 = st.tabs(["📁 文件夹导入", "📄 手动录入"])

# Tab 1: 文件夹导入
with tab1:
    st.subheader("从文件夹导入")
    st.info(f"📂 监听目录: `data/inbox/`")
    
    # 显示已有文件
    inbox_dir = ROOT_DIR / "data" / "inbox"
    if inbox_dir.exists():
        files = list(inbox_dir.glob("*.md")) + list(inbox_dir.glob("*.txt"))
        if files:
            st.write(f"发现 {len(files)} 个文件:")
            for f in files:
                st.text(f"- {f.name}")
        else:
            st.info("inbox 文件夹暂无 .md 或 .txt 文件")
    
    if st.button("🔄 执行导入", type="primary"):
        with st.spinner("正在导入..."):
            try:
                result = ingest_folder(inbox_dir)
                st.success(f"✅ 导入完成！处理了 {len(result.get('processed', []))} 个文件")
            except Exception as e:
                st.error(f"导入失败: {e}")

# Tab 2: 手动录入
with tab2:
    st.subheader("手动录入文档")
    
    title = st.text_input("标题")
    content = st.text_area("内容", height=200)
    
    source = st.text_input("来源", placeholder="如: 手动录入、公众号、书籍等")
    tags = st.text_input("标签（逗号分隔）", placeholder="如: AI, 投资, 认知")
    
    if st.button("💾 保存文档", type="primary"):
        if title and content:
            doc_key = hashlib.sha256(f"{title}{now_iso()}".encode()).hexdigest()[:16]
            upsert_document({
                "title": title,
                "content": content,
                "source": source or "手动录入",
                "tags_json": tags,
                "render_mode": "markdown",
                "document_key": doc_key
            })
            st.success("✅ 文档已保存！")
        else:
            st.warning("⚠️ 请填写标题和内容")
