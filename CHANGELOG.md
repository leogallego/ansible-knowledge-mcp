# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-05-07

### Added

- 8 MCP tools: `search_modules`, `get_module_doc`, `search_docs`, `get_collection_manifest`, `list_skills`, `get_skill`, `generate_skill`, `generate_collection_skills`
- 3 MCP resources: `skills://list`, `skills://{skill_name}`, `docs://sources`
- 3 MCP prompts: `review_playbook`, `explain_module`, `generate_role`
- Documentation search via AI-friendly manifest from ansible-documentation
- Skill package generation with SKILL.md, scripts, and playbooks via Jinja2 templates
- Collection manifest generation with per-module summaries and tagging
- OWASP security hardening: FQCN input validation, path traversal protection, error sanitization, output size limits, audit logging
- 77 tests covering tools, parser, skills, docs, collection manifests, and security

[0.1.0]: https://github.com/leogallego/ansible-know-mcp/releases/tag/v0.1.0
