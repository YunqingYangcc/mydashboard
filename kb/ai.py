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
    list_signal_definitions,
    list_recent_signal_values,
    latest_signal_score,
    list_anomaly_observations,
    insert_signal_report,
    check_claims_for_signal_change,
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


SIGNAL_REPORT_PROMPT = """
你是资深的美股半导体/AI行业投研分析师。请根据以下信号数据，生成一份简洁有力的分析报告。

## 当前信号状态
{signal_status}

## 综合评分
{score_info}

## 异常数据
{anomalies}

## 要求
1. 用 Markdown 格式输出
2. 第一部分：核心结论（1-2句话）
3. 第二部分：各维度信号解读（估值/需求/基本面/宏观/情绪）
4. 第三部分：信号间的因果链分析（哪些信号相互关联、传导路径）
5. 第四部分：行动建议（具体的观察重点和操作方向）
6. 语言简洁，避免废话，直接给判断
""".strip()


def generate_signal_report(provider: str = "gold") -> dict:
    """生成信号分析报告"""
    # 收集数据
    signal_defs = list_signal_definitions()
    recent_values = list_recent_signal_values(limit=200)
    score = latest_signal_score()
    anomalies = list_anomaly_observations(limit=10)

    # 按维度分组信号状态
    dim_status = {}
    for sig in signal_defs:
        dim = sig["dimension"]
        if dim not in dim_status:
            dim_status[dim] = []
        # 找最新值
        latest_sv = None
        for sv in recent_values:
            if sv["signal_key"] == sig["signal_key"]:
                latest_sv = sv
                break
        entry = f"{sig['name']}: {latest_sv.get('raw_value', 'N/A') if latest_sv else 'N/A'} → {latest_sv.get('status', '无数据') if latest_sv else '无数据'}"
        if latest_sv and latest_sv.get("reasoning"):
            entry += f"（{latest_sv['reasoning']}）"
        dim_status[dim].append(entry)

    signal_status_text = ""
    for dim, items in dim_status.items():
        signal_status_text += f"### {dim}\n"
        for item in items:
            signal_status_text += f"- {item}\n"
        signal_status_text += "\n"

    score_text = "暂无评分"
    if score:
        score_text = f"综合得分: {score.get('total_score', 0)}, 动作建议: {score.get('action_suggestion', 'hold')}"

    anomaly_text = "无异常数据"
    if anomalies:
        anomaly_text = "\n".join(
            [f"- {a['metric_key']}: 值={a['raw_value']}, z-score={a.get('z_score', 'N/A')}" for a in anomalies]
        )

    prompt = SIGNAL_REPORT_PROMPT.format(
        signal_status=signal_status_text,
        score_info=score_text,
        anomalies=anomaly_text,
    )

    content, meta, cfg = _ask_text(prompt, provider)
    used_fallback = bool(meta.get("used_fallback"))

    if not used_fallback and content:
        from kb.utils import now_iso
        insert_signal_report(
            report_date=now_iso()[:10],
            report_type="ai_weekly",
            content=content,
            model=cfg.get("model", ""),
            snapshot={"total_score": score.get("total_score") if score else None},
        )

    return {
        "content": content,
        "used_fallback": used_fallback,
        "model": cfg.get("model", ""),
        "reason": meta.get("reason", ""),
    }
