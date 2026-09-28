from pydantic import BaseModel, Field


class ValidationAction(BaseModel):
    hypothesis_index: int
    action_tool: str = Field(min_length=1)
    expected_condition: str = Field(min_length=1)


class ValidationPlan(BaseModel):
    actions: list[ValidationAction] = Field(default_factory=list)
