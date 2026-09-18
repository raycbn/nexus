from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    ollama_model: str | None = None
    ollama_think: bool = False
    ollama_num_ctx: int = 8192
    ollama_timeout: int = 120

    @property
    def ollama_base_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"
