"""Tests for ansible_knowledge.parser."""

from unittest.mock import patch

import pytest

from ansible_knowledge.parser import (
    AnsibleDocError,
    extract_examples,
    extract_module_metadata,
    extract_params,
    extract_short_description,
    get_module_doc,
    is_api_module,
    list_modules,
    search_modules,
)


class TestGetModuleDoc:
    def test_returns_parsed_json(self, sample_module_doc, sample_module_doc_json):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value=sample_module_doc_json):
            result = get_module_doc("ansible.builtin.package")
        assert result == sample_module_doc

    def test_raises_on_invalid_json(self):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value="not json"):
            with pytest.raises(AnsibleDocError, match="Failed to parse"):
                get_module_doc("ansible.builtin.package")


class TestListModules:
    def test_returns_all_modules(self, sample_module_list_json):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value=sample_module_list_json) as mock:
            result = list_modules()
        assert len(result) == 4
        mock.assert_called_once_with("--list", "--json")

    def test_passes_namespace(self, sample_module_list_json):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value=sample_module_list_json) as mock:
            list_modules(namespace="community.general")
        mock.assert_called_once_with("--list", "--json", "community.general")


class TestSearchModules:
    def test_filters_by_keyword_in_name(self, sample_module_list_json):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value=sample_module_list_json):
            result = search_modules("redis")
        assert "community.general.redis" in result
        assert len(result) == 1

    def test_filters_by_keyword_in_description(self, sample_module_list_json):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value=sample_module_list_json):
            result = search_modules("apt")
        assert "ansible.builtin.apt" in result
        assert "ansible.builtin.package" not in result

    def test_case_insensitive(self, sample_module_list_json):
        with patch("ansible_knowledge.parser._run_ansible_doc", return_value=sample_module_list_json):
            result = search_modules("REDIS")
        assert "community.general.redis" in result


class TestExtractParams:
    def test_extracts_all_params(self, sample_module_doc):
        params = extract_params(sample_module_doc)
        names = [p["name"] for p in params]
        assert "name" in names
        assert "state" in names
        assert "use" in names

    def test_required_params_first(self, sample_module_doc):
        params = extract_params(sample_module_doc)
        required_flags = [p["required"] for p in params]
        assert required_flags == [True, True, False]

    def test_param_fields(self, sample_module_doc):
        params = extract_params(sample_module_doc)
        state_param = next(p for p in params if p["name"] == "state")
        assert state_param["type"] == "str"
        assert state_param["required"] is True
        assert state_param["choices"] == ["present", "absent", "latest"]

    def test_default_values(self, sample_module_doc):
        params = extract_params(sample_module_doc)
        use_param = next(p for p in params if p["name"] == "use")
        assert use_param["default"] == "auto"
        assert use_param["required"] is False


class TestExtractExamples:
    def test_returns_example_yaml(self, sample_module_doc):
        examples = extract_examples(sample_module_doc)
        assert "Install ntpdate" in examples
        assert "state: present" in examples


class TestExtractShortDescription:
    def test_returns_description(self, sample_module_doc):
        desc = extract_short_description(sample_module_doc)
        assert desc == "Generic OS package manager"


class TestIsApiModule:
    def test_system_module_returns_false(self, sample_module_doc):
        assert is_api_module(sample_module_doc) is False

    def test_api_module_returns_true(self, sample_api_module_doc):
        assert is_api_module(sample_api_module_doc) is True


class TestExtractModuleMetadata:
    def test_returns_combined_metadata(self, sample_module_doc):
        meta = extract_module_metadata(sample_module_doc)
        assert meta["module_name"] == "ansible.builtin.package"
        assert meta["short_description"] == "Generic OS package manager"
        assert len(meta["params"]) == 3
        assert "ntpdate" in meta["examples"]
        assert meta["is_api_module"] is False

    def test_api_module_metadata(self, sample_api_module_doc):
        meta = extract_module_metadata(sample_api_module_doc)
        assert meta["is_api_module"] is True
