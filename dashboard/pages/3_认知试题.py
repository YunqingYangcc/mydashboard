import sys
import re
from pathlib import Path
from datetime import datetime

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, section_title, render_document_preview
from kb.storage import init_db, upsert_document, fetch_latest_documents
from kb.utils import now_iso

init_db()
init_page_style()

st.title("认知试题")
st.caption("在这里录入你的认知测验题、回答与 AI 反馈。系统会自动解析特定格式，并支持在线作答。")

QUIZ_TEMPLATE = """## 题目：[在这里写下题目标题]
[在这里补充题目详细背景或直接留空]

### 我的回答：


### AI点评：

"""

def parse_quiz_content(content: str) -> list[dict]:
    """
    解析符合格式的 Markdown 试题。
    返回一个字典列表，每个字典包含：
    - raw_block: 原始块文本（用于替换回存）
    - title: 题目标题
    - description: 题目描述
    - answer: 我的回答
    - feedback: AI 点评
    """
    blocks = re.split(r'^(?=## 题目：)', content, flags=re.MULTILINE)
    questions = []
    
    for block in blocks:
        if not block.strip() or not block.startswith("## 题目："):
            continue
            
        # 解析题目部分
        lines = block.split('\n', 1)
        title = lines[0].replace("## 题目：", "").strip()
        rest = lines[1] if len(lines) > 1 else ""
        
        # 分离出 我的回答
        ans_parts = re.split(r'^### 我的回答：', rest, flags=re.MULTILINE)
        q_desc = ans_parts[0].strip()
        
        answer = ""
        feedback = ""
        
        if len(ans_parts) > 1:
            ans_rest = ans_parts[1]
            # 分离出 AI点评
            fb_parts = re.split(r'^### AI点评：', ans_rest, flags=re.MULTILINE)
            answer = fb_parts[0].strip()
            if len(fb_parts) > 1:
                feedback = fb_parts[1].strip()
                
        questions.append({
            "raw_block": block,
            "title": title,
            "description": q_desc,
            "answer": answer,
            "feedback": feedback
        })
    return questions

tab1, tab2 = st.tabs(["📝 录入新试题", "📚 历史试题回顾"])

with tab1:
    section_title("录入试题", "将你在外部生成的测验记录粘贴到这里")
    st.info("💡 **推荐格式**（你可以只贴题目，后续在「历史试题回顾」里直接在线作答）：\n\n" + QUIZ_TEMPLATE.replace("\n", "  \n"))
    
    with st.form("quiz_input_form"):
        title = st.text_input("试卷标题", placeholder="例如：NVDA 2026 财报核心预期测验")
        content = st.text_area(
            "试卷内容 (Markdown)", 
            height=400, 
            value=QUIZ_TEMPLATE
        )
        tags_input = st.text_input("标签 (用逗号分隔)", placeholder="例如：NVDA, 财报, 测验")
        
        submitted = st.form_submit_button("保存试题")
        if submitted:
            if not title.strip() or not content.strip():
                st.error("标题和内容不能为空！")
            else:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                if "quiz" not in tags:
                    tags.append("quiz")
                    
                payload = {
                    "source_type": "quiz",
                    "source_name": "manual_entry",
                    "title": title.strip(),
                    "content": content.strip(),
                    "summary": content.strip()[:200] + "...",
                    "tags": tags,
                    "metadata": {"render_mode": "markdown", "type": "quiz"},
                    "doc_date": now_iso()
                }
                upsert_document(payload)
                st.success("试题保存成功！可以在「历史试题回顾」中查看。")
                st.rerun()

with tab2:
    section_title("试题列表", "你过去录入的所有认知试题")
    
    # 提取所有的试题
    all_docs = fetch_latest_documents(limit=200)
    quiz_docs = []
    for doc in all_docs:
        tags = doc.get("tags_json") or []
        # 兼容 source_type='quiz' 或者 tags_json 中包含 'quiz' 的情况
        if doc.get("source_type") == "quiz" or "quiz" in tags:
            quiz_docs.append(doc)
    
    if not quiz_docs:
        st.info("暂无试题记录。请在「录入新试题」中添加。")
    else:
        left, right = st.columns([1, 2.5])
        with left:
            options = {f"{doc.get('title')} | {doc.get('created_at', '')[:10]}": doc for doc in quiz_docs}
            selected_label = st.selectbox("选择试题", list(options.keys()))
            selected_doc = options[selected_label] if options else None
            
        with right:
            if selected_doc:
                raw_content = selected_doc.get("content", "")
                questions = parse_quiz_content(raw_content)
                
                if not questions:
                    # 如果不符合结构化格式，直接渲染普通预览
                    st.info("💡 当前试卷未使用标准格式，按普通文档渲染：")
                    render_document_preview(selected_doc)
                else:
                    st.markdown(f"### {selected_doc.get('title')}")
                    st.caption(f"共解析出 {len(questions)} 道试题 | {selected_doc.get('created_at', '')[:10]}")
                    
                    # 引入单题轮询（上一题/下一题）模式
                    if f"current_q_idx_{selected_doc['id']}" not in st.session_state:
                        st.session_state[f"current_q_idx_{selected_doc['id']}"] = 0
                        
                    current_idx = st.session_state[f"current_q_idx_{selected_doc['id']}"]
                    q = questions[current_idx]
                    
                    # 顶部导航按钮
                    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                    with nav_col1:
                        if st.button("⬅️ 上一题", disabled=(current_idx == 0), use_container_width=True):
                            st.session_state[f"current_q_idx_{selected_doc['id']}"] -= 1
                            st.rerun()
                    with nav_col2:
                        st.markdown(f"<div style='text-align: center; padding-top: 5px;'><b>进度：{current_idx + 1} / {len(questions)}</b></div>", unsafe_allow_html=True)
                    with nav_col3:
                        if st.button("下一题 ➡️", disabled=(current_idx == len(questions) - 1), use_container_width=True):
                            st.session_state[f"current_q_idx_{selected_doc['id']}"] += 1
                            st.rerun()
                            
                    st.divider()
                    
                    # 渲染当前题目
                    st.markdown(f"#### {q['title']}".replace('$', r'\$'))
                    if q["description"]:
                        st.markdown(q["description"].replace('$', r'\$'))
                    
                    st.write("") # 间距
                    
                    # 交互式回答区域
                    if not q["answer"]:
                        st.warning("此题尚未回答")
                        with st.form(f"answer_form_{selected_doc['id']}_{current_idx}"):
                            user_ans = st.text_area("✍️ 在此作答", height=200, placeholder="请写下你的分析或判断...")
                            if st.form_submit_button("保存回答并进入下一题", use_container_width=True):
                                # 替换原文中的块
                                new_block = q["raw_block"].replace("### 我的回答：", f"### 我的回答：\n{user_ans}")
                                new_content = raw_content.replace(q["raw_block"], new_block)
                                
                                # 更新入库
                                payload = dict(selected_doc)
                                payload["content"] = new_content
                                upsert_document(payload)
                                
                                st.success("回答已保存！")
                                # 自动跳转下一题
                                if current_idx < len(questions) - 1:
                                    st.session_state[f"current_q_idx_{selected_doc['id']}"] += 1
                                st.rerun()
                    else:
                        st.markdown("**✅ 我的回答：**")
                        st.success(q["answer"].replace('$', r'\$'))
                        
                    if q["feedback"]:
                        st.markdown("**🤖 AI 点评：**")
                        st.info(q["feedback"].replace('$', r'\$'))
