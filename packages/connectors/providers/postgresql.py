
import asyncpg

from packages.connectors.base import Connector
from packages.connectors.base.models import ConnectorCapabilities, HealthStatus, ReadResult
from packages.domain.exceptions import ConnectorAuthenticationError, ConnectorConnectionError
from packages.domain.models.resource import Resource


class PostgreSQLConnector(Connector):
    """Read-only PostgreSQL connector for health and inventory discovery."""

    def __init__(
        self,
        resource: Resource,
        host: str,
        username: str,
        password: str,
        database: str = "postgres",
        port: int = 5432,
        connect_timeout: float = 10.0,
    ) -> None:
        self._resource = resource
        self._host = host
        self._username = username
        self._password = password
        self._database = database
        self._port = port
        self._connect_timeout = connect_timeout
        self._connection: asyncpg.Connection | None = None

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(read=True, write=False, discover=True)

    async def connect(self, resource: Resource) -> None:
        if resource.resource_type.value != "postgresql":
            raise ValueError(f"Resource type not supported: {resource.resource_type}")
        try:
            self._connection = await asyncpg.connect(
                host=self._host,
                port=self._port,
                user=self._username,
                password=self._password,
                database=self._database,
                timeout=self._connect_timeout,
            )
        except asyncpg.InvalidPasswordError as exc:
            raise ConnectorAuthenticationError("PostgreSQL authentication failed") from exc
        except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
            raise ConnectorConnectionError(str(exc)) from exc

    async def disconnect(self, resource: Resource) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def health_check(self, resource: Resource) -> HealthStatus:
        if self._connection is None:
            return HealthStatus(healthy=False, message="not connected")
        try:
            row = await self._connection.fetchrow(
                "SELECT version() AS version, current_database() AS database"
            )
            return HealthStatus(
                healthy=True,
                message="connected",
                details={"database": row["database"], "version": row["version"]},
            )
        except asyncpg.PostgresError as exc:
            return HealthStatus(healthy=False, message=str(exc))

    async def discover(self, resource: Resource):
        if self._connection is None:
            raise ConnectorConnectionError("PostgreSQL connector is not connected")
        row = await self._connection.fetchrow(
            "SELECT current_database() AS database, current_user AS username"
        )
        labels = dict(resource.labels)
        labels.update({"database": row["database"], "database_user": row["username"]})
        yield resource.model_copy(update={"labels": labels})

    async def execute_read(self, resource: Resource, command: str) -> ReadResult:
        if self._connection is None:
            return ReadResult(success=False, error="PostgreSQL connector is not connected")
        try:
            rows = await self._connection.fetch(command)
            return ReadResult(
                success=True,
                data=[dict(row) for row in rows],
                metadata={"database": self._database},
            )
        except asyncpg.PostgresError as exc:
            return ReadResult(success=False, error=str(exc))

