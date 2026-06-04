.PHONY: help dev down logs reset status ps setup topics

.DEFAULT_GOAL := help

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Start all services and wait until healthy
	@echo "Starting ERP local dev environment..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; fi
	docker compose up -d
	@bash scripts/wait-for-services.sh
	@echo ""
	@echo "\033[32mAll services ready:\033[0m"
	@echo "  Traefik dashboard  →  http://localhost:8090"
	@echo "  Grafana            →  http://grafana.localhost    (admin/admin)"
	@echo "  Prometheus         →  http://prometheus.localhost"
	@echo "  Redpanda Console   →  http://redpanda.localhost"
	@echo "  Vault UI           →  http://vault.localhost      (token: dev-root-token)"
	@echo "  Qdrant dashboard   →  http://localhost:6333/dashboard"
	@echo ""
	@echo "Next step: run 'make topics' to create all Kafka topics."

down: ## Stop all services
	docker compose down

logs: ## Follow logs from all services
	docker compose logs -f

reset: ## DESTRUCTIVE: stop all services and remove all volumes
	@echo "\033[31mWARNING: This will delete all local data!\033[0m"
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	docker compose down -v
	@echo "All volumes removed. Run 'make dev' to start fresh."

status: ## Show health status of all services
	@bash scripts/wait-for-services.sh --check-only

ps: ## List running containers
	docker compose ps

setup: ## First-time setup: copy .env and seed Vault secrets
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env"; else echo ".env already exists"; fi
	@docker compose up -d vault postgres redis redpanda qdrant
	@sleep 8
	@bash scripts/seed-vault.sh

topics: ## Create all Kafka topics in Redpanda
	@bash scripts/bootstrap-topics.sh
