# CLAUDE.md

## Project

Ansible Knowledge MCP Server — module discovery, documentation search, and skill generation for AI agents via the Model Context Protocol.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Runtime requirement: `ansible-core` must be installed in the same environment (for `ansible-doc`).

## Architecture

```
src/ansible_knowledge/
├── server.py              # FastMCP server, 8 @tool functions (entrypoint)
├── parser.py              # ansible-doc wrapper — module discovery and metadata extraction
├── skills.py              # skill rendering + package writing (Jinja2)
├── config.py              # paths, constants, doc source registry
├── collection_manifest.py # collection-level MANIFEST.json generation/caching
├── docs.py                # multi-manifest documentation client (httpx)
└── templates/             # Jinja2 templates for skill packages
```

## MCP Tools

| Tool | Type | Description |
|------|------|-------------|
| `search_modules` | read-only | Find modules by keyword |
| `get_module_doc` | read-only | Get full module documentation |
| `search_docs` | read-only | Search conceptual doc manifests |
| `get_collection_manifest` | read-only | Get collection-level module summary |
| `list_skills` | read-only | List generated skills |
| `get_skill` | read-only | Read a skill's content |
| `generate_skill` | write | Generate a skill package for one module |
| `generate_collection_skills` | write | Batch generate skills for a collection |

## Key Patterns

- All `parser.py` functions call `subprocess.run()`. The server wraps them via `asyncio.run_in_executor()`.
- Tool functions use lazy imports for `parser` and `skills` to avoid importing ansible-core at startup.
- `docs.py` fetches manifests via httpx, caches per-source in a dict.
- Tests mock `_run_ansible_doc` — no real `ansible-doc` needed.

## Testing

```bash
pytest tests/ -v
```

All tests use `unittest.mock.patch` to mock `_run_ansible_doc`. No ansible-core installation is needed to run the test suite.

## Registration

Development (from project root):
```bash
claude mcp add ansible-knowledge -- uv run --directory . ansible-knowledge-mcp
```

Global (after pip install):
```bash
claude mcp add ansible-knowledge -- ansible-knowledge-mcp
```
