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

    async def run(
        self,
        objective: str,
        agent: Agent,
        allowed_tool_identifiers: list[str],
    ) -> AgentState:
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

        state.messages.append(LLMMessage(role="user", content=objective))

        while state.iteration_count < self._max_iterations:
            request = LLMRequest(
                messages=state.messages,
                tools=[t.get_identifier() for t in available_tools],
            )

            try:
                response = await self._llm.generate(request)
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
                )
            )

            if response.wants_tool_execution:
                for tool_call in response.tool_calls:
                    self._events.emit(
                        ToolRequestedEvent(
                            agent_id=agent.id,
                            tool_name=tool_call.tool_name,
                            arguments=tool_call.arguments,
                        )
                    )

                    tool = self._registry.get(tool_call.tool_name)

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
                        allowed, reason = self._policy.is_allowed(tool, allowed_tool_identifiers)
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
                                await tool.execute(tool_call.arguments)
                                self._events.emit(
                                    ToolExecutedEvent(
                                        agent_id=agent.id,
                                        tool_name=tool_call.tool_name,
                                        success=True,
                                    )
                                )
                                observation = f"Tool {tool_call.tool_name} executed successfully"
                                self._events.emit(
                                    ObservationRecordedEvent(
                                        agent_id=agent.id,
                                        observation=observation,
                                    )
                                )
                            except Exception as e:
                                self._events.emit(
                                    ToolExecutedEvent(
                                        agent_id=agent.id,
                                        tool_name=tool_call.tool_name,
                                        success=False,
                                    )
                                )
                                observation = f"Tool execution failed: {e}"

                    state.observations.append(observation)
                    state.messages.append(
                        LLMMessage(
                            role="tool",
                            tool_name=tool_call.tool_name,
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

        return state

    @property
    def events(self) -> InMemoryEventSink:
        return self._events
