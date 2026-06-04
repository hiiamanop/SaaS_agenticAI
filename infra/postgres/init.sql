-- infra/postgres/init.sql
-- Creates one database per ERP service.
-- Runs automatically on first container start.

CREATE DATABASE auth_db;
CREATE DATABASE tenant_db;
CREATE DATABASE crm_db;
CREATE DATABASE sales_db;
CREATE DATABASE inventory_db;
CREATE DATABASE procurement_db;
CREATE DATABASE accounting_db;
CREATE DATABASE approval_db;
CREATE DATABASE audit_db;
CREATE DATABASE agent_db;

GRANT ALL PRIVILEGES ON DATABASE auth_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE tenant_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE crm_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE sales_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE procurement_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE accounting_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE approval_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE audit_db TO erp;
GRANT ALL PRIVILEGES ON DATABASE agent_db TO erp;
