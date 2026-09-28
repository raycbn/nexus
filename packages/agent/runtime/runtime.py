import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from packages.agent.llm.contract import LLMMessage, LLMProvider, LLMRequest
from packages.agent.runtime.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentStartedEvent,
    LLMResponseReceivedEvent,
    ObservationRecordedEvent,
    ToolAllowedEvent,
    ToolDeniedEvent,
    ToolExecutedEvent,
    ToolRequestedEvent,
)
from packages.agent.runtime.execution import (
    ToolExecutionResult,
    sanitize_failure,
    sanitize_observation_failure,
)
from packages.agent.runtime.observability import InMemoryEventSink
from packages.agent.runtime.state import AgentState, AgentStatus
from packages.domain.models.agent import Agent
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.registry import ToolRegistry


class AgentRuntime:
    def __init__(
        self,
        llm: LLMProvider,
        registry: ToolRegistry,
        policy: PolicyEvaluator,
        max_iterations: int = 10,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._policy = policy
        self._max_iterations = max_iterations
        self._events: InMemoryEventSink = InMemoryEventSink()

    @contextmanager
    def using_llm(self, provider: LLMProvider) -> Iterator[None]:
        """Temporarily use a different LLM provider for a runtime phase."""
        previous = self._llm
        self._llm = provider
        try:
            yield
        finally:
            self._llm = previous

    async def run(
        self,
        objective: str,
        agent: Agent,
        allowed_tool_identifiers: list[str],
        response_format: str | dict[str, Any] | None = None,
    ) -> AgentState:
        runtime_start = time.perf_counter()
        state = AgentState(
            objective=objective,
            agent_id=agent.id,
            organization_id=agent.organization_id,
            workspace_id=agent.workspace_id,
            status=AgentStatus.RUNNING,
        )

        self._events.emit(
            AgentStartedEvent(
                agent_id=agent.id,
                organization_id=agent.organization_id,
                workspace_id=agent.workspace_id,
                objective=objective,
            )
        )

        available_tools = [
            t for t in self._registry.list_tools() if t.get_identifier() in allowed_tool_identifiers
        ]

        if agent.system_instructions:
            state.messages.append(
                LLMMessage(role="system", content=agent.system_instructions)
            )
        state.messages.append(LLMMessage(role="user", content=objective))

        while state.iteration_count < self._max_iterations:
            if state.iteration_count > 0:
                print("[LLM] Sending follow-up...")
            request = LLMRequest(
                messages=state.messages,
                tools=[t.get_identifier() for t in available_tools],
                response_format=response_format,
            )

            try:
                llm_start = time.perf_counter()
                response = await self._llm.generate(request)
                llm_duration = time.perf_counter() - llm_start
            except Exception as e:
                self._events.emit(
                    AgentFailedEvent(
                        agent_id=agent.id,
                        reason=f"LLM generation failed: {e}",
                    )
                )
                state.status = AgentStatus.FAILED
                break

            self._events.emit(
                LLMResponseReceivedEvent(
                    agent_id=agent.id,
                    iteration=state.iteration_count,
                    has_tool_calls=response.wants_tool_execution,
                    content_preview=response.content[:200] if response.content else "",
                    tool_call_count=len(response.tool_calls),
                    duration=llm_duration,
                )
            )

            if response.wants_tool_execution:
                state.tool_calls.extend(response.tool_calls)
                state.messages.append(
                    LLMMessage(
                        role="assistant",
                        content=response.content or None,
                        tool_calls=response.tool_calls,
                    )
                )
                for tool_call in response.tool_calls:
                    self._events.emit(
                        ToolRequestedEvent(
                            agent_id=agent.id,
                            tool_name=tool_call.tool_name,
                            arguments=tool_call.arguments,
                        )
                    )

                    tool = self._registry.get(tool_call.tool_name)
                    tool_result = None

                    if tool is None:
                        self._events.emit(
                            ToolDeniedEvent(
                                agent_id=agent.id,
                                tool_name=tool_call.tool_name,
                                reason="Unknown tool",
                            )
                        )
                        observation = f"Unknown tool: {tool_call.tool_name}"
                    else:
                        allowed, reason = self._policy.is_tool_execution_allowed(
                            tool, allowed_tool_identifiers
                        )
                        if not allowed:
                            self._events.emit(
                                ToolDeniedEvent(
                                    agent_id=agent.id,
                                    tool_name=tool_call.tool_name,
                                    reason=reason,
                                )
                            )
                            observation = f"Tool denied: {reason}"
                        else:
                            self._events.emit(
                                ToolAllowedEvent(
                                    agent_id=agent.id,
                                    tool_name=tool_call.tool_name,
                                )
                            )
                            try:
                                tool_start = time.perf_counter()
                                exec_result = await tool.execute(tool_call.arguments)
                                tool_duration = time.perf_counter() - tool_start
                                tool_result = ToolExecutionResult.from_result(exec_result)
                                self._events.emit(
                                    ToolExecutedEvent(
                                        agent_id=agent.id,
                                        tool_name=tool_call.tool_name,
                                        success=True,
                                        duration=tool_duration,
                                        resource_mode=tool.get_resource_mode(),
                                        resource_id=tool.get_resource_id(),
                                        result=tool_result,
                                    )
                                )
                                observation = sanitize_observation_failure(
                                    RuntimeError("tool execution failed")
                                )
                                if exec_result is not None:
                                    observation = "Tool executed successfully"
                                self._events.emit(
                                    ObservationRecordedEvent(
                                        agent_id=agent.id,
                                        observation=observation,
                                    )
                                )
                                if tool_result is not None:
                                    state.tool_results.append(
                                        {
                                            "tool_name": tool_call.tool_name,
                                            "resource_id": tool.get_resource_id(),
                                            "structured_content": tool_result.structured_content,
                                        }
                                    )
                            except Exception as e:
                                tool_duration = time.perf_counter() - tool_start
                                failure = sanitize_failure(e)
                                self._events.emit(
                                    ToolExecutedEvent(
                                        agent_id=agent.id,
                                        tool_name=tool_call.tool_name,
                                        success=False,
                                        duration=tool_duration,
                                        resource_mode=tool.get_resource_mode(),
                                        resource_id=tool.get_resource_id(),
                                        failure=failure,
                                    )
                                )
                                observation = sanitize_observation_failure(e)

                    state.observations.append(observation)
                    if tool is not None and tool_result is not None:
                        tool_content = json.dumps(
                            tool_result.structured_content,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        if len(tool_content) > 6000:
                            tool_content = tool_content[:6000] + "...[truncated]"
                        observation = f"Tool result for {tool_call.tool_name}: {tool_content}"
                    state.messages.append(
                        LLMMessage(
                            role="tool",
                            tool_name=tool_call.tool_name,
                            tool_call_id=tool_call.id,
                            content=observation,
                        )
                    )
            else:
                state.final_result = response.content
                state.status = AgentStatus.COMPLETED
                self._events.emit(
                    AgentCompletedEvent(
                        agent_id=agent.id,
                        final_result=response.content,
                        iterations=state.iteration_count,
                    )
                )
                break

            state.iteration_count += 1

        if state.status == AgentStatus.RUNNING:
            state.status = AgentStatus.MAX_ITERATIONS
            self._events.emit(
                AgentFailedEvent(
                    agent_id=agent.id,
                    reason=f"Maximum iterations ({self._max_iterations}) exceeded",
                )
            )

        state.total_duration = time.perf_counter() - runtime_start
        return state

    async def collect_read_only_tools(
        self,
        agent: Agent,
        allowed_tool_identifiers: list[str],
    ) -> AgentState:
        """Collect one baseline observation from every allowed read-only tool."""
        state = AgentState(
            objective="Baseline read-only collection",
            agent_id=agent.id,
            organization_id=agent.organization_id,
            workspace_id=agent.workspace_id,
            status=AgentStatus.RUNNING,
        )
        available_tools = [
            tool
            for tool in self._registry.list_tools()
            if tool.get_identifier() in allowed_tool_identifiers
        ]

        for tool in available_tools:
            self._events.emit(
                ToolRequestedEvent(
                    agent_id=agent.id,
                    tool_name=tool.get_identifier(),
                    arguments={},
                )
            )
            allowed, reason = self._policy.is_allowed(tool, allowed_tool_identifiers)
            if not allowed:
                self._events.emit(
                    ToolDeniedEvent(
                        agent_id=agent.id,
                        tool_name=tool.get_identifier(),
                        reason=reason or "Denied by policy",
                    )
                )
                continue

            self._events.emit(
                ToolAllowedEvent(
                    agent_id=agent.id,
                    tool_name=tool.get_identifier(),
                )
            )
            tool_start = time.perf_counter()
            try:
                exec_result = await tool.execute({})
                tool_duration = time.perf_counter() - tool_start
                tool_result = ToolExecutionResult.from_result(exec_result)
                self._events.emit(
                    ToolExecutedEvent(
                        agent_id=agent.id,
                        tool_name=tool.get_identifier(),
                        success=True,
                        duration=tool_duration,
                        resource_mode=tool.get_resource_mode(),
                        resource_id=tool.get_resource_id(),
                        result=tool_result,
                    )
                )
                if tool_result is not None:
                    structured = tool_result.structured_content
                    state.tool_results.append(
                        {
                            "tool_name": tool.get_identifier(),
                            "resource_id": tool.get_resource_id(),
                            "structured_content": structured,
                        }
                    )
                    state.observations.append(
                        f"{tool.get_identifier()}: {json.dumps(structured, ensure_ascii=False)}"
                    )
                else:
                    state.observations.append(
                        f"{tool.get_identifier()}: no structured result"
                    )
            except Exception as exc:
                tool_duration = time.perf_counter() - tool_start
                failure = sanitize_failure(exc)
                self._events.emit(
                    ToolExecutedEvent(
                        agent_id=agent.id,
                        tool_name=tool.get_identifier(),
                        success=False,
                        duration=tool_duration,
                        resource_mode=tool.get_resource_mode(),
                        resource_id=tool.get_resource_id(),
                        failure=failure,
                    )
                )
                state.observations.append(f"{tool.get_identifier()}: execution failed")

        state.status = AgentStatus.COMPLETED
        state.total_duration = sum(
            event.duration
            for event in self._events.get_by_type(ToolExecutedEvent)
            if event.agent_id == agent.id
        )
        return state

    @property
    def events(self) -> InMemoryEventSink:
        return self._events
