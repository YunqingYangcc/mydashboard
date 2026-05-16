from datetime import datetime
from pathlib import Path
from time import sleep

import feedparser
import requests
from pypdf import PdfReader

from kb.constants import RENDER_MODE_IMAGE, RENDER_MODE_MARKDOWN, RENDER_MODE_TEXT
from kb.config import (
    ALPHAVANTAGE_API_KEY,
    FMP_API_KEY,
    FRED_API_KEY,
    INBOX_DIR,
    RSS_URLS,
    SEC_USER_AGENT,
)
from kb.logger import logger
from kb.markdown_extract import extract_from_markdown
from kb.services import persist_document_with_extract
from kb.storage import (
    finish_run,
    init_db,
    insert_observation,
    insert_run,
)
from kb.utils import normalize_text


REQUEST_TIMEOUT = 20
SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".html", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def ingest_rss() -> list[dict]:
    documents = []
    for url in RSS_URLS:
        logger.info("Fetching RSS: %s", url)
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            content_parts = []
            if getattr(entry, "summary", None):
                content_parts.append(normalize_text(entry.summary))
            if getattr(entry, "content", None):
                for item in entry.content:
                    if item.get("value"):
                        content_parts.append(normalize_text(item["value"]))
            published = None
            if getattr(entry, "published_parsed", None):
                published = datetime(*entry.published_parsed[:6]).isoformat()
            documents.append(
                {
                    "source_type": "rss",
                    "source_name": feed.feed.get("title", url),
                    "title": normalize_text(getattr(entry, "title", "Untitled RSS Entry"))
                    or "Untitled RSS Entry",
                    "content": "\n\n".join(content_parts)[:20000],
                    "summary": normalize_text(getattr(entry, "summary", ""))[:500],
                    "author": normalize_text(getattr(entry, "author", "")) or None,
                    "url": getattr(entry, "link", None),
                    "doc_date": published,
                    "tags": ["rss"],
                    "metadata": {"feed_url": url},
                }
            )
    return documents


def _read_file(path: Path) -> str:
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return f"[image] {path.name}"
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return normalize_text("\n".join(page.extract_text() or "" for page in reader.pages))
    return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))


def ingest_folder() -> list[dict]:
    documents = []
    if not INBOX_DIR.exists():
        return documents
    for path in sorted(INBOX_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        content = _read_file(path)
        if not content:
            continue
        documents.append(
            {
                "source_type": "folder",
                "source_name": path.parent.name or "inbox",
                "title": path.stem,
                "content": content[:50000],
                "summary": content[:500],
                "doc_date": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                "tags": ["folder", path.suffix.lower().lstrip(".")],
                "metadata": {
                    "path": str(path.relative_to(INBOX_DIR.parent)),
                    "absolute_path": str(path),
                    "file_ext": path.suffix.lower(),
                    "render_mode": (
                        RENDER_MODE_MARKDOWN
                        if path.suffix.lower() == ".md"
                        else RENDER_MODE_IMAGE
                        if path.suffix.lower() in IMAGE_EXTENSIONS
                        else RENDER_MODE_TEXT
                    ),
                },
            }
        )
    return documents


def _json_get(url: str, params=None, headers=None):
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Request failed (%s/3): %s", attempt + 1, exc)
            if attempt < 2:
                sleep(1.5 * (attempt + 1))
    raise last_error


def ingest_api() -> list[dict]:
    observations = []

    if FRED_API_KEY:
        for metric_key, metric_name, series_id in [
            ("US10Y_REAL", "美国10年期实际利率", "DFII10"),
            ("EFFR", "有效联邦基金利率", "EFFR"),
        ]:
            try:
                payload = _json_get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": series_id,
                        "api_key": FRED_API_KEY,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 1,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("FRED ingest skipped for %s: %s", series_id, exc)
                continue
            items = payload.get("observations", [])
            if items and items[-1].get("value") not in {".", "", None}:
                latest = items[-1]
                observations.append(
                    {
                        "metric_key": metric_key,
                        "metric_name": metric_name,
                        "value": float(latest["value"]),
                        "unit": "pct",
                        "observed_at": f"{latest['date']}T00:00:00",
                        "frequency": "daily",
                        "source": "fred",
                    }
                )

    if ALPHAVANTAGE_API_KEY:
        try:
            payload = _json_get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": "NVDA",
                    "apikey": ALPHAVANTAGE_API_KEY,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("AlphaVantage ingest skipped: %s", exc)
            payload = {}
        quote = payload.get("Global Quote", {})
        if quote.get("05. price"):
            observations.append(
                {
                    "metric_key": "NVDA_PRICE",
                    "metric_name": "NVDA 价格",
                    "value": float(quote["05. price"]),
                    "unit": "USD",
                    "observed_at": f"{quote['07. latest trading day']}T00:00:00",
                    "frequency": "daily",
                    "source": "alphavantage",
                    "asset": "NVDA",
                }
            )

    if FMP_API_KEY:
        try:
            payload = _json_get(
                "https://financialmodelingprep.com/api/v3/quote/NVDA",
                params={"apikey": FMP_API_KEY},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("FMP ingest skipped: %s", exc)
            payload = []
        if payload and payload[0].get("pe") is not None:
            observations.append(
                {
                    "metric_key": "NVDA_PE_FORWARD",
                    "metric_name": "NVDA Forward PE",
                    "value": float(payload[0]["pe"]),
                    "unit": "x",
                    "observed_at": datetime.utcfromtimestamp(payload[0]["timestamp"]).isoformat(),
                    "frequency": "daily",
                    "source": "fmp",
                    "asset": "NVDA",
                }
            )

    try:
        sec_payload = _json_get(
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
            headers={"User-Agent": SEC_USER_AGENT},
        )
        shares = (
            sec_payload.get("facts", {})
            .get("us-gaap", {})
            .get("CommonStockSharesOutstanding", {})
            .get("units", {})
            .get("shares", [])
        )
        if shares:
            latest = sorted(shares, key=lambda item: item.get("end", ""))[-1]
            observations.append(
                {
                    "metric_key": "NVDA_SHARES_OUT",
                    "metric_name": "NVDA 总股本",
                    "value": float(latest["val"]),
                    "unit": "shares",
                    "observed_at": f"{latest['end']}T00:00:00",
                    "frequency": "quarterly",
                    "source": "sec",
                    "asset": "NVDA",
                }
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SEC ingest skipped: %s", exc)

    return observations


def run_ingest_all() -> dict:
    init_db()
    run_id = f"ingest_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    insert_run(run_id, "ingest", "running")
    try:
        documents = ingest_rss() + ingest_folder()
        observations = ingest_api()
        extracted_counts = {"claims": 0, "relations": 0, "tasks": 0}
        for document in documents:
            _, counters = persist_document_with_extract(document, extract_from_markdown)
            for key, value in counters.items():
                extracted_counts[key] += value
        for observation in observations:
            insert_observation(observation)
        summary = {
            "documents": len(documents),
            "observations": len(observations),
            "markdown_extract": extracted_counts,
        }
        finish_run(run_id, "completed", summary)
        return summary
    except Exception as exc:  # noqa: BLE001
        finish_run(run_id, "failed", {"error": str(exc)})
        raise
