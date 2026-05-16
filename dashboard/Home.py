import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import (
    init_page_style,
    chips,
    metric_card,
    render_document_preview,
    section_title,
    show_table,
)
from kb.storage import (
    claim_validation_summary,
    fetch_latest_documents,
    init_db,
    list_extracted_claims_by_document_key,
    list_extracted_relations_by_document_key,
    list_extracted_tasks_by_document_key,
    list_claims,
    list_relations,
    list_tasks,
    search_documents,
)


init_page_style()
init_db()

st.title("杨云清 Dashboard")
st.caption("你的个人认知飞轮与决策仪表盘")

documents = fetch_latest_documents(limit=20)
tasks = list_tasks(limit=12)
claims = list_claims()
relations = list_relations()
claim_summary = claim_validation_summary()
markdown_documents = [
    doc for doc in documents if (doc.get("metadata_json") or {}).get("render_mode") == "markdown"
]
today_focus_tasks = tasks[:3]
recent_claims = claims[:5]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("知识文档", len(documents), "最近入库文档数量")
with col2:
    metric_card("待办任务", len(tasks), "需要跟进的执行动作")
with col3:
    metric_card("断言卡片", len(claims), "可复盘的研究判断")
with col4:
    metric_card("抽取关系", len(relations), "文档里提到的关系")
with col5:
    metric_card("已验证判断", claim_summary["counts"].get("validated_count", 0), "最近沉淀里被确认的判断")

top_left, top_right = st.columns([1.05, 0.95])
with top_left:
    section_title("今天先看什么", "把最少的注意力放在最关键的 3 件事上")
    if today_focus_tasks:
        for index, task in enumerate(today_focus_tasks, start=1):
            st.markdown(
                f"**{index}. {task.get('title', '未命名任务')}**  "
                f"\n`{task.get('priority', 'medium')}` · `{task.get('status', 'todo')}`  "
                f"\n{task.get('description') or '暂无说明'}"
            )
    else:
        st.info("当前没有待办任务")

with top_right:
    section_title("最近判断更新", "优先看最近新增的判断与断言")
    show_table(
        [
            {
                "subject": claim.get("subject"),
                "statement": claim.get("statement"),
                "cycle": claim.get("review_cycle"),
            }
            for claim in recent_claims
        ],
        height=270,
    )
    st.caption("更完整的入口在左侧导航中的“文档工作台”“认知闭环”。")

section_title("最近研究文档", "最近 3 篇 Markdown 文档及其自动抽取摘要")
recent_cols = st.columns(3)
recent_markdown_docs = markdown_documents[:3]
for idx, col in enumerate(recent_cols):
    with col:
        if idx < len(recent_markdown_docs):
            doc = recent_markdown_docs[idx]
            doc_key = doc.get("document_key") or doc.get("hash", "")
            doc_claims = list_extracted_claims_by_document_key(doc_key)
            doc_relations = list_extracted_relations_by_document_key(doc_key)
            doc_tasks = list_extracted_tasks_by_document_key(doc_key)
            st.markdown(f"### {doc.get('title')}")
            st.caption(f"{doc.get('source_name')} | {doc.get('doc_date') or ''}")
            chips(doc.get("tags_json", []))
            st.write((doc.get("summary") or doc.get("content") or "")[:180])
            c1, c2, c3 = st.columns(3)
            c1.metric("Claims", len(doc_claims))
            c2.metric("Relations", len(doc_relations))
            c3.metric("Tasks", len(doc_tasks))
            if doc_claims:
                st.markdown(f"- {doc_claims[0].get('statement')}")
            if doc_tasks:
                st.markdown(f"- {doc_tasks[0].get('title')}")
        else:
            st.info("暂无更多 Markdown 文档")

section_title("快速浏览文档", "需要时直接搜文档，不必离开首页")
search_text = st.text_input("搜索知识库", placeholder="例如：NVDA、CoWoS、HBM、护城河、CapEx")
matched_docs = search_documents(search_text, limit=50) if search_text else documents

list_col, preview_col = st.columns([0.95, 1.45])
with list_col:
    doc_options = {
        f"{doc.get('title')} | {doc.get('source_name')}": index
        for index, doc in enumerate(matched_docs)
    }
    if doc_options:
        selected_key = st.selectbox("选择文档", list(doc_options.keys()))
        selected_doc = matched_docs[doc_options[selected_key]]
    else:
        selected_doc = None
        st.info("没有匹配的文档")

    show_table(
        [
            {
                "title": doc.get("title"),
                "source": doc.get("source_name"),
                "date": doc.get("doc_date"),
                "tags": ",".join(doc.get("tags_json", [])),
            }
            for doc in matched_docs[:12]
        ],
        height=360,
    )

with preview_col:
    section_title("内容预览", "Markdown 会按知识文档直接渲染")
    render_document_preview(selected_doc if matched_docs else None)
    if selected_doc and (selected_doc.get("metadata_json") or {}).get("render_mode") == "markdown":
        document_key = selected_doc.get("document_key") or selected_doc.get("hash", "")
        ext_claims = list_extracted_claims_by_document_key(document_key)
        ext_relations = list_extracted_relations_by_document_key(document_key)
        ext_tasks = list_extracted_tasks_by_document_key(document_key)
        col1, col2, col3 = st.columns(3)
        col1.metric("抽取断言", len(ext_claims))
        col2.metric("抽取关系", len(ext_relations))
        col3.metric("抽取任务", len(ext_tasks))
        st.caption("更完整的逐篇检查可进入左侧导航中的“文档工作台”页面。")
