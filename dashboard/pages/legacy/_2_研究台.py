import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import (
    init_page_style,
    metric_card,
    render_document_preview,
    render_signal_summary,
    section_title,
    show_table,
)
from kb.constants import RELATION_TYPES
from kb.storage import (
    claim_validation_summary,
    ensure_entity,
    fetch_latest_documents,
    init_db,
    insert_action,
    insert_claim,
    insert_relation,
    insert_review,
    insert_task,
    latest_signal_score,
    list_actions,
    list_claims,
    list_disciplines,
    list_entities,
    list_plans,
    list_relations,
    list_reviews,
    list_signal_values,
    list_tasks,
    search_documents,
    update_claim_validation,
    upsert_plan,
)
from kb.utils import now_iso


init_db()
init_page_style()
st.title("研究台")
st.caption("把投资、周期、基础设施、认知执行放到一个研究工作面板里")

score = latest_signal_score() or {}
actions = list_actions(limit=30)
claims = list_claims(limit=100)
relations = list_relations()
tasks = list_tasks(limit=30)
claim_progress = claim_validation_summary()

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("动作建议", score.get("action_suggestion", "尚未生成"), "来自最新信号评分")
with col2:
    metric_card("行动记录", len(actions), "投资动作与跟踪结果")
with col3:
    metric_card("断言卡片", len(claims), f"已验证 {claim_progress['counts'].get('validated_count', 0)} 条")
with col4:
    metric_card("图谱关系", len(relations), "产业链关系与因果边")

tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs(
    ["P1 投资", "P2 周期", "P3 基础设施", "P4 执行复盘"]
)

with tab_p1:
    p1_score = latest_signal_score() or {}
    signal_values = list_signal_values(limit=20)
    disciplines = list_disciplines()

    left, right = st.columns([1.15, 1.0])
    with left:
        section_title("信号仪表盘", "6 维评分、动作建议与最新信号值")
        render_signal_summary(p1_score)
        show_table(signal_values, height=340)
    with right:
        section_title("新增行动记录", "把每一次加仓、减仓、观望沉淀为数据资产")
        with st.form("research_p1_action_form"):
            asset = st.text_input("资产", value="NVDA")
            action_type = st.selectbox("动作", ["加仓", "减仓", "观望"])
            size = st.number_input("仓位变化", value=0.0, step=0.1)
            reason_signal_ids = st.text_input(
                "触发信号", value="valuation_forward_pe,rates_real_yield"
            )
            risk_control = st.text_input("风险控制", value="遵守仓位上限，不追涨")
            result_followup = st.text_area("后续跟踪", value="下周复核财报与利率条件")
            submitted = st.form_submit_button("保存行动记录")
            if submitted:
                insert_action(
                    {
                        "action_time": now_iso(),
                        "asset": asset,
                        "action_type": action_type,
                        "size": size,
                        "reason_signal_ids": reason_signal_ids,
                        "risk_control": risk_control,
                        "result_followup": result_followup,
                    }
                )
                st.success("已保存")

    bottom_left, bottom_right = st.columns([1.2, 0.8])
    with bottom_left:
        section_title("行动记录")
        show_table(list_actions(limit=30), height=280)
    with bottom_right:
        section_title("纪律库")
        show_table(disciplines, height=280)

with tab_p2:
    cycle_claims = list_claims(claim_type="cycle_assertion")
    docs = fetch_latest_documents(limit=30)

    left, right = st.columns([1.0, 1.1])
    with left:
        section_title("新增周期断言", "维护 PC→互联网→移动→云→AI 周期坐标系")
        with st.form("research_p2_claim_form"):
            subject = st.text_input("主题", value="AI 周期")
            statement = st.text_area(
                "断言", value="AI 周期仍处于基础设施扩张阶段，应用爆发尚未全面兑现。"
            )
            stance = st.selectbox("立场", ["support", "neutral", "contradict"])
            review_cycle = st.selectbox("复盘周期", ["quarterly", "monthly", "weekly"])
            submitted = st.form_submit_button("新增断言")
            if submitted:
                insert_claim(
                    {
                        "claim_type": "cycle_assertion",
                        "subject": subject,
                        "statement": statement,
                        "stance": stance,
                        "review_cycle": review_cycle,
                    }
                )
                st.success("季度断言已写入")

        section_title("当前断言")
        show_table(cycle_claims, height=360)
        section_title("判断验证", "把判断标记为已验证、待观察或已证伪")
        claim_options = {
            f"{claim.get('subject')} | {claim.get('statement')[:28]}": claim.get("id")
            for claim in cycle_claims[:20]
        }
        if claim_options:
            with st.form("research_p2_claim_validation_form"):
                selected_label = st.selectbox("选择断言", list(claim_options.keys()))
                validation_status = st.selectbox("验证结果", ["pending", "validated", "invalidated"])
                validation_note = st.text_area("验证说明", value="补充证据、反例或验证结论")
                if st.form_submit_button("保存验证结果"):
                    update_claim_validation(
                        claim_options[selected_label],
                        validation_status,
                        validation_note or None,
                    )
                    st.success("验证结果已更新")

    with right:
        section_title("周期研究文档", "从飞书导出的 Markdown 可以直接作为判断素材")
        search_text = st.text_input(
            "搜索周期研究文档",
            placeholder="例如：周期、AI、云、移动、PC",
            key="research_p2_doc_search",
        )
        matched_docs = search_documents(search_text, limit=30) if search_text else docs
        options = {
            f"{doc.get('title')} | {doc.get('source_name')}": idx
            for idx, doc in enumerate(matched_docs)
        }
        selected = (
            matched_docs[options[st.selectbox("选择文档", list(options.keys()), key="research_p2_doc_select")]]
            if options
            else None
        )
        render_document_preview(selected)

    section_title("断言验证状态")
    show_table(
        [
            {
                "subject": claim.get("subject"),
                "statement": claim.get("statement"),
                "validation": claim.get("validation_status", "pending"),
                "note": claim.get("validation_note"),
            }
            for claim in cycle_claims
        ],
        height=220,
    )

with tab_p3:
    entities = list_entities()
    if not entities:
        ensure_entity("AI 基础设施", "theme", "AI 产业链事实库")
        ensure_entity("CoWoS", "technology", "先进封装")
        entities = list_entities()

    entity_options = {f"{row['name']} ({row['entity_type']})": row["id"] for row in entities}
    infra_docs = fetch_latest_documents(limit=30)

    left, right = st.columns([1.0, 1.1])
    with left:
        section_title("事实卡补录", "把 GPU / HBM / CoWoS / 电力约束挂到图谱")
        with st.form("research_p3_relation_form"):
            subject_label = st.selectbox("主体实体", list(entity_options.keys()))
            object_label = st.selectbox(
                "客体实体",
                list(entity_options.keys()),
                index=min(1, len(entity_options) - 1),
            )
            relation_type = st.selectbox(
                "关系类型",
                RELATION_TYPES,
            )
            note = st.text_area("说明", value="请补充证据来源与判断背景")
            confidence = st.slider("置信度", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
            submitted = st.form_submit_button("新增关系")
            if submitted:
                insert_relation(
                    {
                        "subject_entity_id": entity_options[subject_label],
                        "relation_type": relation_type,
                        "object_entity_id": entity_options[object_label],
                        "confidence": confidence,
                        "note": note,
                    }
                )
                st.success("关系已写入")

        section_title("关系列表")
        show_table(list_relations(), height=360)

    with right:
        section_title("图谱文档来源", "支持 Markdown 文档，也支持图片资料预览")
        search_text = st.text_input(
            "搜索基础设施文档",
            placeholder="例如：HBM、CoWoS、电力、封装",
            key="research_p3_doc_search",
        )
        matched_docs = search_documents(search_text, limit=30) if search_text else infra_docs
        options = {
            f"{doc.get('title')} | {doc.get('source_name')}": idx
            for idx, doc in enumerate(matched_docs)
        }
        selected = (
            matched_docs[options[st.selectbox("选择素材", list(options.keys()), key="research_p3_doc_select")]]
            if options
            else None
        )
        render_document_preview(selected)

    section_title("实体列表")
    show_table(list_entities(), height=260)

with tab_p4:
    plans = list_plans()
    reviews = list_reviews(limit=20)

    subtab1, subtab2, subtab3 = st.tabs(["计划布局", "任务执行", "复盘沉淀"])

    with subtab1:
        left, right = st.columns([0.95, 1.1])
        with left:
            section_title("新增或更新计划", "把认知提升主线持续入库")
            with st.form("research_p4_plan_form"):
                plan_key = st.text_input("计划代号", value="P4_custom")
                name = st.text_input("计划名称", value="周报自动化")
                weight = st.number_input(
                    "权重", min_value=0.0, max_value=1.0, value=0.1, step=0.05
                )
                stage_goal = st.text_area("阶段目标", value="将输出沉淀为卡片、文档和图谱。")
                cadence = st.selectbox("节奏", ["weekly", "monthly", "quarterly"])
                if st.form_submit_button("保存计划"):
                    upsert_plan(
                        {
                            "plan_key": plan_key,
                            "name": name,
                            "weight": weight,
                            "stage_goal": stage_goal,
                            "cadence": cadence,
                        }
                    )
                    st.success("计划已保存")
        with right:
            section_title("计划总览")
            show_table(plans, height=340)

    with subtab2:
        left, right = st.columns([0.95, 1.1])
        with left:
            section_title("新增任务", "把长期动作拆成可执行颗粒")
            with st.form("research_p4_task_form"):
                title = st.text_input("任务标题", value="每周生成持仓简报")
                description = st.text_area(
                    "任务说明", value="自动汇总信号、行动、图谱更新与输出记录。"
                )
                due_date = st.text_input("截止日期", value="")
                cadence = st.selectbox("任务节奏", ["weekly", "monthly", "quarterly", "adhoc"])
                priority = st.selectbox("优先级", ["high", "medium", "low"])
                if st.form_submit_button("新增任务"):
                    insert_task(
                        {
                            "title": title,
                            "description": description,
                            "due_date": due_date or None,
                            "cadence": cadence,
                            "priority": priority,
                        }
                    )
                    st.success("任务已保存")
        with right:
            section_title("任务总览")
            show_table(list_tasks(limit=30), height=340)

    with subtab3:
        left, right = st.columns([0.95, 1.1])
        with left:
            section_title("新增复盘", "把输入、输出、偏差与下一步持续沉淀")
            with st.form("research_p4_review_form"):
                review_type = st.selectbox("复盘类型", ["weekly", "monthly", "quarterly"])
                review_period = st.text_input("复盘周期", value="2026-W20")
                summary = st.text_area("总结", value="本周的关键增量是什么？")
                reflection = st.text_area("反思", value="哪些判断偏差需要修正？")
                next_actions = st.text_area("下阶段动作", value="下周优先做什么？")
                score_value = st.slider("自评分", 0, 100, 70)
                if st.form_submit_button("保存复盘"):
                    insert_review(
                        {
                            "review_type": review_type,
                            "review_period": review_period,
                            "summary": summary,
                            "reflection": reflection,
                            "next_actions": next_actions,
                            "score": score_value,
                        }
                    )
                    st.success("复盘已保存")
        with right:
            section_title("复盘记录")
            show_table(reviews, height=340)
