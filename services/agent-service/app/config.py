from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/agent_db"
    )
    service_name: str = "agent-service"
    debug: bool = False
    kafka_bootstrap_servers: str = "localhost:19092"
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "erp"

    # Model Gateway — "mock" (default, used in tests/CI) or "ollama"
    model_provider: str = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Downstream service the agent calls to execute approved recommendations
    procurement_url: str = "http://localhost:8004"


settings = Settings()
