from abc import ABC
from typing import Any

import pytest
from packages.domain.models.enums import RiskLevel
from packages.tools.base import Tool


class DummyTool(Tool):
    def get_identifier(self) -> str:
        return "dummy_tool"

    def get_name(self) -> str:
        return "Dummy Tool"

    def get_description(self) -> str:
        return "A dummy tool for testing"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object"}

    def get_output_schema(self) -> dict[str, Any]:
        return {"type": "object"}

    def get_risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def is_read_only(self) -> bool:
        return True

    def get_required_permissions(self) -> list[str]:
        return []

    def get_resource_mode(self) -> str:
        return "real"

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        return {}


class TestToolContract:
    def test_tool_is_abstract(self):
        assert issubclass(Tool, ABC)

    def test_tool_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Tool()

    def test_tool_has_get_identifier(self):
        assert hasattr(Tool, "get_identifier")

    def test_tool_has_get_name(self):
        assert hasattr(Tool, "get_name")

    def test_tool_has_get_description(self):
        assert hasattr(Tool, "get_description")

    def test_tool_has_get_input_schema(self):
        assert hasattr(Tool, "get_input_schema")

    def test_tool_has_get_output_schema(self):
        assert hasattr(Tool, "get_output_schema")

    def test_tool_has_get_risk_level(self):
        assert hasattr(Tool, "get_risk_level")

    def test_tool_has_is_read_only(self):
        assert hasattr(Tool, "is_read_only")

    def test_tool_has_get_required_permissions(self):
        assert hasattr(Tool, "get_required_permissions")

    def test_all_abstract_methods_are_implemented(self):
        tool = DummyTool()
        assert tool is not None

    def test_get_identifier_returns_string(self):
        tool = DummyTool()
        assert isinstance(tool.get_identifier(), str)
        assert tool.get_identifier() == "dummy_tool"

    def test_get_name_returns_string(self):
        tool = DummyTool()
        assert isinstance(tool.get_name(), str)

    def test_get_description_returns_string(self):
        tool = DummyTool()
        assert isinstance(tool.get_description(), str)

    def test_get_input_schema_returns_dict(self):
        tool = DummyTool()
        assert isinstance(tool.get_input_schema(), dict)

    def test_get_output_schema_returns_dict(self):
        tool = DummyTool()
        assert isinstance(tool.get_output_schema(), dict)

    def test_get_risk_level_returns_risk_level(self):
        tool = DummyTool()
        assert isinstance(tool.get_risk_level(), RiskLevel)

    def test_is_read_only_returns_bool(self):
        tool = DummyTool()
        assert isinstance(tool.is_read_only(), bool)

    def test_get_required_permissions_returns_list(self):
        tool = DummyTool()
        assert isinstance(tool.get_required_permissions(), list)


class TestToolReadOnlyContract:
    @pytest.mark.parametrize("readonly", [True, False])
    def test_tool_can_be_read_only_or_not(self, readonly):
        class ConfigurableTool(Tool):
            def get_identifier(self):
                return "configurable"

            def get_name(self):
                return "Configurable"

            def get_description(self):
                return "Test"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            def get_risk_level(self):
                return RiskLevel.MEDIUM

            def is_read_only(self):
                return readonly

            def get_required_permissions(self):
                return []

            def get_resource_mode(self):
                return "real"

            async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
                return {}

        tool = ConfigurableTool()
        assert tool.is_read_only() == readonly


class TestToolRiskLevelContract:
    def test_tool_risk_levels(self):
        for level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:

            class TestTool(Tool):
                def get_identifier(self):
                    return "test"

                def get_name(self):
                    return "Test"

                def get_description(self):
                    return "Test"

                def get_input_schema(self):
                    return {}

                def get_output_schema(self):
                    return {}

                def get_risk_level(self, _level=level):
                    return _level

                def is_read_only(self):
                    return True

                def get_required_permissions(self):
                    return []

                def get_resource_mode(self):
                    return "real"

                async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
                    return {}

            tool = TestTool()
            assert tool.get_risk_level() == level


class TestToolIdentifiers:
    def test_tools_have_stable_identifiers(self):
        class MyTool(Tool):
            def get_identifier(self):
                return "my.unique.tool.id"

            def get_name(self):
                return "My Tool"

            def get_description(self):
                return "Test"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            def get_risk_level(self):
                return RiskLevel.LOW

            def is_read_only(self):
                return True

            def get_required_permissions(self):
                return []

            def get_resource_mode(self):
                return "real"

            async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
                return {}

        tool = MyTool()
        assert tool.get_identifier() == "my.unique.tool.id"
        assert isinstance(tool.get_identifier(), str)
        assert len(tool.get_identifier()) > 0
