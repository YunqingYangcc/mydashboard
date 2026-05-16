from kb.config import EXPORT_DIR
from kb.storage import latest_signal_score, list_actions, list_reviews, list_tasks
from kb.utils import now_iso


def build_weekly_review_template() -> str:
    score = latest_signal_score() or {}
    tasks = list_tasks(limit=10)
    actions = list_actions(limit=10)
    reviews = list_reviews(limit=5)

    lines = [
        "# 本周认知操作系统复盘模板",
        "",
        f"生成时间：{now_iso()}",
        "",
        "## 1. 本周信号概览",
        f"- 正向信号：{score.get('positive_count', 0)}",
        f"- 负向信号：{score.get('negative_count', 0)}",
        f"- 建议动作：{score.get('action_suggestion', '待生成')}",
        "",
        "## 2. 本周执行任务",
    ]
    for task in tasks:
        lines.append(f"- [{task['status']}] {task['title']}")

    lines.extend(["", "## 3. 本周操作记录"])
    for action in actions:
        lines.append(
            f"- {action['action_time']} | {action['asset']} | {action['action_type']} | {action.get('risk_control') or ''}"
        )

    lines.extend(["", "## 4. 上次复盘回看"])
    for review in reviews:
        lines.append(f"- {review['review_period']} | {review.get('summary') or ''}")

    lines.extend(
        [
            "",
            "## 5. 本周输入",
            "- 重要文档：",
            "- 关键事实：",
            "- 反直觉信息：",
            "",
            "## 6. 本周输出",
            "- 新断言：",
            "- 新关系：",
            "- 新任务：",
            "",
            "## 7. 下周聚焦",
            "- P1：",
            "- P2：",
            "- P3：",
            "- P4：",
        ]
    )
    return "\n".join(lines)


def export_weekly_review_template():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"weekly_review_{now_iso().split('T')[0]}.md"
    path.write_text(build_weekly_review_template(), encoding="utf-8")
    return path
