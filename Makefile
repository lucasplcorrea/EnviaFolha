# ==============================================================================
# Makefile - Comandos úteis para nexo-rh
# ==============================================================================

.PHONY: help build test push deploy clean logs status

# Variáveis
DOCKER_USERNAME ?= nexorh
BACKEND_IMAGE = $(DOCKER_USERNAME)/nexo-rh-backend
FRONTEND_IMAGE = $(DOCKER_USERNAME)/nexo-rh-frontend
TAG ?= latest

help: ## Mostrar esta ajuda
	@echo "Comandos disponíveis para nexo-rh:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

build: ## Build local das imagens (para teste)
	@echo "🔨 Building imagens..."
	cd backend && docker build -f Dockerfile.prod -t $(BACKEND_IMAGE):$(TAG) .
	cd frontend && docker build -f Dockerfile.prod -t $(FRONTEND_IMAGE):$(TAG) .
	@echo "✅ Build concluído!"

test: ## Testar build localmente
	@echo "🧪 Testando build..."
	docker-compose -f docker-compose.prod.yml config
	@echo "✅ Configuração válida!"

push: ## Push das imagens para Docker Hub
	@echo "📤 Pushing para Docker Hub..."
	docker push $(BACKEND_IMAGE):$(TAG)
	docker push $(FRONTEND_IMAGE):$(TAG)
	@echo "✅ Push concluído!"

deploy: ## Deploy local com docker-compose
	@echo "🚀 Iniciando deploy local..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Deploy concluído!"
	@echo "Frontend: http://localhost"
	@echo "Backend: http://localhost:8002"

stop: ## Parar containers
	@echo "⏸️  Parando containers..."
	docker-compose -f docker-compose.prod.yml stop

down: ## Parar e remover containers
	@echo "🛑 Removendo containers..."
	docker-compose -f docker-compose.prod.yml down

clean: ## Limpar volumes e containers (CUIDADO: apaga dados!)
	@echo "🧹 Limpando tudo..."
	docker-compose -f docker-compose.prod.yml down -v
	docker system prune -f

logs: ## Ver logs dos containers
	docker-compose -f docker-compose.prod.yml logs -f

logs-backend: ## Ver logs apenas do backend
	docker-compose -f docker-compose.prod.yml logs -f backend

logs-frontend: ## Ver logs apenas do frontend
	docker-compose -f docker-compose.prod.yml logs -f frontend

status: ## Ver status dos containers
	docker-compose -f docker-compose.prod.yml ps

restart: ## Reiniciar containers
	docker-compose -f docker-compose.prod.yml restart

update: ## Atualizar containers (pull + recreate)
	@echo "🔄 Atualizando containers..."
	docker-compose -f docker-compose.prod.yml pull
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Atualização concluída!"

backup-db: ## Backup do banco de dados
	@echo "💾 Fazendo backup do PostgreSQL..."
	docker exec nexo-rh-postgres pg_dump -U enviafolha_user enviafolha_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup salvo!"

shell-backend: ## Acesso shell do backend
	docker exec -it nexo-rh-backend sh

shell-db: ## Acesso shell do PostgreSQL
	docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db

health: ## Verificar health dos serviços
	@echo "🏥 Verificando health..."
	@echo "Frontend: $$(curl -s http://localhost/health || echo 'FAIL')"
	@echo "Backend: $$(curl -s http://localhost:8002/api/v1/database/health || echo 'FAIL')"

stats: ## Ver estatísticas de recursos
	docker stats nexo-rh-backend nexo-rh-frontend nexo-rh-postgres
