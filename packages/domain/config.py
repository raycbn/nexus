from pydantic_settings import BaseSettings, SettingsConfigDict


class NexusSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_model: str = "nomic-embed-text"

    @property
    def ollama_base_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"
