# 🐳 Docker Setup - nexo-rh

## ✅ Arquivos Criados

### 📦 Dockerfiles
- **`backend/Dockerfile.prod`** - Imagem otimizada do backend (multi-stage, ~300MB)
- **`frontend/Dockerfile.prod`** - Imagem otimizada do frontend com Nginx (~25MB)

### 🎼 Docker Compose
- **`docker-compose.prod.yml`** - Orquestração completa para produção
  - PostgreSQL 16 Alpine
  - Backend (nexo-rh-backend:latest)
  - Frontend (nexo-rh-frontend:latest)
  - Health checks configurados
  - Volumes persistentes

### 🚀 Scripts de Deploy
- **`build-and-push.sh`** - Script Bash para Linux/Mac
- **`build-and-push.ps1`** - Script PowerShell para Windows
- **`test-build.sh`** - Teste rápido antes do push (Linux/Mac)
- **`test-build.ps1`** - Teste rápido antes do push (Windows)
- **`Makefile`** - Comandos úteis (make build, make deploy, etc)

### 📋 Configuração
- **`.env.production.example`** - Template de variáveis de ambiente
- **`.dockerignore`** - Arquivos ignorados no build (raiz)
- **`backend/.dockerignore`** - Específico do backend
- **`frontend/.dockerignore`** - Específico do frontend

### 📚 Documentação
- **`DOCKER_DEPLOY.md`** - Guia completo de deploy

---

## 🚀 Quick Start

### 1. Primeiro Build Local (Windows)

```powershell
# Testar build antes de fazer push
.\test-build.ps1

# Se OK, build e push para Docker Hub
.\build-and-push.ps1
```

### 2. Deploy Local para Testar

```bash
# Subir tudo localmente
docker-compose -f docker-compose.prod.yml up

# Ou em background
docker-compose -f docker-compose.prod.yml up -d
```

**Acessos:**
- Frontend: http://localhost
- Backend: http://localhost:8002
- PostgreSQL: localhost:5432

### 3. Push para Docker Hub

```powershell
# Login no Docker Hub
docker login

# Build e push
.\build-and-push.ps1
# Ou com username customizado
$env:DOCKER_USERNAME="seu-usuario"
.\build-and-push.ps1
```

### 4. Deploy em Servidor de Produção

```bash
# No servidor
git clone seu-repo
cd EnviaFolha

# Configurar .env
cp .env.production.example .env
nano .env  # Editar com credenciais reais

# Pull das imagens
docker pull nexorh/nexo-rh-backend:latest
docker pull nexorh/nexo-rh-frontend:latest

# Subir
docker-compose -f docker-compose.prod.yml up -d

# Verificar
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 📦 Imagens Docker Hub

Após fazer push, suas imagens estarão disponíveis em:

- **Backend:** `nexorh/nexo-rh-backend:latest`
- **Frontend:** `nexorh/nexo-rh-frontend:latest`

Para usar em qualquer servidor:
```bash
docker pull nexorh/nexo-rh-backend:latest
docker pull nexorh/nexo-rh-frontend:latest
```

---

## 🎯 Arquitetura

```
┌───────────────────────────────────────┐
│  🌐 Frontend (Nginx)                  │
│  nexorh/nexo-rh-frontend:latest       │
│  Port 80 → React Build + Proxy        │
└─────────────┬─────────────────────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  ⚙️  Backend (FastAPI)                │
│  nexorh/nexo-rh-backend:latest        │
│  Port 8002 → Python + Evolution API   │
└─────────────┬─────────────────────────┘
              │
              ▼
┌───────────────────────────────────────┐
│  🗄️  PostgreSQL 16                    │
│  postgres:16-alpine                   │
│  Port 5432 → Database persistente     │
└───────────────────────────────────────┘
```

---

## 🔧 Comandos Úteis

### Com Makefile (Linux/Mac)
```bash
make build          # Build local
make deploy         # Deploy local
make logs           # Ver logs
make status         # Ver status
make update         # Atualizar containers
make backup-db      # Backup do banco
```

### Comandos Docker Diretos
```bash
# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Reiniciar
docker-compose -f docker-compose.prod.yml restart

# Parar
docker-compose -f docker-compose.prod.yml down

# Shell do backend
docker exec -it nexo-rh-backend sh

# Shell do banco
docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

---

## ⚠️ Importante - Antes de Fazer Push

1. **Testar localmente primeiro:**
   ```powershell
   .\test-build.ps1
   docker-compose -f docker-compose.prod.yml up
   ```

2. **Verificar se tudo funciona:**
   - [ ] Frontend carrega em http://localhost
   - [ ] Backend responde em http://localhost:8002
   - [ ] Login funciona
   - [ ] Conexão com banco funciona

3. **Configurar .env de produção:**
   - [ ] Alterar `SECRET_KEY` JWT
   - [ ] Configurar Evolution API
   - [ ] Senha forte do PostgreSQL
   - [ ] Verificar URLs corretas

---

## 🔐 Checklist de Segurança

- [ ] Senhas fortes em `.env`
- [ ] `SECRET_KEY` aleatória e forte
- [ ] Não commitar `.env` no git
- [ ] Usar HTTPS em produção (Traefik/Nginx Proxy)
- [ ] Firewall configurado (portas 80, 443, 22 apenas)
- [ ] Backup automático do banco
- [ ] Logs externos (opcional)

---

## 🐞 Troubleshooting

### Build falha
```powershell
# Limpar cache do Docker
docker builder prune -a -f

# Tentar novamente
.\test-build.ps1
```

### Container não inicia
```bash
# Ver logs detalhados
docker-compose -f docker-compose.prod.yml logs backend

# Verificar configuração
docker-compose -f docker-compose.prod.yml config
```

### Banco de dados não conecta
```bash
# Verificar se PostgreSQL está rodando
docker-compose -f docker-compose.prod.yml ps

# Testar conexão
docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

---

## 📞 Próximos Passos

1. ✅ **Testar build local** - `.\test-build.ps1`
2. ✅ **Testar docker-compose** - `docker-compose -f docker-compose.prod.yml up`
3. ✅ **Fazer login Docker Hub** - `docker login`
4. ✅ **Build e push** - `.\build-and-push.ps1`
5. ✅ **Deploy em servidor** - Seguir `DOCKER_DEPLOY.md`

---

## 📚 Documentação Completa

Veja **`DOCKER_DEPLOY.md`** para guia completo com:
- Configuração detalhada
- Exemplos de deploy
- Backup e restore
- Monitoramento
- Atualização de versões
