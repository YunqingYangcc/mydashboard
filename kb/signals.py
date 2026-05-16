from collections import Counter, defaultdict
from datetime import date

from kb.storage import (
    insert_signal_score,
    insert_signal_value,
    latest_observation_map,
    upsert_signal_definition,
)


SIGNAL_SPECS = [
    {
        "signal_key": "valuation_forward_pe",
        "name": "估值阈值：NVDA Forward PE",
        "dimension": "valuation",
        "frequency": "weekly",
        "comparator": "lte",
        "threshold": 35.0,
        "metric_key": "NVDA_PE_FORWARD",
        "action_mapping": {"positive": "可以考虑分批加仓", "negative": "估值偏贵，谨慎追高"},
        "description": "低于 35x 视作估值更有吸引力。",
    },
    {
        "signal_key": "rates_real_yield",
        "name": "利率阈值：10Y 实际利率",
        "dimension": "rates",
        "frequency": "weekly",
        "comparator": "lte",
        "threshold": 2.0,
        "metric_key": "US10Y_REAL",
        "action_mapping": {"positive": "贴现压力可控", "negative": "高实际利率压制成长估值"},
        "description": "10Y 实际利率越低，对成长股越友好。",
    },
    {
        "signal_key": "policy_rate",
        "name": "资金成本：EFFR",
        "dimension": "liquidity",
        "frequency": "weekly",
        "comparator": "lte",
        "threshold": 5.25,
        "metric_key": "EFFR",
        "action_mapping": {"positive": "流动性边际压力减轻", "negative": "高资金成本环境"},
        "description": "资金价格越高，风险偏好越受限。",
    },
    {
        "signal_key": "earnings_momentum",
        "name": "盈利动能：NVDA 价格代理",
        "dimension": "earnings",
        "frequency": "weekly",
        "comparator": "gte",
        "threshold": 100.0,
        "metric_key": "NVDA_PRICE",
        "action_mapping": {"positive": "基本面与资金面可能同步", "negative": "回看订单与财报细节"},
        "description": "MVP 用价格代理盈利动能，后续可替换为营收/毛利/CapEx 数据。",
    },
    {
        "signal_key": "capex_confidence",
        "name": "供给扩张：总股本稳定代理",
        "dimension": "capex",
        "frequency": "weekly",
        "comparator": "gte",
        "threshold": 1.0,
        "metric_key": "NVDA_SHARES_OUT",
        "action_mapping": {"positive": "维持产业链跟踪", "negative": "回看供给与约束变量"},
        "description": "建议后续替换为 hyperscaler CapEx / HBM / CoWoS 数据。",
    },
    {
        "signal_key": "sentiment_risk_balance",
        "name": "情绪与风险平衡",
        "dimension": "risk",
        "frequency": "weekly",
        "comparator": "gte",
        "threshold": 0.0,
        "metric_key": "NVDA_PRICE",
        "action_mapping": {"positive": "维持跟踪，不追涨", "negative": "等待确认信号"},
        "description": "MVP 占位信号，用于保证 6 维结构完整。",
    },
]


def seed_signal_definitions() -> None:
    for spec in SIGNAL_SPECS:
        upsert_signal_definition(spec)


def _evaluate(comparator: str, value: float | None, threshold: float | None):
    if value is None or threshold is None:
        return "missing", "neutral", 0
    if comparator == "lte":
        matched = value <= threshold
    elif comparator == "gte":
        matched = value >= threshold
    else:
        matched = False
    if matched:
        return "triggered", "positive", 1
    return "triggered", "negative", -1


def score_signals(score_date: str | None = None) -> dict:
    seed_signal_definitions()
    score_date = score_date or date.today().isoformat()
    observations = latest_observation_map()
    details = []
    counter = Counter()
    breakdown = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

    for spec in SIGNAL_SPECS:
        observation = observations.get(spec["metric_key"])
        raw_value = observation.get("value") if observation else None
        status, direction, score = _evaluate(
            spec["comparator"], raw_value, spec["threshold"]
        )
        reasoning = spec["action_mapping"].get(direction, spec["description"])
        insert_signal_value(
            {
                "signal_key": spec["signal_key"],
                "observed_at": score_date,
                "raw_value": raw_value,
                "threshold": spec["threshold"],
                "status": status,
                "direction": direction,
                "score": score,
                "reasoning": reasoning,
                "metadata": {"dimension": spec["dimension"], "metric_key": spec["metric_key"]},
            }
        )
        breakdown[spec["dimension"]][direction] += 1
        counter[direction] += 1
        details.append(
            {
                "signal_key": spec["signal_key"],
                "name": spec["name"],
                "dimension": spec["dimension"],
                "raw_value": raw_value,
                "threshold": spec["threshold"],
                "direction": direction,
                "reasoning": reasoning,
            }
        )

    if counter["positive"] >= 4:
        action_suggestion = "正向信号较多：可做小步加仓草案"
    elif counter["negative"] >= 4:
        action_suggestion = "负向信号较多：以观望/减仓为主"
    else:
        action_suggestion = "信号分歧较大：维持跟踪与纪律"

    result = {
        "score_date": score_date,
        "positive_count": counter["positive"],
        "negative_count": counter["negative"],
        "neutral_count": counter["neutral"],
        "total_score": counter["positive"] - counter["negative"],
        "action_suggestion": action_suggestion,
        "dimension_breakdown": dict(breakdown),
        "details": details,
    }
    insert_signal_score(result)
    return result
