from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/tenant_db"
    )
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "erp"
    service_name: str = "tenant-service"
    debug: bool = False


settings = Settings()
