from typing import Any


def build_document_key(payload: dict[str, Any]) -> str:
    source_type = payload.get("source_type", "").strip() or "unknown"
    metadata = payload.get("metadata", {}) or {}

    if source_type == "folder":
        stable_path = metadata.get("absolute_path") or metadata.get("path")
        if stable_path:
            return f"folder::{stable_path}"

    if source_type == "rss":
        url = payload.get("url")
        if url:
            return f"rss::{url}"
        feed_url = metadata.get("feed_url")
        title = payload.get("title", "").strip()
        return f"rss::{feed_url}::{title}"

    url = payload.get("url")
    if url:
        return f"{source_type}::{url}"

    title = payload.get("title", "").strip() or "untitled"
    source_name = payload.get("source_name", "").strip() or "unknown"
    return f"{source_type}::{source_name}::{title}"
