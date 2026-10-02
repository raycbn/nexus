from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="ignore")

    secret_key: SecretStr = Field(default=SecretStr("dev-secret-key-change-in-production"))
    algorithm: str = "HS256"
    token_issuer: str = "nexus"
    token_audience: str = "nexus-api"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    app_environment: str = "local"
    app_debug: bool = True
    auto_migrate: bool = True
    auto_bootstrap: bool = False
    allowed_origins: str = "http://localhost:3000"
    sso_public_base_url: str = ""
    sso_oidc_allowed_hosts: str = ""
    nexus_version: str = "0.3.0"
    postgres_container: str = "nexus-selfhosted-postgres"
    redis_container: str = "nexus-selfhosted-redis"
    update_channel: str = "stable"
    update_manifest_url: str = ""
    update_latest_version: str = "0.3.0"
    license_mode: str = "owner-configured"
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    billing_success_url: str = "http://localhost:3000/billing?success=1"
    billing_cancel_url: str = "http://localhost:3000/billing?cancelled=1"
    bootstrap_email: str = "admin@nexus.local"
    bootstrap_password: SecretStr = Field(default=SecretStr("nexus-admin"))

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0

    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    ollama_model: str | None = None
    ollama_think: bool = False
    ollama_num_ctx: int = 8192
    ollama_timeout: int = 120

    lab_ssh_host: str = "localhost"
    lab_ssh_port: int = 2222
    lab_ssh_username: str = "nexus"
    lab_ssh_key_path: str = "infrastructure/lab/ssh_key"
    lab_app_base_url: str = "http://localhost:8080"
    lab_app_slow_seconds: int = 2

    remediation_kill_switch: bool = True
    remediation_writes_enabled: bool = False
    remediation_lab_only: bool = True
    remediation_max_retries: int = 1
    remediation_command_timeout: int = 30

    default_organization_id: str = "00000000-0000-0000-0000-000000000002"
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def ollama_base_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def secret_key_str(self) -> str:
        return self.secret_key.get_secret_value()

    @property
    def bootstrap_password_str(self) -> str:
        return self.bootstrap_password.get_secret_value()

    @property
    def allowed_origins_list(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]

    @property
    def default_secret_key(self) -> str:
        return "dev-secret-key-change-in-production"

