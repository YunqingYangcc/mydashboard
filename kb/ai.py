from datetime import datetime, timezone

from openai import OpenAI

from kb.config import (
    MODEL_DIRECTOR,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    GOLD_AI_API_KEY,
    GOLD_AI_BASE_URL,
    GOLD_AI_MODEL,
    ZHIPU_GOLD_AI_API_KEY,
    ZHIPU_GOLD_AI_BASE_URL,
    ZHIPU_GOLD_AI_MODEL,
    XIAOMI_GOLD_AI_API_KEY,
    XIAOMI_GOLD_AI_BASE_URL,
    XIAOMI_GOLD_AI_MODEL,
)
from kb.storage import (
    finish_run,
    insert_ai_output,
    insert_run,
    get_connection,
)
from kb.utils import now_iso

UPDATE_DOC_PROMPT = """
你是资深的 AI 投研总监。请对以下名为《{title}》的知识库文章进行全面更新、润色和认知升维。
你可以：
1. 优化和重构原有的 Markdown 结构，使其更具逻辑性和可读性。
2. 基于你的知识储备，补充更深度的产业链洞察、前沿数据或逻辑推演。
3. 在文末增加一个「💡 AI 认知迭代补充」的总结段落，简述你做了哪些补充。

请必须且只能输出更新后的完整 Markdown 全文，不要输出任何如“好的，以下是更新后的内容”等开场白或废话。

原文内容：
{content}
""".strip()

def _provider_config(provider: str = "gold") -> dict:
    """获取 AI 提供商配置
    
    Args:
        provider: 提供商类型，可选 'gold', 'siliconflow', 'zhipu', 'xiaomi', 'openai'
    
    Returns:
        包含 provider, model, base_url, api_key 的配置字典
    """
    import os
    
    # Gold AI (默认)
    if provider == "gold" or not provider:
        api_key = GOLD_AI_API_KEY or os.getenv("GOLD_AI_API_KEY", "")
        if api_key:
            return {
                "provider": "gold",
                "model": os.getenv("GOLD_AI_MODEL", GOLD_AI_MODEL),
                "base_url": os.getenv("GOLD_AI_BASE_URL", GOLD_AI_BASE_URL),
                "api_key": api_key,
            }
    
    # SiliconFlow
    if provider == "siliconflow":
        api_key = SILICONFLOW_API_KEY or os.getenv("SILICONFLOW_API_KEY", "")
        if api_key:
            return {
                "provider": "siliconflow",
                "model": os.getenv("MODEL_DIRECTOR", MODEL_DIRECTOR),
                "base_url": SILICONFLOW_BASE_URL or OPENAI_BASE_URL or "",
                "api_key": api_key,
            }
    
    # 智谱 Gold AI
    if provider == "zhipu":
        api_key = ZHIPU_GOLD_AI_API_KEY or os.getenv("ZHIPU_GOLD_AI_API_KEY", "")
        if api_key:
            return {
                "provider": "zhipu",
                "model": os.getenv("ZHIPU_GOLD_AI_MODEL", ZHIPU_GOLD_AI_MODEL),
                "base_url": os.getenv("ZHIPU_GOLD_AI_BASE_URL", ZHIPU_GOLD_AI_BASE_URL),
                "api_key": api_key,
            }
    
    # 小米 MiMo
    if provider == "xiaomi":
        api_key = XIAOMI_GOLD_AI_API_KEY or os.getenv("XIAOMI_GOLD_AI_API_KEY", "")
        if api_key:
            return {
                "provider": "xiaomi",
                "model": os.getenv("XIAOMI_GOLD_AI_MODEL", XIAOMI_GOLD_AI_MODEL),
                "base_url": os.getenv("XIAOMI_GOLD_AI_BASE_URL", XIAOMI_GOLD_AI_BASE_URL),
                "api_key": api_key,
            }
    
    # OpenAI (备选)
    if provider == "openai":
        api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        if api_key:
            return {
                "provider": "openai",
                "model": os.getenv("MODEL_DIRECTOR", MODEL_DIRECTOR),
                "base_url": OPENAI_BASE_URL or "https://api.openai.com/v1",
                "api_key": api_key,
            }
    
    # 回退到 siliconflow
    api_key = SILICONFLOW_API_KEY or os.getenv("SILICONFLOW_API_KEY", "") or OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
    return {
        "provider": "siliconflow",
        "model": os.getenv("MODEL_DIRECTOR", MODEL_DIRECTOR),
        "base_url": (SILICONFLOW_BASE_URL or OPENAI_BASE_URL) or "https://api.siliconflow.cn/v1",
        "api_key": api_key,
    }

def _ask_text(prompt: str, provider: str = "gold"):
    cfg = _provider_config(provider)
    if not cfg.get("api_key"):
        return "", {"used_fallback": True, "reason": "missing_api_key"}, cfg

    try:
        client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
        response = client.chat.completions.create(
            model=cfg["model"],
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "你是资深的投资与研究助手。请直接输出 Markdown 文本，不要有任何多余的寒暄。",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        return "", {"used_fallback": True, "reason": str(exc)}, cfg

    # 清理可能带有的 markdown code block 标记
    if content.startswith("```markdown"):
        content = content[11:]
    elif content.startswith("```md"):
        content = content[5:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    return content.strip(), {"used_fallback": False}, cfg


def _build_fallback_content(title: str, content: str, reason: str) -> str:
    fallback_note = (
        "## AI 更新状态\n"
        f"- 文章：{title}\n"
        f"- 本次未调用到真实模型。\n"
        f"- 原因：{reason}\n"
        "- 系统已保留原文，未自动覆写数据库。\n"
    )
    if "## AI 更新状态" in content:
        return content
    return f"{content.rstrip()}\n\n{fallback_note}\n"

def run_document_update_workflow(doc_id: str, title: str, content: str, provider: str = "gold") -> dict:
    run_id = f"ai_doc_update_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    insert_run(run_id, "ai_doc_update", "running")

    try:
        prompt = UPDATE_DOC_PROMPT.format(title=title, content=content)
        new_content, meta, cfg = _ask_text(prompt, provider)
        used_fallback = bool(meta.get("used_fallback"))
        result_content = (
            _build_fallback_content(title, content, str(meta.get("reason", "未知错误")))
            if used_fallback
            else new_content
        )

        insert_ai_output(
            {
                "run_id": run_id,
                "role": "director",
                "provider": cfg["provider"],
                "model": cfg["model"],
                "prompt_text": prompt,
                "response_text": result_content,
                "json_metadata": meta,
            }
        )

        # 只有真实模型返回成功时才覆写原文，避免认证失败污染知识库。
        if not used_fallback:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE documents SET content = ?, updated_at = ? WHERE id = ?",
                    (result_content, now_iso(), doc_id),
                )

        finish_run(run_id, "completed", {"doc_id": doc_id})
        return {
            "run_id": run_id,
            "new_content": result_content,
            "used_fallback": used_fallback,
            "message": meta.get("reason", ""),
        }
    except Exception as exc:
        finish_run(run_id, "failed", {"error": str(exc)})
        raise
