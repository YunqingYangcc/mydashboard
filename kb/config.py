import os
from pathlib import Path

import pytz
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")

# 多数据库配置（按业务分库）
DATABASE_KNOWLEDGE = ROOT_DIR / os.getenv("DATABASE_KNOWLEDGE", "data/知识库.db")
DATABASE_CLAIMS = ROOT_DIR / os.getenv("DATABASE_CLAIMS", "data/认知闭环.db")
DATABASE_REVIEW = ROOT_DIR / os.getenv("DATABASE_REVIEW", "data/复盘.db")
# 保留旧路径兼容
DATABASE_PATH = ROOT_DIR / os.getenv("DATABASE_PATH", "data/cognitive_os.db")

LOG_DIR = ROOT_DIR / os.getenv("LOG_DIR", "logs")
INBOX_DIR = ROOT_DIR / os.getenv("INBOX_DIR", "data/inbox")
EXPORT_DIR = ROOT_DIR / os.getenv("EXPORT_DIR", "data/exports")
RSS_URLS = [item.strip() for item in os.getenv("RSS_URLS", "").split(",") if item.strip()]

FRED_API_KEY = os.getenv("FRED_API_KEY")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "personal-cognitive-os research@example.com")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

XIAOMI_BASE_URL = os.getenv("XIAOMI_BASE_URL")
XIAOMI_API_KEY = os.getenv("XIAOMI_API_KEY")

# ===== Gold AI 配置 =====
GOLD_AI_API_KEY = os.getenv("GOLD_AI_API_KEY", "")
GOLD_AI_BASE_URL = os.getenv("GOLD_AI_BASE_URL", "https://api.siliconflow.cn/v1")
GOLD_AI_MODEL = os.getenv("GOLD_AI_MODEL", "deepseek-ai/DeepSeek-V4-Flash")

# ===== 智谱 Gold AI 配置 =====
ZHIPU_GOLD_AI_API_KEY = os.getenv("ZHIPU_GOLD_AI_API_KEY", "")
ZHIPU_GOLD_AI_BASE_URL = os.getenv("ZHIPU_GOLD_AI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
ZHIPU_GOLD_AI_MODEL = os.getenv("ZHIPU_GOLD_AI_MODEL", "glm-4-plus")

# ===== 小米 MiMo Gold AI 配置 =====
XIAOMI_GOLD_AI_API_KEY = os.getenv("XIAOMI_GOLD_AI_API_KEY", "")
XIAOMI_GOLD_AI_BASE_URL = os.getenv("XIAOMI_GOLD_AI_BASE_URL", "https://api.xiaomimimo.com/v1")
XIAOMI_GOLD_AI_MODEL = os.getenv("XIAOMI_GOLD_AI_MODEL", "mimo-v2.5-pro")

MODEL_RESEARCHER_A = os.getenv("MODEL_RESEARCHER_A", "glm-4-flash")
MODEL_RESEARCHER_B = os.getenv("MODEL_RESEARCHER_B", "mimo-7b-chat")
MODEL_DIRECTOR = os.getenv("MODEL_DIRECTOR", "deepseek-v3")


def ensure_directories() -> None:
    for path in [DATABASE_KNOWLEDGE.parent, DATABASE_CLAIMS.parent, DATABASE_REVIEW.parent, LOG_DIR, INBOX_DIR, EXPORT_DIR]:
        Path(path).mkdir(parents=True, exist_ok=True)


def timezone():
    return pytz.timezone(TIMEZONE)
