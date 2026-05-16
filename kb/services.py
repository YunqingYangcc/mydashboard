from typing import Any

from kb.constants import EXTRACTION_SOURCE_TYPE, RENDER_MODE_MARKDOWN
from kb.markdown_extract import ExtractResult, _guess_entity_type
from kb.storage import (
    delete_extracted_by_source_document_key,
    ensure_entity,
    get_document_by_key,
    insert_claim,
    insert_relation,
    insert_task,
    upsert_document,
)


def persist_document(document: dict[str, Any]) -> dict[str, Any]:
    return upsert_document(document)


def persist_extract_result(extract_result: ExtractResult, document: dict[str, Any]) -> dict[str, int]:
    document_key = document.get("document_key")
    document_row = get_document_by_key(document_key) if document_key else None
    metadata = {
        "source_document_key": document_key,
        "source_document_hash": document.get("hash"),
        "source_document_title": document.get("title"),
        "source_type": EXTRACTION_SOURCE_TYPE,
    }

    claim_count = 0
    relation_count = 0
    task_count = 0

    for claim in extract_result.claims:
        insert_claim(
            {
                "claim_type": "markdown_claim",
                "subject": claim["subject"],
                "statement": claim["statement"],
                "stance": claim.get("stance", "neutral"),
                "review_cycle": claim.get("review_cycle", "weekly"),
                "evidence_document_id": document_row.get("id") if document_row else None,
                "source_document_key": document_key,
                "metadata": metadata,
            }
        )
        claim_count += 1

    for relation in extract_result.relations:
        subject_id = ensure_entity(relation["subject"], _guess_entity_type(relation["subject"]))
        object_id = ensure_entity(relation["object"], _guess_entity_type(relation["object"]))
        insert_relation(
            {
                "subject_entity_id": subject_id,
                "relation_type": relation["relation_type"],
                "object_entity_id": object_id,
                "evidence_document_id": document_row.get("id") if document_row else None,
                "confidence": relation.get("confidence", 0.6),
                "note": f"自动抽取自 Markdown 文档：{document.get('title')}",
                "source_document_key": document_key,
                "metadata": metadata,
            }
        )
        relation_count += 1

    for task in extract_result.tasks:
        insert_task(
            {
                "plan_key": "P4",
                "title": task["title"],
                "description": task.get("description"),
                "cadence": task.get("cadence", "adhoc"),
                "priority": task.get("priority", "medium"),
                "source": task.get("source", EXTRACTION_SOURCE_TYPE),
                "source_document_key": document_key,
                "metadata": metadata,
            }
        )
        task_count += 1

    return {"claims": claim_count, "relations": relation_count, "tasks": task_count}


def persist_document_with_extract(document: dict[str, Any], extract_from_markdown) -> tuple[dict[str, Any], dict[str, int]]:
    saved = persist_document(document)
    saved_document = {**document, **saved}
    counts = {"claims": 0, "relations": 0, "tasks": 0}

    if document.get("metadata", {}).get("render_mode") == RENDER_MODE_MARKDOWN:
        delete_extracted_by_source_document_key(saved["document_key"])
        extract_result = extract_from_markdown(document.get("content", ""))
        counts = persist_extract_result(extract_result, saved_document)

    return saved_document, counts
