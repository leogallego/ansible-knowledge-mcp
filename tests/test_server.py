"""Tests for ansible_knowledge.server MCP tools."""

import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from ansible_knowledge.server import mcp
from tests.conftest import SAMPLE_MODULE_DOC, SAMPLE_MODULE_LIST, SAMPLE_API_MODULE_DOC


@pytest.fixture
def mock_ansible_doc():
    with patch("ansible_knowledge.parser._run_ansible_doc") as mock:
        yield mock


@pytest.fixture
def mock_doc_fetch():
    """Mock httpx for docs search tests."""
    mock_manifest = [
        {
            "title": "Playbook Guide",
            "summary": "How to write playbooks",
            "topics": ["playbooks"],
            "audience": ["beginner"],
            "core": True,
            "lines": 100,
            "url": "https://example.com/playbook.md",
        }
    ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_manifest
    mock_resp.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("ansible_knowledge.docs.httpx.AsyncClient", return_value=mock_client):
        from ansible_knowledge.docs import clear_cache
        clear_cache()
        yield
        clear_cache()


class TestSearchModulesTool:
    @pytest.mark.asyncio
    async def test_search_modules(self, mock_ansible_doc):
        mock_ansible_doc.return_value = json.dumps(SAMPLE_MODULE_LIST)
        from ansible_knowledge.server import search_modules
        result = await search_modules("redis")
        assert "community.general.redis" in result
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_with_namespace(self, mock_ansible_doc):
        mock_ansible_doc.return_value = json.dumps(SAMPLE_MODULE_LIST)
        from ansible_knowledge.server import search_modules
        result = await search_modules("package", namespace="ansible.builtin")
        assert "ansible.builtin.package" in result


class TestGetModuleDocTool:
    @pytest.mark.asyncio
    async def test_get_module_doc(self, mock_ansible_doc):
        mock_ansible_doc.return_value = json.dumps(SAMPLE_MODULE_DOC)
        from ansible_knowledge.server import get_module_doc
        result = await get_module_doc("ansible.builtin.package")
        assert result["module_name"] == "ansible.builtin.package"
        assert result["short_description"] == "Generic OS package manager"
        assert len(result["params"]) == 3
        assert result["is_api_module"] is False


class TestSearchDocsTool:
    @pytest.mark.asyncio
    async def test_search_docs(self, mock_doc_fetch):
        from ansible_knowledge.server import search_docs
        results = await search_docs("playbook")
        assert len(results) == 1
        assert results[0]["title"] == "Playbook Guide"


class TestGetCollectionManifestTool:
    @pytest.mark.asyncio
    async def test_returns_error_for_empty_collection(self, mock_ansible_doc):
        mock_ansible_doc.return_value = json.dumps({})
        from ansible_knowledge.server import get_collection_manifest
        result = await get_collection_manifest("nonexistent.collection")
        assert "error" in result


class TestListSkillsTool:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_skills(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ansible_knowledge.config.SKILLS_DIR", tmp_path)
        from ansible_knowledge.server import list_skills
        result = await list_skills()
        assert result == []


class TestGetSkillTool:
    @pytest.mark.asyncio
    async def test_returns_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ansible_knowledge.config.SKILLS_DIR", tmp_path)
        from ansible_knowledge.server import get_skill
        result = await get_skill("nonexistent")
        assert "not found" in result.lower()


class TestGenerateSkillTool:
    @pytest.mark.asyncio
    async def test_generates_skill(self, tmp_path, mock_ansible_doc, monkeypatch):
        mock_ansible_doc.return_value = json.dumps(SAMPLE_MODULE_DOC)
        monkeypatch.setattr("ansible_knowledge.config.SKILLS_DIR", tmp_path)
        from ansible_knowledge.server import generate_skill
        result = await generate_skill("ansible.builtin.package")
        assert "ansible.builtin.package" in result
        assert (tmp_path / "ansible.builtin.package" / "SKILL.md").exists()


class TestGenerateCollectionSkillsTool:
    @pytest.mark.asyncio
    async def test_generates_collection_skills(self, tmp_path, mock_ansible_doc, monkeypatch):
        mock_ansible_doc.side_effect = [
            json.dumps(SAMPLE_MODULE_LIST),
            json.dumps(SAMPLE_MODULE_DOC),
            json.dumps(SAMPLE_MODULE_DOC),
            json.dumps(SAMPLE_MODULE_DOC),
            json.dumps(SAMPLE_MODULE_DOC),
        ]
        monkeypatch.setattr("ansible_knowledge.config.SKILLS_DIR", tmp_path)
        from ansible_knowledge.server import generate_collection_skills
        result = await generate_collection_skills("ansible.builtin", install_to=str(tmp_path))
        assert result["total"] == 4
        assert result["succeeded"] + result["failed"] == 4
