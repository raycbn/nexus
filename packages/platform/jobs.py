from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class JobEnvelope:
    job_id: UUID
    job_type: str
    payload: dict
    idempotency_key: str
    created_at: datetime
    attempt: int = 0

    @classmethod
    def create(cls, job_type: str, payload: dict, idempotency_key: str) -> "JobEnvelope":
        if not job_type.strip():
            raise ValueError("job_type must not be empty")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        return cls(uuid4(), job_type, payload, idempotency_key, datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "job_id": str(self.job_id),
            "job_type": self.job_type,
            "payload": self.payload,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
            "attempt": self.attempt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobEnvelope":
        return cls(
            job_id=UUID(data["job_id"]),
            job_type=data["job_type"],
            payload=data["payload"],
            idempotency_key=data["idempotency_key"],
            created_at=datetime.fromisoformat(data["created_at"]),
            attempt=int(data.get("attempt", 0)),
        )
