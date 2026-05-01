"""Multi-manifest documentation client.

Manages a registry of documentation manifest sources (e.g., ansible-core ai-docs),
fetches them via HTTP, caches per-source, and provides cross-source search.
"""

from __future__ import annotations

from typing import Any

import httpx

from ansible_knowledge.config import SEARCH_DOCS_LIMIT, get_doc_sources


_manifest_cache: dict[str, list[dict[str, Any]]] = {}


async def _fetch_manifest(source_name: str, url: str) -> list[dict[str, Any]]:
    """Fetch and cache a manifest from a URL."""
    if source_name in _manifest_cache:
        return _manifest_cache[source_name]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    entries = data if isinstance(data, list) else data.get("documents", data.get("entries", []))

    for entry in entries:
        entry["_source"] = source_name

    _manifest_cache[source_name] = entries
    return entries


async def search_docs(
    query: str,
    source: str | None = None,
    topic: str | None = None,
    audience: str | None = None,
    core_only: bool = False,
) -> list[dict[str, Any]]:
    """Search documentation manifests for conceptual guides.

    Args:
        query: Search term (matched against title, summary, topics).
        source: Filter to a single source name (e.g. "ansible-core").
        topic: Filter by topic tag.
        audience: Filter by audience tag.
        core_only: If True, only return entries marked as core.

    Returns:
        Up to SEARCH_DOCS_LIMIT matching entries with source info.
    """
    sources = get_doc_sources()
    query_lower = query.lower()
    results: list[dict[str, Any]] = []

    for src_name, src_config in sources.items():
        if source and src_name != source:
            continue

        try:
            entries = await _fetch_manifest(src_name, src_config["url"])
        except (httpx.HTTPError, KeyError):
            continue

        for entry in entries:
            if core_only and not entry.get("core", False):
                continue
            if topic:
                entry_topics = entry.get("topics", [])
                if isinstance(entry_topics, str):
                    entry_topics = [entry_topics]
                if topic.lower() not in [t.lower() for t in entry_topics]:
                    continue
            if audience:
                entry_audience = entry.get("audience", [])
                if isinstance(entry_audience, str):
                    entry_audience = [entry_audience]
                if audience.lower() not in [a.lower() for a in entry_audience]:
                    continue

            title = entry.get("title", "").lower()
            summary = entry.get("summary", "").lower()
            topics_str = " ".join(
                t.lower() for t in entry.get("topics", [])
                if isinstance(t, str)
            )
            searchable = f"{title} {summary} {topics_str}"

            if query_lower in searchable:
                result = {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "topic": entry.get("topics", []),
                    "audience": entry.get("audience", []),
                    "lines": entry.get("lines", 0),
                    "source": src_name,
                    "url": entry.get("url", ""),
                }
                results.append(result)

            if len(results) >= SEARCH_DOCS_LIMIT:
                break

    return results[:SEARCH_DOCS_LIMIT]


def clear_cache() -> None:
    """Clear the manifest cache (useful for testing)."""
    _manifest_cache.clear()
