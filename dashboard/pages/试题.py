"""试题页面 - 显示和回答与文档关联的试题"""
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import fetch_quizzes_by_document_key, get_document_by_key, init_db

init_db()
init_page_style()

st.title("📝 试题练习")
st.caption("回答与文档关联的试题，检验知识掌握程度")

# 获取文档key
doc_key = st.session_state.get("quiz_document_key")
if not doc_key:
    st.warning("⚠️ 未指定文档，请从知识库页面进入")
    if st.button("← 返回知识库"):
        st.switch_page("pages/知识库.py")
    st.stop()

# 获取文档信息和试题
doc = get_document_by_key(doc_key)
quizzes = fetch_quizzes_by_document_key(doc_key)

if not quizzes:
    st.info("本文档暂无关联试题")
    if st.button("← 返回知识库"):
        st.switch_page("pages/知识库.py")
    st.stop()

# 显示文档标题
if doc:
    st.markdown(f"**文档**: {doc.get('title', '未命名')}")

st.divider()

# 初始化答题状态
if "current_question_idx" not in st.session_state:
    st.session_state["current_question_idx"] = 0
if "answers" not in st.session_state:
    st.session_state["answers"] = {}
if "show_explanation" not in st.session_state:
    st.session_state["show_explanation"] = {}

# 答题界面
total_questions = len(quizzes)
current_idx = st.session_state["current_question_idx"]

# 进度显示
progress = current_idx / total_questions
st.progress(progress)
st.caption(f"进度: {current_idx + 1} / {total_questions}")

# 当前试题
quiz = quizzes[current_idx]
question_type = quiz.get("question_type", "")
question_text = quiz.get("question_text", "")
options = quiz.get("options_json") or []
correct_answer = quiz.get("correct_answer", "")
explanation = quiz.get("explanation", "")

# 显示试题
st.markdown(f"### {question_type}")
st.markdown(question_text)

# 根据题型显示不同的答题界面
question_key = f"q_{quiz['id']}"

if options and len(options) > 0:
    # 选择题
    user_answer = st.radio("请选择：", options, key=question_key)
else:
    # 问答题
    user_answer = st.text_area("请输入你的答案：", key=question_key, height=150)

# 提交答案
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("✅ 提交答案", use_container_width=True):
        st.session_state["answers"][quiz['id']] = user_answer
        st.session_state["show_explanation"][quiz['id']] = True
        st.rerun()

with col2:
    if st.button("⏭️ 跳过此题", use_container_width=True):
        st.session_state["current_question_idx"] = (current_idx + 1) % total_questions
        st.rerun()

# 显示答案和解析
if st.session_state["show_explanation"].get(quiz['id']):
    st.divider()
    st.markdown("### 📖 参考答案")
    st.info(correct_answer)
    
    if explanation:
        st.markdown("### 💡 解析")
        st.markdown(explanation)
    
    # 导航按钮
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
    with nav_col1:
        if current_idx > 0:
            if st.button("← 上一题"):
                st.session_state["current_question_idx"] = current_idx - 1
                st.rerun()
    with nav_col2:
        if st.button("📊 查看成绩"):
            st.session_state["show_results"] = True
            st.rerun()
    with nav_col3:
        if current_idx < total_questions - 1:
            if st.button("下一题 →"):
                st.session_state["current_question_idx"] = current_idx + 1
                st.rerun()

# 显示结果
if st.session_state.get("show_results"):
    st.divider()
    st.markdown("### 📊 答题结果")
    
    answered_count = len(st.session_state["answers"])
    st.metric("已答题数", f"{answered_count} / {total_questions}")
    
    if st.button("🔄 重新答题"):
        st.session_state["current_question_idx"] = 0
        st.session_state["answers"] = {}
        st.session_state["show_explanation"] = {}
        st.session_state["show_results"] = False
        st.rerun()

# 底部导航
st.divider()
if st.button("← 返回知识库"):
    # 清除答题状态
    for key in ["current_question_idx", "answers", "show_explanation", "show_results"]:
        if key in st.session_state:
            del st.session_state[key]
    st.switch_page("pages/知识库.py")

# 侧边栏
with st.sidebar:
    render_signature()
