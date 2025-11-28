# ==============================================================================
# README - Deploy Docker - nexo-rh
# ==============================================================================

## 🚀 Quick Start

### 1️⃣ Desenvolvimento Local

```bash
# Subir todos os serviços (com dev mode)
docker-compose up --build

# Apenas produção (sem volumes de dev)
docker-compose -f docker-compose.prod.yml up --build
```

### 2️⃣ Build e Push para Docker Hub

**Windows (PowerShell):**
```powershell
# Fazer login no Docker Hub
docker login

# Build e push
.\build-and-push.ps1
```

**Linux/Mac (Bash):**
```bash
# Fazer login no Docker Hub
docker login

# Dar permissão de execução
chmod +x build-and-push.sh

# Build e push
./build-and-push.sh
```

### 3️⃣ Deploy em Servidor (Produção)

```bash
# 1. Copiar arquivos necessários para o servidor
scp docker-compose.prod.yml user@server:/opt/nexo-rh/
scp .env.production.example user@server:/opt/nexo-rh/.env

# 2. No servidor, editar .env com credenciais reais
nano .env

# 3. Pull das imagens
docker pull nexorh/nexo-rh-backend:latest
docker pull nexorh/nexo-rh-frontend:latest

# 4. Subir os serviços
docker-compose -f docker-compose.prod.yml up -d

# 5. Verificar status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## 📦 Estrutura das Imagens

### Backend (`nexo-rh-backend:latest`)
- **Base:** Python 3.11-slim
- **Tamanho:** ~300MB (otimizado com multi-stage build)
- **Porta:** 8002
- **Healthcheck:** `/api/v1/database/health`
- **Executa:** `main_legacy.py`

### Frontend (`nexo-rh-frontend:latest`)
- **Base:** Nginx 1.25-alpine
- **Tamanho:** ~25MB (apenas build estático)
- **Porta:** 80
- **Healthcheck:** `/health`
- **Features:** Gzip, cache, proxy reverso para backend

## 🔧 Configuração

### Variáveis de Ambiente Importantes

```env
# Database
DB_HOST=postgres
DB_NAME=enviafolha_db
DB_USER=enviafolha_user
DB_PASSWORD=secure_password

# Evolution API
EVOLUTION_SERVER_URL=https://api.evolution.com
EVOLUTION_API_KEY=your-key
EVOLUTION_INSTANCE_NAME=instance-name

# JWT
SECRET_KEY=your-strong-secret-key-here
```

### Volumes Persistentes

```yaml
volumes:
  postgres_data      # Dados do banco PostgreSQL
  uploads_data       # PDFs enviados pelos usuários
  enviados_data      # Histórico de envios
  holerites_data     # Holerites processados
  processed_data     # Arquivos processados
  sent_data          # Arquivos enviados
```

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────┐
│           Nginx (Frontend)                  │
│     nexo-rh-frontend:latest (Port 80)       │
│  React Build + Proxy Reverso                │
└──────────────┬──────────────────────────────┘
               │ HTTP Proxy
               ▼
┌─────────────────────────────────────────────┐
│        FastAPI (Backend)                    │
│     nexo-rh-backend:latest (Port 8002)      │
│  Python 3.11 + PostgreSQL + Evolution API   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│        PostgreSQL Database                  │
│     postgres:16-alpine (Port 5432)          │
│  Dados persistentes em volume               │
└─────────────────────────────────────────────┘
```

## 🔍 Troubleshooting

### Ver logs
```bash
# Todos os serviços
docker-compose -f docker-compose.prod.yml logs -f

# Apenas backend
docker-compose -f docker-compose.prod.yml logs -f backend

# Apenas frontend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### Reiniciar serviços
```bash
# Reiniciar tudo
docker-compose -f docker-compose.prod.yml restart

# Reiniciar apenas backend
docker-compose -f docker-compose.prod.yml restart backend
```

### Limpar e recriar
```bash
# Parar e remover containers
docker-compose -f docker-compose.prod.yml down

# Remover volumes (CUIDADO: apaga dados!)
docker-compose -f docker-compose.prod.yml down -v

# Recriar do zero
docker-compose -f docker-compose.prod.yml up -d --build
```

### Acessar shell do container
```bash
# Backend
docker exec -it nexo-rh-backend sh

# PostgreSQL
docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

## 🔐 Segurança em Produção

1. **Sempre altere as senhas padrão!**
2. Use HTTPS (considere Traefik ou Nginx Proxy Manager)
3. Configure firewall (ufw, iptables)
4. Use Docker secrets para credenciais sensíveis
5. Mantenha imagens atualizadas: `docker-compose pull && docker-compose up -d`
6. Faça backup regular dos volumes do PostgreSQL

## 📊 Monitoramento

### Health Checks
```bash
# Frontend
curl http://localhost/health

# Backend
curl http://localhost:8002/api/v1/database/health

# PostgreSQL
docker exec nexo-rh-postgres pg_isready
```

### Métricas de recursos
```bash
docker stats nexo-rh-backend nexo-rh-frontend nexo-rh-postgres
```

## 🆙 Atualização

```bash
# 1. Pull das novas imagens
docker pull nexorh/nexo-rh-backend:latest
docker pull nexorh/nexo-rh-frontend:latest

# 2. Recriar containers (mantém volumes)
docker-compose -f docker-compose.prod.yml up -d

# 3. Remover imagens antigas
docker image prune -a
```

## 📝 Backup

```bash
# Backup do banco de dados
docker exec nexo-rh-postgres pg_dump -U enviafolha_user enviafolha_db > backup_$(date +%Y%m%d).sql

# Backup dos volumes
docker run --rm -v nexo-rh_uploads_data:/data -v $(pwd):/backup ubuntu tar czf /backup/uploads_backup.tar.gz /data
```

## 🎯 Checklist de Deploy

- [ ] Configurar `.env` com credenciais reais
- [ ] Alterar `SECRET_KEY` JWT
- [ ] Configurar Evolution API (EVOLUTION_SERVER_URL, EVOLUTION_API_KEY)
- [ ] Testar conexão com PostgreSQL
- [ ] Verificar portas (80, 8002, 5432)
- [ ] Configurar firewall
- [ ] Testar health checks
- [ ] Configurar backups automáticos
- [ ] Documentar credenciais em local seguro
- [ ] Testar envio de holerite
- [ ] Configurar logs externos (opcional)

## 📞 Suporte

Para dúvidas ou problemas:
- Verificar logs: `docker-compose logs -f`
- Verificar status: `docker-compose ps`
- Reiniciar: `docker-compose restart`
