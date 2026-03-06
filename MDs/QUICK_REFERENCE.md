# 🚀 Quick Reference - nexo-rh Docker

## 📝 Passo a Passo Completo

### 1️⃣ Validar Ambiente
```powershell
.\validate-deploy.ps1
```

### 2️⃣ Testar Build Local
```powershell
.\test-build.ps1
```

### 3️⃣ Testar Aplicação Local
```powershell
docker-compose -f docker-compose.prod.yml up
```
- Frontend: http://localhost
- Backend: http://localhost:8002

### 4️⃣ Login no Docker Hub
```powershell
docker login
```

### 5️⃣ Build e Push
```powershell
.\build-and-push.ps1
```

### 6️⃣ Deploy em Servidor
```bash
# SSH no servidor
ssh user@servidor

# Criar diretório
mkdir -p /opt/nexo-rh
cd /opt/nexo-rh

# Copiar arquivos
# (do local para servidor)
scp docker-compose.prod.yml user@servidor:/opt/nexo-rh/
scp .env.production.example user@servidor:/opt/nexo-rh/.env

# No servidor, editar .env
nano .env

# Pull e deploy
docker pull nexorh/nexo-rh-backend:latest
docker pull nexorh/nexo-rh-frontend:latest
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔧 Comandos Diários

### Ver Status
```bash
docker-compose -f docker-compose.prod.yml ps
```

### Ver Logs
```bash
# Todos os serviços
docker-compose -f docker-compose.prod.yml logs -f

# Apenas backend
docker-compose -f docker-compose.prod.yml logs -f backend

# Últimas 100 linhas
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Reiniciar Serviços
```bash
# Todos
docker-compose -f docker-compose.prod.yml restart

# Apenas backend
docker-compose -f docker-compose.prod.yml restart backend
```

### Parar/Iniciar
```bash
# Parar
docker-compose -f docker-compose.prod.yml stop

# Iniciar
docker-compose -f docker-compose.prod.yml start

# Parar e remover
docker-compose -f docker-compose.prod.yml down
```

---

## 🐞 Troubleshooting

### Container não inicia
```bash
# Ver logs detalhados
docker-compose -f docker-compose.prod.yml logs backend

# Verificar saúde
docker inspect nexo-rh-backend | grep Health -A 10
```

### Banco de dados
```bash
# Acessar PostgreSQL
docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db

# Verificar tabelas
\dt

# Ver employees
SELECT COUNT(*) FROM employees;
```

### Rebuild
```bash
# Parar tudo
docker-compose -f docker-compose.prod.yml down

# Rebuild
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 💾 Backup

### Banco de Dados
```bash
# Backup
docker exec nexo-rh-postgres pg_dump -U enviafolha_user enviafolha_db > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20250127.sql | docker exec -i nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

### Volumes
```bash
# Backup de uploads
docker run --rm \
  -v nexo-rh_uploads_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/uploads_backup.tar.gz /data
```

---

## 🔄 Atualização

### Pull Nova Versão
```bash
docker pull nexorh/nexo-rh-backend:latest
docker pull nexorh/nexo-rh-frontend:latest
docker-compose -f docker-compose.prod.yml up -d
```

### Limpar Imagens Antigas
```bash
docker image prune -a
```

---

## 📊 Monitoramento

### Health Checks
```bash
# Frontend
curl http://localhost/health

# Backend
curl http://localhost:8002/api/v1/database/health
```

### Recursos
```bash
# Stats em tempo real
docker stats nexo-rh-backend nexo-rh-frontend nexo-rh-postgres

# Uso de disco
docker system df
```

---

## 🔐 Segurança

### Verificar .env
```bash
# NUNCA commitar .env!
git status

# Ver variáveis
cat .env | grep -v "#"
```

### Alterar Senhas
```bash
# Editar .env
nano .env

# Recriar containers
docker-compose -f docker-compose.prod.yml up -d
```

---

## ⚡ Comandos Rápidos

```bash
# Status rápido
docker-compose -f docker-compose.prod.yml ps

# Logs em tempo real
docker-compose -f docker-compose.prod.yml logs -f

# Reiniciar tudo
docker-compose -f docker-compose.prod.yml restart

# Atualizar
docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d

# Limpar tudo (CUIDADO!)
docker-compose -f docker-compose.prod.yml down -v
```
