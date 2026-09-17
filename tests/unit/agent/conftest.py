import asyncio
from uuid import uuid4

from packages.agent.llm.contract import LLMResponse
from packages.agent.runtime.runtime import AgentRuntime
from packages.domain.models.agent import Agent
from packages.domain.models.organization import Organization
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.user import User
from packages.domain.models.workspace import Workspace
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.providers.mock_tools import (
    GetCpuUsageTool,
    GetDiskUsageTool,
    GetMemoryUsageTool,
    GetRunningProcessesTool,
    GetSystemInfoTool,
)
from packages.tools.registry import ToolRegistry


def make_org():
    return Organization(name="Test Org")


def make_workspace(org_id=None):
    return Workspace(organization_id=org_id or uuid4(), name="Test WS")


def make_user(org_id):
    return User(organization_id=org_id, email="test@example.com", display_name="Test")


def make_agent(org_id, workspace_id=None, allowed_tool_ids=None):
    return Agent(
        organization_id=org_id,
        workspace_id=workspace_id,
        name="Test Agent",
        role="investigator",
        autonomy_level="read_only",
        allowed_tool_ids=allowed_tool_ids or [],
    )


def make_registry(tools):
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def make_policy(org_id, allowed=None):
    return PolicyModel(
        organization_id=org_id,
        name="test-policy",
        allowed_tool_ids=allowed or [],
    )


def make_runtime(llm, registry, policy, max_iterations=10):
    return AgentRuntime(
        llm=llm,
        registry=registry,
        policy=PolicyEvaluator(policy),
        max_iterations=max_iterations,
    )


def make_default_tools():
    return [
        GetSystemInfoTool(),
        GetCpuUsageTool(),
        GetMemoryUsageTool(),
        GetDiskUsageTool(),
        GetRunningProcessesTool(),
    ]


def make_default_policy(org_id, allowed=None):
    return make_policy(org_id, allowed_tool_ids=allowed or [])


def asyncio_run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_llm_response(content="", tool_calls=None):
    return LLMResponse(
        content=content,
        tool_calls=tool_calls or [],
    )
