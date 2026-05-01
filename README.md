# Ansible Knowledge MCP Server

Module discovery, documentation search, and skill generation for AI agents via the Model Context Protocol.

## What It Does

The Ansible Knowledge MCP Server is the foundational "learn" layer for AI agents working with Ansible. It provides:

- **Module discovery** — search and explore Ansible modules across all installed collections
- **Module documentation** — get structured parameter specs, examples, and metadata
- **Documentation search** — find conceptual guides from Ansible's AI-friendly docs
- **Skill generation** — create ready-to-use skill packages that teach agents how to use specific modules
- **Collection manifests** — get collection-level overviews with per-module summaries

Together with [Ansible Devtools MCP](https://github.com/ansible/ansible-dev-tools) (build) and [AAP MCP](https://github.com/ansible/aap-mcp-server) (deploy), this enables the full autonomous cycle: **learn -> build -> deploy**.

```
 Agent's MCP servers:

 +-----------------------+  +-------------------+  +---------------+
 | Ansible Knowledge     |  | Ansible Devtools  |  |   AAP MCP     |
 | (this project)        |  |                   |  |               |
 |                       |  |                   |  |               |
 | search_modules        |  | ansible_lint      |  | controller.*  |
 | get_module_doc        |  | ansible_navigator |  | eda.*         |
 | get_collection_       |  | ansible_create_*  |  | gateway.*     |
 |   manifest            |  | build_ee          |  | galaxy.*      |
 | search_docs           |  | zen_of_ansible    |  |               |
 | generate_skill        |  | setup_environment |  |               |
 | generate_collection   |  | environment_info  |  |               |
 | list_skills           |  |                   |  |               |
 | get_skill             |  |                   |  |               |
 |                       |  |                   |  |               |
 | LEARN                 |  | BUILD             |  | DEPLOY        |
 +-----------------------+  +-------------------+  +---------------+
```

## Installation

```bash
pip install ansible-knowledge-mcp
```

Runtime requirement: `ansible-core` must be installed (for `ansible-doc`).

## Usage

### With Claude Code

```bash
claude mcp add ansible-knowledge -- ansible-knowledge-mcp
```

### With VS Code / Cursor

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "ansible-knowledge": {
      "command": "ansible-knowledge-mcp",
      "type": "stdio"
    }
  }
}
```

### With any MCP client

The server runs over stdio by default:

```bash
ansible-knowledge-mcp
```

### Full stack configuration

```json
{
  "mcpServers": {
    "ansible-knowledge": { "command": "ansible-knowledge-mcp" },
    "ansible-devtools":  { "command": "ade", "args": ["mcp"] },
    "aap":               { "command": "aap-mcp-server" }
  }
}
```

## Tools

### Discovery (read-only)

| Tool | Description |
|------|-------------|
| `search_modules(keyword, namespace?)` | Find modules by keyword in name or description. Returns up to 50 matches. |
| `get_module_doc(module_name)` | Get full structured docs: params, examples, API detection. |
| `search_docs(query, source?, topic?, audience?, core_only?)` | Search documentation manifests for conceptual guides. Returns up to 20 matches. |
| `get_collection_manifest(collection_namespace)` | Get collection-level manifest with per-module summaries. |

### Skill management

| Tool | Description |
|------|-------------|
| `list_skills()` | List all generated skills (read-only). |
| `get_skill(skill_name)` | Read a skill's SKILL.md content (read-only). |
| `generate_skill(module_name, install_to?)` | Generate a skill package for one module. Returns SKILL.md inline. |
| `generate_collection_skills(collection_namespace, install_to?)` | Batch generate skills for an entire collection. |

## Development

```bash
git clone <repo-url>
cd ansible-knowledge-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `ANSIBLE_KNOWLEDGE_SKILLS_DIR` | Where to write generated skills | `./skills/` |
| `ANSIBLE_KNOWLEDGE_DOC_SOURCES` | JSON dict of doc manifest sources | Built-in ansible-core source |

## License

Apache-2.0
