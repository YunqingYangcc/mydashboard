import re
from dataclasses import dataclass
from typing import Any

from kb.constants import (
    CLAIM_HEADERS,
    CLAIM_PREFIXES,
    KNOWN_COMPANIES,
    KNOWN_METRIC,
    KNOWN_TECH,
    KNOWN_THEME,
    RELATION_ALIASES,
    RELATION_HEADERS,
    RELATION_PREFIXES,
    RELATION_TYPES,
    TASK_HEADERS,
    TASK_PREFIXES,
)
from kb.logger import logger


@dataclass(frozen=True)
class ExtractResult:
    claims: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    tasks: list[dict[str, Any]]


def _normalize_header(value: str) -> str:
    return value.strip().strip("#").strip().lower()


def _match_header(header: str, candidates: set[str]) -> bool:
    normalized = _normalize_header(header)
    return any(normalized == item or normalized.startswith(f"{item}(") or normalized.startswith(f"{item}（") for item in candidates)


def _iter_sections(markdown_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_header = "default"
    sections[current_header] = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if re.match(r"^\s*#{1,6}\s+", line):
            current_header = _normalize_header(re.sub(r"^\s*#{1,6}\s+", "", line))
            sections.setdefault(current_header, [])
            continue
        sections.setdefault(current_header, []).append(line)
    return sections


def _extract_bullets(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[-*]\s+", stripped):
            items.append(re.sub(r"^[-*]\s+", "", stripped).strip())
        elif re.match(r"^\d+\.\s+", stripped):
            items.append(re.sub(r"^\d+\.\s+", "", stripped).strip())
    return items


def _extract_paragraph_items(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    buffer: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            continue
        buffer.append(stripped)

    if buffer:
        paragraphs.append(" ".join(buffer).strip())
    return paragraphs


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _guess_entity_type(name: str) -> str:
    lowered = name.lower().strip()
    if lowered in KNOWN_COMPANIES or re.fullmatch(r"[A-Z]{2,6}", name.strip()):
        return "company"
    if lowered in KNOWN_THEME or any(keyword in lowered for keyword in ("周期", "infrastructure", "demand", "生态", "产业链")):
        return "theme"
    if lowered in KNOWN_TECH or any(keyword in lowered for keyword in ("gpu", "hbm", "cowos", "cuda", "封装", "算力", "推理", "训练", "芯片")):
        return "technology"
    if lowered in KNOWN_METRIC or any(keyword in lowered for keyword in ("pe", "capex", "yield", "估值", "利率", "毛利率", "营收")):
        return "metric"
    if any(keyword in lowered for keyword in ("法案", "监管", "政策", "关税")):
        return "policy"
    if any(keyword in lowered for keyword in ("财报", "电话会", "发布会", "业绩", "会议")):
        return "event"
    return "concept"


def _normalize_relation_type(value: str) -> str | None:
    return RELATION_ALIASES.get(value.strip().lower()) or RELATION_ALIASES.get(value.strip())


def _parse_relation_line(text: str) -> dict[str, str] | None:
    arrow_match = re.match(
        r"^\s*(.+?)\s*(?:->|=>|→)\s*([A-Za-z_\u4e00-\u9fff]+)\s*(?:->|=>|→)\s*(.+?)\s*$",
        text,
    )
    if arrow_match:
        subject, relation_type, obj = arrow_match.groups()
        relation_type = _normalize_relation_type(relation_type)
        if relation_type in RELATION_TYPES:
            return {
                "subject": subject.strip(),
                "relation_type": relation_type,
                "object": obj.strip(),
            }

    word_match = re.match(
        r"^\s*(.+?)\s+(causes|drives|depends_on|constrains|competes_with|supplies_to|buys_from|signals|implies|priced_by|supports|contradicts|导致|驱动|带动|依赖|取决于|约束|限制|竞争|供应给|采购自|指向|预示|意味着|说明|支持|反驳)\s+(.+?)\s*$",
        text,
    )
    if word_match:
        subject, relation_type, obj = word_match.groups()
        return {
            "subject": subject.strip(),
            "relation_type": _normalize_relation_type(relation_type.strip()) or relation_type.strip(),
            "object": obj.strip(),
        }
    return None


def _guess_claim_subject(statement: str) -> str:
    candidates = [
        "NVDA",
        "NVIDIA",
        "CoWoS",
        "HBM",
        "Meta",
        "Microsoft",
        "Google",
        "Amazon",
        "AI 周期",
        "AI 基础设施",
    ]
    lowered = statement.lower()
    for candidate in candidates:
        if candidate.lower() in lowered:
            return candidate
    return "研究判断"


def _extract_prefixed_items(lines: list[str], prefixes: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        for prefix in prefixes:
            match = re.match(rf"^\s*{re.escape(prefix)}\s*[:：]\s*(.+?)\s*$", stripped, flags=re.IGNORECASE)
            if match:
                items.append(match.group(1).strip())
                break
    return items


def extract_from_markdown(markdown_text: str) -> ExtractResult:
    sections = _iter_sections(markdown_text)
    claims: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    default_lines = sections.get("default", [])

    for header, lines in sections.items():
        bullets = _extract_bullets(lines)
        paragraphs = _extract_paragraph_items(lines)
        if _match_header(header, CLAIM_HEADERS):
            for item in _dedupe_preserve_order(bullets + paragraphs):
                claims.append(
                    {
                        "subject": _guess_claim_subject(item),
                        "statement": item,
                        "stance": "neutral",
                        "review_cycle": "weekly",
                    }
                )
        elif _match_header(header, RELATION_HEADERS):
            for item in _dedupe_preserve_order(bullets + paragraphs):
                parsed = _parse_relation_line(item)
                if parsed:
                    relations.append(parsed)
                else:
                    logger.info("Skipping unsupported relation line: %s", item)
        elif _match_header(header, TASK_HEADERS):
            for item in _dedupe_preserve_order(bullets + paragraphs):
                tasks.append(
                    {
                        "title": item,
                        "description": "由 Markdown 文档自动抽取",
                        "cadence": "adhoc",
                        "priority": "medium",
                        "source": "markdown_extract",
                    }
                )

    for item in _extract_prefixed_items(default_lines, CLAIM_PREFIXES):
        claims.append(
            {
                "subject": _guess_claim_subject(item),
                "statement": item,
                "stance": "neutral",
                "review_cycle": "weekly",
            }
        )

    for item in _extract_prefixed_items(default_lines, TASK_PREFIXES):
        tasks.append(
            {
                "title": item,
                "description": "由 Markdown 文档自动抽取",
                "cadence": "adhoc",
                "priority": "medium",
                "source": "markdown_extract",
            }
        )

    for item in _extract_prefixed_items(default_lines, RELATION_PREFIXES):
        parsed = _parse_relation_line(item)
        if parsed:
            relations.append(parsed)

    claims = [
        {
            **claim,
            "statement": claim["statement"].strip(),
        }
        for claim in claims
        if claim["statement"].strip()
    ]
    relations = [
        relation
        for relation in relations
        if relation["subject"].strip() and relation["object"].strip()
    ]
    tasks = [
        {
            **task,
            "title": task["title"].strip(),
        }
        for task in tasks
        if task["title"].strip()
    ]

    return ExtractResult(claims=claims, relations=relations, tasks=tasks)


def save_extract_result(
    extract_result: ExtractResult,
    document: dict[str, Any],
) -> dict[str, int]:
    from kb.services import persist_extract_result

    return persist_extract_result(extract_result, document)
