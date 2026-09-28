from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionField:
    key: str
    label: str
    field_type: str = "text"
    required: bool = True
    secret: bool = False


@dataclass(frozen=True)
class CredentialRequirement:
    key: str
    label: str
    secret: bool = True
