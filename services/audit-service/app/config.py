# services/audit-service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://erp:erp_dev_password@localhost:5432/audit_db"
    )
    kafka_brokers: str = "localhost:19092"
    kafka_group_id: str = "audit-service"
    kafka_topics: str = (
        "crm.lead.qualified,crm.opportunity.won,"
        "sales.order.created,sales.order.approved,"
        "inventory.stock.low,procurement.po.requested,procurement.po.approved,"
        "accounting.invoice.generated,accounting.payment.processed,"
        "approval.request.created,approval.request.approved,approval.request.rejected,"
        "agent.action.executed"
    )
    service_name: str = "audit-service"
    debug: bool = False


settings = Settings()
