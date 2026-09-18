from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    ollama_model: str | None = None
    ollama_think: bool = False
    ollama_num_ctx: int = 8192
    ollama_timeout: int = 120

    # --- Linux Lab (local development infrastructure) ---
    lab_ssh_host: str = "localhost"
    lab_ssh_port: int = 2222
    lab_ssh_username: str = "nexus"
    # Path to a local private SSH key file (gitignored; key contents are never
    # stored in source, only the path is referenced by configuration).
    lab_ssh_key_path: str = "infrastructure/lab/ssh_key"

    @property
    def ollama_base_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"
