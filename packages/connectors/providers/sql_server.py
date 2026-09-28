import asyncio
from typing import Any

import pytds

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.resource import Resource


class SQLServerConnector(Connector):
    """Read-only SQL Server connector for health and inventory discovery."""

    def __init__(self, resource: Resource, host: str, username: str, password: str,
                 database: str = "master", port: int = 1433, connect_timeout: float = 10.0) -> None:
        self._resource, self._host, self._username = resource, host, username
        self._password, self._database, self._port = password, database, port
        self._connect_timeout = connect_timeout
        self._connection: Any | None = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        if resource.resource_type.value != "sql_server":
            raise ValueError(f"Resource type not supported: {resource.resource_type}")
        try:
            self._connection = await asyncio.to_thread(
                pytds.connect, self._host, self._database, self._username, self._password,
                port=self._port, timeout=self._connect_timeout, autocommit=True,
            )
        except (pytds.OperationalError, OSError, TimeoutError) as exc:
            message = str(exc)
            if "login" in message.lower() or "password" in message.lower():
                raise ConnectorAuthenticationError("SQL Server authentication failed") from exc
            raise ConnectorConnectionError(message) from exc

    async def disconnect(self, resource: Resource) -> None:
        if self._connection is not None:
            await asyncio.to_thread(self._connection.close)
            self._connection = None

    async def _fetch(self, command: str) -> list[dict[str, Any]]:
        def run() -> list[dict[str, Any]]:
            cursor = self._connection.cursor()
            try:
                cursor.execute(command)
                columns = [item[0] for item in cursor.description or ()]
                return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            finally:
                cursor.close()
        return await asyncio.to_thread(run)

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._connection is None:
            return HealthStatus(healthy=False, message="not connected")
        try:
            row = (await self._fetch("SELECT @@VERSION AS version, DB_NAME() AS database"))[0]
            return HealthStatus(healthy=True, message="connected", details=row)
        except Exception as exc:
            return HealthStatus(healthy=False, message=str(exc))

    async def discover(self, resource: Resource):
        if self._connection is None:
            raise ConnectorConnectionError("SQL Server connector is not connected")
        row = (await self._fetch("SELECT DB_NAME() AS database, SUSER_SNAME() AS username"))[0]
        labels = dict(resource.labels)
        labels.update({"database": str(row["database"]), "database_user": str(row["username"])})
        yield resource.model_copy(update={"labels": labels})

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._connection is None:
            return ReadResult(success=False, error="SQL Server connector is not connected")
        try:
            return ReadResult(success=True, data=await self._fetch(command),
                              metadata={"database": self._database})
        except Exception as exc:
            return ReadResult(success=False, error=str(exc))
