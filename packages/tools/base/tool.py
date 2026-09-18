from abc import ABC, abstractmethod
from typing import Any

from packages.domain.models.enums import RiskLevel


class Tool(ABC):
    @abstractmethod
    def get_identifier(self) -> str: ...

    @abstractmethod
    def get_name(self) -> str: ...

    @abstractmethod
    def get_description(self) -> str: ...

    @abstractmethod
    def get_input_schema(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_output_schema(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_risk_level(self) -> RiskLevel: ...

    @abstractmethod
    def is_read_only(self) -> bool: ...

    @abstractmethod
    def get_required_permissions(self) -> list[str]: ...

    @abstractmethod
    def get_resource_mode(self) -> str: ...

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]: ...
