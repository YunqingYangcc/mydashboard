import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, metric_card, section_title, show_table
from kb.constants import EXTRACTION_SOURCE_TYPE, RELATION_TYPES
from kb.storage import ensure_entity, init_db, list_claims, list_entities, list_relations


init_db()
init_page_style()
st.title("认知图谱")

if not list_entities():
    ensure_entity("NVDA", "company", "英伟达")
    ensure_entity("HBM", "technology", "高带宽内存")

all_entities = list_entities()
all_claims = list_claims()


def build_graphviz(rows: list[dict]) -> str:
    lines = [
        "digraph G {",
        'rankdir="LR";',
        'graph [bgcolor="transparent"];',
        'node [shape="box", style="rounded,filled", fillcolor="#1f2430", color="#4f5b77", fontcolor="white"];',
        'edge [color="#7aa2f7", fontcolor="#c0caf5"];',
    ]
    for row in rows:
        subject = row["subject_name"].replace('"', '\\"')
        obj = row["object_name"].replace('"', '\\"')
        relation = row["relation_type"].replace('"', '\\"')
        lines.append(f'"{subject}" -> "{obj}" [label="{relation}"];')
    lines.append("}")
    return "\n".join(lines)


with st.sidebar:
    relation_type = st.selectbox(
        "关系类型",
        ["", *RELATION_TYPES],
    )
    source_scope = st.selectbox("来源", ["全部", "自动抽取", "手动录入"])
    graph_limit = st.slider("图谱边数量", min_value=5, max_value=80, value=20, step=5)

filtered_relations = list_relations(relation_type=relation_type or None)
if source_scope == "自动抽取":
    filtered_relations = [
        row
        for row in filtered_relations
        if (row.get("metadata_json") or {}).get("source_type") == EXTRACTION_SOURCE_TYPE
    ]
elif source_scope == "手动录入":
    filtered_relations = [
        row
        for row in filtered_relations
        if (row.get("metadata_json") or {}).get("source_type") != EXTRACTION_SOURCE_TYPE
    ]

graph_rows = filtered_relations[:graph_limit]

col1, col2, col3 = st.columns(3)
with col1:
    metric_card("实体数", len(all_entities), "图谱中的节点数量")
with col2:
    metric_card("关系数", len(filtered_relations), "当前筛选条件下的边数量")
with col3:
    metric_card("断言数", len(all_claims), "可复盘的判断卡片")

tab1, tab2 = st.tabs(["关系网络图", "明细列表"])

with tab1:
    section_title("关系网络图", "适合快速检查自动抽取是否合理")
    if graph_rows:
        st.graphviz_chart(build_graphviz(graph_rows), use_container_width=True)
    else:
        st.info("当前筛选条件下没有关系可展示")

with tab2:
    left, right = st.columns([1.05, 0.95])
    with left:
        section_title("关系")
        show_table(filtered_relations, height=360)
        section_title("断言")
        show_table(all_claims, height=280)
    with right:
        section_title("实体")
        show_table(all_entities, height=660)
