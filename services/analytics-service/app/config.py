from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/analytics_db"
    )
    service_name: str = "analytics-service"
    debug: bool = False
    kafka_bootstrap_servers: str = "localhost:19092"
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "erp"


settings = Settings()
