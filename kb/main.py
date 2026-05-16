import argparse

from kb.ai import run_multi_role_workflow
from kb.config import INBOX_DIR, ensure_directories
from kb.ingest import run_ingest_all
from kb.logger import logger
from kb.reports import export_weekly_review_template
from kb.storage import (
    init_db,
    insert_task,
)


def generate_weekly_plan() -> None:
    insert_task(
        {
            "plan_key": "P1",
            "title": "复核本周行动建议草案",
            "description": "结合 6 维评分确认加仓/减仓/观望",
            "cadence": "weekly",
            "priority": "high",
            "source": "system",
        }
    )
    insert_task(
        {
            "plan_key": "P2",
            "title": "更新周期断言卡片",
            "description": "补 1 条 supports/contradicts 证据",
            "cadence": "weekly",
            "priority": "medium",
            "source": "system",
        }
    )


def build_parser():
    parser = argparse.ArgumentParser(description="本地个人认知操作系统")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    sub.add_parser("ingest-all")
    sub.add_parser("run-ai")
    sub.add_parser("weekly-review-template")
    sub.add_parser("weekly-plan")
    return parser


def main() -> None:
    ensure_directories()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        logger.info("Database initialized")
    elif args.command == "ingest-all":
        logger.info(run_ingest_all())
    elif args.command == "run-ai":
        logger.info(run_multi_role_workflow())
    elif args.command == "weekly-review-template":
        logger.info("Exported to %s", export_weekly_review_template())
    elif args.command == "weekly-plan":
        generate_weekly_plan()
        logger.info("Weekly plan generated")


if __name__ == "__main__":
    main()
