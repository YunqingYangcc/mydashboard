import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, metric_card, render_signature
from kb.storage import (
    fetch_latest_documents,
    init_db,
    list_claims,
    list_tasks,
)

init_db()
init_page_style()

st.title("🚀 认知炼金术士")

# 励志标语
SLOGANS = [
    "📈 认知差是最大的投资壁垒",
    "🧠 每天进步1%，一年强大37倍",
    "⛏️ 挖矿不如掌握采矿技术",
    "🎯 知道什么不重要，理解为什么才值钱",
    "📚 知识不复习等于快时尚，穿几次就扔",
    "🔥 成为AI时代的知识资本家",
    "💎 认知深度决定财富高度",
]

import random
slogan = random.choice(SLOGANS)
st.caption(f"> *{slogan}*")

# 知识库统计
docs = fetch_latest_documents(limit=100)
tasks = list_tasks(limit=100)
claims = list_claims()
markdown_docs = [d for d in docs if (d.get("metadata_json") or {}).get("render_mode") == "markdown"]
starred_docs = [d for d in docs if (d.get("metadata_json") or {}).get("starred", False)]

st.subheader("📊 知识库统计")
stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
with stat_col1:
    metric_card("文档", len(docs), "总数量")
with stat_col2:
    metric_card("Markdown", len(markdown_docs), "可渲染")
with stat_col3:
    metric_card("收藏", len(starred_docs), "⭐")
with stat_col4:
    metric_card("个人提炼", len(claims), "核心判断")

st.divider()

# 快速入口
st.subheader("快速入口")
entry_col1, entry_col2, entry_col3, entry_col4 = st.columns(4)
with entry_col1:
    st.page_link("pages/布局.py", label="📊 布局", icon="📊")
with entry_col2:
    st.page_link("pages/知识库.py", label="📝 知识库", icon="📝")
with entry_col3:
    st.page_link("pages/学习笔记.py", label="🧠 学习笔记", icon="🧠")
with entry_col4:
    st.page_link("pages/试题.py", label="📝 试题练习", icon="📝")

entry_col5, entry_col6 = st.columns(2)
with entry_col5:
    st.page_link("pages/复盘编辑器.py", label="🔄 复盘", icon="🔄")
with entry_col6:
    st.page_link("pages/文档导入管理.py", label="📥 文档导入", icon="📥")

# 签名
with st.sidebar:
    render_signature()
