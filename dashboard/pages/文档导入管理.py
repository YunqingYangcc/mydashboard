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

# ===== 章节选项 =====
CHAPTER_OPTIONS = [
    "未分类",
    # P0 基础设施层
    "P0-基础设施/AI芯片",
    "P0-基础设施/AI芯片/GPU训练",
    "P0-基础设施/AI芯片/GPU推理",
    "P0-基础设施/AI芯片/ASIC定制",
    "P0-基础设施/AI芯片/NPU端侧",
    "P0-基础设施/AI芯片/FPGA",
    "P0-基础设施/AI芯片/车载AI",
    "P0-基础设施/存储与内存/HBM",
    "P0-基础设施/存储与内存/DRAM",
    "P0-基础设施/存储与内存/NAND",
    "P0-基础设施/存储与内存/CXL",
    "P0-基础设施/AI服务器/整机",
    "P0-基础设施/AI服务器/液冷",
    "P0-基础设施/AI服务器/电源",
    "P0-基础设施/高速互联/800G光模块",
    "P0-基础设施/高速互联/1.6T光模块",
    "P0-基础设施/高速互联/InfiniBand",
    "P0-基础设施/高速互联/NVLink",
    "P0-基础设施/云计算/CapEx",
    "P0-基础设施/云计算/算力租赁",
    "P0-基础设施/云计算/CapEx周期",
    "P0-基础设施/云计算/自研芯片",
    # P0 数据层
    "P0-数据/训练数据",
    "P0-数据/标注与RLHF",
    "P0-数据/数据治理",
    "P0-数据/向量数据库",
    # P0 软件层
    "P0-软件/CUDA生态",
    "P0-软件/AI框架",
    "P0-软件/MLOps",
    "P0-软件/Agent框架",
    # P1 能源电力层
    "P1-能源/电力需求",
    "P1-能源/电力供给",
    "P1-能源/散热",
    # P1 半导体制造
    "P1-制造/晶圆代工",
    "P1-制造/封装测试",
    "P1-制造/设备材料",
]

tab1, tab2 = st.tabs(["📁 文件夹导入", "📄 手动录入"])

# Tab 1: 文件夹导入
with tab1:
    st.subheader("从文件夹导入")
    st.info(f"📂 监听目录: `data/inbox/`")
    
    # 导入时分配的章节
    chapter_for_import = st.selectbox("导入后分配章节", CHAPTER_OPTIONS, key="import_chapter")
    
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
                docs = ingest_folder()
                count = 0
                for doc in docs:
                    doc_key = hashlib.sha256(f"{doc['title']}{now_iso()}".encode()).hexdigest()[:16]
                    upsert_document({
                        "title": doc.get("title", "未命名"),
                        "content": doc.get("content", ""),
                        "source": doc.get("source_name", "folder"),
                        "chapter": chapter_for_import if chapter_for_import != "未分类" else None,
                        "tags_json": ",".join(doc.get("tags", [])),
                        "render_mode": doc.get("metadata", {}).get("render_mode", "markdown"),
                        "document_key": doc_key
                    })
                    count += 1
                st.success(f"✅ 导入完成！处理了 {count} 个文件，已分配章节: {chapter_for_import}")
            except Exception as e:
                st.error(f"导入失败: {e}")

# Tab 2: 手动录入
with tab2:
    st.subheader("手动录入文档")
    
    title = st.text_input("标题")
    content = st.text_area("内容", height=200)
    chapter = st.selectbox("所属章节", CHAPTER_OPTIONS)
    source = st.text_input("来源", placeholder="如: 手动录入、公众号、书籍等")
    tags = st.text_input("标签（逗号分隔）", placeholder="如: AI, 投资, 认知")
    
    if st.button("💾 保存文档", type="primary"):
        if title and content:
            doc_key = hashlib.sha256(f"{title}{now_iso()}".encode()).hexdigest()[:16]
            upsert_document({
                "title": title,
                "content": content,
                "source": source or "手动录入",
                "chapter": chapter if chapter != "未分类" else None,
                "tags_json": tags,
                "render_mode": "markdown",
                "document_key": doc_key
            })
            st.success(f"✅ 文档已保存！章节: {chapter}")
        else:
            st.warning("⚠️ 请填写标题和内容")
