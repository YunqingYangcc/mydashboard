import json
import re
from datetime import datetime

from openai import OpenAI

from kb.config import (
    MODEL_DIRECTOR,
    MODEL_RESEARCHER_A,
    MODEL_RESEARCHER_B,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    XIAOMI_API_KEY,
    XIAOMI_BASE_URL,
    ZHIPU_API_KEY,
    ZHIPU_BASE_URL,
)
from kb.storage import (
    fetch_latest_documents,
    finish_run,
    insert_ai_output,
    insert_claim,
    insert_run,
    latest_signal_score,
    list_claims,
)


RESEARCHER_PROMPT = """
你是一名研究员。请基于以下认知操作系统上下文，输出严格 JSON：
{{
  "summary": "一句话结论",
  "bullish_score": 0,
  "key_factors": ["因素1", "因素2"],
  "claims": [{{"subject": "AI 基础设施", "statement": "CoWoS 仍是约束变量", "stance": "support", "review_cycle": "quarterly"}}],
  "tasks": ["下周跟踪点1", "下周跟踪点2"]
}}

上下文：
{context}
""".strip()

DIRECTOR_PROMPT = """
你是策略总监。请融合两位研究员观点，输出严格 JSON：
{{
  "summary": "最终综合判断",
  "action": "加仓|减仓|观望",
  "confidence": 0.0,
  "bullish_score": 0,
  "key_factors": ["共识要点1", "共识要点2"],
  "final_claims": [{{"subject": "NVDA", "statement": "估值需要盈利兑现配合", "stance": "neutral", "review_cycle": "weekly"}}]
}}

研究员A：
{researcher_a}

研究员B：
{researcher_b}
""".strip()


def _provider_config(role: str) -> dict:
    mapping = {
        "researcher_a": {
            "provider": "zhipu",
            "model": MODEL_RESEARCHER_A,
            "base_url": ZHIPU_BASE_URL or OPENAI_BASE_URL,
            "api_key": ZHIPU_API_KEY or OPENAI_API_KEY,
        },
        "researcher_b": {
            "provider": "xiaomi",
            "model": MODEL_RESEARCHER_B,
            "base_url": XIAOMI_BASE_URL or OPENAI_BASE_URL,
            "api_key": XIAOMI_API_KEY or OPENAI_API_KEY,
        },
        "director": {
            "provider": "siliconflow",
            "model": MODEL_DIRECTOR,
            "base_url": SILICONFLOW_BASE_URL or OPENAI_BASE_URL,
            "api_key": SILICONFLOW_API_KEY or OPENAI_API_KEY,
        },
    }
    return mapping[role]


def _extract_json(text: str) -> dict:
    matched = re.search(r"\{[\s\S]*\}", text)
    if not matched:
        return {}
    try:
        return json.loads(matched.group(0))
    except json.JSONDecodeError:
        return {}


def _ask(role: str, prompt: str):
    cfg = _provider_config(role)
    if not cfg["api_key"]:
        mock = {
            "summary": f"{role} mock 结论：保持跟踪。",
            "bullish_score": 55,
            "key_factors": ["缺少 API Key，当前为 mock", "请配置真实模型接口"],
            "claims": [
                {
                    "subject": "system",
                    "statement": f"{role} 运行于 mock 模式",
                    "stance": "neutral",
                    "review_cycle": "weekly",
                }
            ],
            "tasks": ["配置模型密钥", "补充真实文档与指标"],
        }
        return json.dumps(mock, ensure_ascii=False), mock, cfg

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    response = client.chat.completions.create(
        model=cfg["model"],
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "你是严谨研究助手，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or "{}"
    return content, _extract_json(content), cfg


def _context_text() -> str:
    lines = ["最新信号评分：", json.dumps(latest_signal_score() or {}, ensure_ascii=False)]
    lines.append("最新文档：")
    for document in fetch_latest_documents(limit=5):
        lines.append(f"- {document['title']}: {document.get('summary') or ''}")
    lines.append("已有断言：")
    for claim in list_claims(limit=5):
        lines.append(f"- {claim['subject']}: {claim['statement']}")
    return "\n".join(lines)


def run_multi_role_workflow() -> dict:
    run_id = f"ai_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    insert_run(run_id, "ai_workflow", "running")

    try:
        context = _context_text()

        prompt_a = RESEARCHER_PROMPT.format(context=context)
        response_a, meta_a, cfg_a = _ask("researcher_a", prompt_a)
        insert_ai_output(
            {
                "run_id": run_id,
                "role": "researcher_a",
                "provider": cfg_a["provider"],
                "model": cfg_a["model"],
                "prompt_text": prompt_a,
                "response_text": response_a,
                "json_metadata": meta_a,
            }
        )

        prompt_b = RESEARCHER_PROMPT.format(context=context)
        response_b, meta_b, cfg_b = _ask("researcher_b", prompt_b)
        insert_ai_output(
            {
                "run_id": run_id,
                "role": "researcher_b",
                "provider": cfg_b["provider"],
                "model": cfg_b["model"],
                "prompt_text": prompt_b,
                "response_text": response_b,
                "json_metadata": meta_b,
            }
        )

        prompt_director = DIRECTOR_PROMPT.format(
            researcher_a=response_a, researcher_b=response_b
        )
        response_director, meta_director, cfg_director = _ask("director", prompt_director)
        insert_ai_output(
            {
                "run_id": run_id,
                "role": "director",
                "provider": cfg_director["provider"],
                "model": cfg_director["model"],
                "prompt_text": prompt_director,
                "response_text": response_director,
                "json_metadata": meta_director,
            }
        )

        for claim in meta_director.get("final_claims", []):
            insert_claim(
                {
                    "claim_type": "director_consensus",
                    "subject": claim.get("subject", "unknown"),
                    "statement": claim.get("statement", ""),
                    "stance": claim.get("stance", "neutral"),
                    "review_cycle": claim.get("review_cycle", "weekly"),
                    "metadata": {"run_id": run_id},
                }
            )

        finish_run(run_id, "completed", {"roles": 3})
        return {
            "run_id": run_id,
            "researcher_a": meta_a,
            "researcher_b": meta_b,
            "director": meta_director,
        }
    except Exception as exc:  # noqa: BLE001
        finish_run(run_id, "failed", {"error": str(exc)})
        raise
