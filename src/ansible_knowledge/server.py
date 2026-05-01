"""Ansible Knowledge MCP Server.

Provides 8 tools for module discovery, documentation search,
and skill generation via the Model Context Protocol.
"""

from __future__ import annotations

import asyncio
import json
from functools import partial
from typing import Annotated, Any

from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

mcp = FastMCP(
    name="Ansible Knowledge",
    instructions=(
        "Ansible module discovery, documentation, and skill generation. "
        "Use search_modules to find modules, get_module_doc for details, "
        "search_docs for conceptual guides, and generate_skill to create "
        "ready-to-use skill packages."
    ),
)


def _run_in_executor(func, *args, **kwargs):
    """Run a blocking function in the default executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, partial(func, *args, **kwargs))


# --- Discovery tools (read-only) ---


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def search_modules(
    keyword: Annotated[str, "Search term to match against module names and descriptions"],
    namespace: Annotated[str | None, "Optional collection namespace filter (e.g. 'community.docker')"] = None,
) -> dict[str, str]:
    """Find Ansible modules by keyword in name or description. Returns up to 50 matches as {fqcn: short_description}."""
    from ansible_knowledge import parser
    from ansible_knowledge.config import SEARCH_MODULES_LIMIT

    results = await _run_in_executor(parser.search_modules, keyword, namespace)
    if len(results) > SEARCH_MODULES_LIMIT:
        results = dict(list(results.items())[:SEARCH_MODULES_LIMIT])
    return results


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_module_doc(
    module_name: Annotated[str, "Fully-qualified collection name (e.g. 'ansible.builtin.copy')"],
) -> dict[str, Any]:
    """Get full structured documentation for one module.

    Returns: module_name, short_description, params (list with name/type/required/default/choices/description/aliases),
    examples (raw YAML), is_api_module.
    """
    from ansible_knowledge import parser

    raw_doc = await _run_in_executor(parser.get_module_doc, module_name)
    metadata = parser.extract_module_metadata(raw_doc)
    return metadata


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def search_docs(
    query: Annotated[str, "Search term to match against documentation titles, summaries, and topics"],
    source: Annotated[str | None, "Filter to a single source (e.g. 'ansible-core')"] = None,
    topic: Annotated[str | None, "Filter by topic tag"] = None,
    audience: Annotated[str | None, "Filter by audience tag"] = None,
    core_only: Annotated[bool, "If true, only return entries marked as core"] = False,
) -> list[dict[str, Any]]:
    """Search documentation manifests for conceptual guides.

    Returns up to 20 matching entries with title, summary, topic, audience, lines, source, and raw URL.
    """
    from ansible_knowledge import docs

    return await docs.search_docs(
        query=query, source=source, topic=topic, audience=audience, core_only=core_only,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_collection_manifest(
    collection_namespace: Annotated[str, "Collection namespace (e.g. 'netbox.netbox')"],
) -> dict[str, Any]:
    """Get collection-level manifest with per-module summaries.

    Returns cached MANIFEST.json if available, otherwise generates on-demand
    (metadata extraction only, no skill generation).
    """
    from ansible_knowledge import parser, collection_manifest

    cached = collection_manifest.load_cached_manifest(collection_namespace)
    if cached:
        return cached

    modules = await _run_in_executor(parser.search_modules, "", collection_namespace)
    if not modules:
        return {"error": f"No modules found in collection '{collection_namespace}'"}

    metadata_list = []
    for module_name in sorted(modules):
        try:
            raw_doc = await _run_in_executor(parser.get_module_doc, module_name)
            metadata_list.append(parser.extract_module_metadata(raw_doc))
        except parser.AnsibleDocError:
            continue

    return collection_manifest.generate_manifest(collection_namespace, metadata_list)


# --- Skill management tools ---


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_skills() -> list[dict[str, str]]:
    """List all available generated skills. Returns name, description, path for each."""
    from ansible_knowledge.config import SKILLS_DIR

    results = []
    if not SKILLS_DIR.exists():
        return results

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text()
            description = ""
            for line in content.splitlines():
                if line.startswith("description:"):
                    description = line.partition(":")[2].strip().strip(">-").strip()
                    break
            results.append({
                "name": skill_dir.name,
                "description": description,
                "path": str(skill_dir),
            })

    return results


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_skill(
    skill_name: Annotated[str, "Skill name (usually the module FQCN)"],
) -> str:
    """Read a specific skill's SKILL.md content by name."""
    from ansible_knowledge.config import SKILLS_DIR

    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return f"Skill '{skill_name}' not found."
    return skill_path.read_text()


@mcp.tool
async def generate_skill(
    module_name: Annotated[str, "Fully-qualified module name (e.g. 'ansible.builtin.copy')"],
    install_to: Annotated[str | None, "Optional absolute path to install the skill to"] = None,
    ctx: Context = None,
) -> str:
    """Generate a skill package for one module.

    Writes SKILL.md + scripts + playbook to disk.
    Returns the SKILL.md content inline so the agent can use it immediately.
    """
    from ansible_knowledge import parser, skills
    from ansible_knowledge.config import SKILLS_DIR

    if ctx:
        await ctx.report_progress(progress=0, total=100)

    raw_doc = await _run_in_executor(parser.get_module_doc, module_name)
    metadata = parser.extract_module_metadata(raw_doc)

    if ctx:
        await ctx.report_progress(progress=50, total=100)

    skill_name = skills._module_to_skill_name(metadata["module_name"])
    from pathlib import Path
    output_dir = Path(install_to) / skill_name if install_to else SKILLS_DIR / skill_name

    await _run_in_executor(skills.write_skill_package, output_dir, metadata)

    if ctx:
        await ctx.report_progress(progress=100, total=100)

    return skills.render_skill(metadata)


@mcp.tool
async def generate_collection_skills(
    collection_namespace: Annotated[str, "Collection namespace (e.g. 'netbox.netbox')"],
    install_to: Annotated[str | None, "Optional absolute path to install skills to"] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Batch generate skills for an entire collection.

    Generates/updates the collection MANIFEST.json as a byproduct.
    Returns summary (succeeded/failed counts) + manifest content.
    """
    from ansible_knowledge import parser, skills, collection_manifest
    from ansible_knowledge.config import SKILLS_DIR
    from pathlib import Path

    modules = await _run_in_executor(parser.search_modules, "", collection_namespace)
    if not modules:
        return {"error": f"No modules found in collection '{collection_namespace}'"}

    total = len(modules)
    succeeded = 0
    failed = 0
    metadata_list = []

    base_dir = Path(install_to) if install_to else SKILLS_DIR

    for i, module_name in enumerate(sorted(modules)):
        if ctx:
            await ctx.report_progress(progress=i, total=total)
        try:
            raw_doc = await _run_in_executor(parser.get_module_doc, module_name)
            metadata = parser.extract_module_metadata(raw_doc)
            metadata_list.append(metadata)

            skill_name = skills._module_to_skill_name(metadata["module_name"])
            output_dir = base_dir / skill_name
            await _run_in_executor(skills.write_skill_package, output_dir, metadata)
            succeeded += 1
        except Exception:
            failed += 1

    manifest = collection_manifest.generate_manifest(
        collection_namespace, metadata_list, skills_dir=base_dir,
    )

    if ctx:
        await ctx.report_progress(progress=total, total=total)

    return {
        "succeeded": succeeded,
        "failed": failed,
        "total": total,
        "manifest": manifest,
    }


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
