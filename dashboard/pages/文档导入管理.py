"""文档导入管理 - 将外部内容导入知识库"""
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import init_db, upsert_document
from kb.utils import now_iso
import hashlib

init_db()
init_page_style()

st.title("📥 文档导入")
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

# 手动录入文档
st.markdown("### 📄 手动录入文档")

with st.form("import_form", clear_on_submit=True):
    title = st.text_input("标题 *", placeholder="输入文档标题")
    
    content = st.text_area("内容 *", height=300, placeholder="输入文档内容...")
    
    col1, col2 = st.columns([2, 2])
    with col1:
        chapter = st.selectbox("所属章节", CHAPTER_OPTIONS)
    with col2:
        source = st.text_input("来源", placeholder="如: 公众号、书籍、网页等")
    
    tags = st.text_input("标签（逗号分隔）", placeholder="如: AI, 投资, 认知")
    
    st.caption("* 为必填项")
    
    submitted = st.form_submit_button("💾 保存文档", type="primary", use_container_width=True)
    
    if submitted:
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
            st.balloons()
        else:
            if not title:
                st.error("⚠️ 请填写标题")
            if not content:
                st.error("⚠️ 请填写内容")

st.divider()

# 导入提示
st.markdown("### 💡 导入提示")
st.info(
    """
    **支持的导入方式：**
    - 📄 手动录入：直接在此页面填写标题、内容和元数据
    - 📁 文件夹导入：将 .md 或 .txt 文件放入 `data/inbox/` 目录，系统会自动导入
    
    **章节分类建议：**
    - P0 开头：基础设施层（AI芯片、存储、服务器、互联、云计算）
    - P0 数据/软件：数据层和软件层
    - P1 开头：能源电力层、半导体制造层
    """
)

# 侧边栏
with st.sidebar:
    st.markdown("### 📥 导入指南")
    st.markdown(
        """
        **文档质量建议：**
        - 标题简洁明确
        - 内容结构清晰（使用 Markdown 格式）
        - 添加合适的标签便于检索
        - 选择正确的章节进行分类
        
        **自动导入：**
        将文件放入 `data/inbox/` 目录，
        系统会在下次启动时自动导入。
        """
    )
    st.divider()
    render_signature()
