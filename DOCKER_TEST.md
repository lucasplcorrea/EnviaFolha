# 🧪 Guia de Teste Local - Docker

## 📋 Pré-requisitos

1. PostgreSQL rodando localmente na porta 5432
2. Backend local parado (liberar porta 8002)
3. Frontend local parado (liberar porta 80)

## 🔧 Configuração Inicial

### 1. Criar arquivo .env
```powershell
# Copiar exemplo e editar com suas credenciais
cp .env.docker.example .env

# Editar .env com suas credenciais reais
notepad .env
```

**Importante:** Configure o `DB_HOST=host.docker.internal` para acessar o PostgreSQL do Windows.

### 2. Verificar PostgreSQL Acessível
```powershell
# Testar conexão com PostgreSQL
docker run --rm -it --add-host=host.docker.internal:host-gateway postgres:16-alpine psql -h host.docker.internal -U enviafolha_user -d enviafolha_db
```

## 🚀 Testar Individualmente

### Backend Isolado
```powershell
# Testar backend com PostgreSQL local
docker run --rm -p 8002:8002 \
  --add-host=host.docker.internal:host-gateway \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_NAME=enviafolha_db \
  -e DB_USER=enviafolha_user \
  -e DB_PASSWORD=secure_password \
  -e SECRET_KEY=your-secret-key \
  nexo-rh-backend:test
```

Acessar: http://localhost:8002/api/v1/database/health

### Frontend Isolado
```powershell
# Testar frontend (sem proxy, só arquivos estáticos)
docker run --rm -p 80:80 nexo-rh-frontend:test
```

Acessar: http://localhost

## 🎼 Testar com Docker Compose

### Stack Completa (Backend + Frontend + PostgreSQL local)
```powershell
# Subir stack completa
docker-compose -f docker-compose.prod.yml up

# Ou em background
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

**Acessos:**
- Frontend: http://localhost
- Backend: http://localhost:8002
- Health Backend: http://localhost:8002/api/v1/database/health

## 🔍 Troubleshooting

### Backend não conecta no PostgreSQL

**Erro:** `could not connect to server`

**Solução:**
1. Verificar se PostgreSQL está rodando: `docker ps -a` (procure por postgres)
2. Verificar se porta 5432 está aberta no Windows Firewall
3. Verificar se PostgreSQL aceita conexões externas:
   ```powershell
   # Entrar no container PostgreSQL
   docker exec -it <container-id> bash
   
   # Verificar postgresql.conf
   cat /var/lib/postgresql/data/postgresql.conf | grep listen_addresses
   # Deve ser: listen_addresses = '*'
   
   # Verificar pg_hba.conf
   cat /var/lib/postgresql/data/pg_hba.conf | grep host
   # Deve ter: host all all 0.0.0.0/0 scrypt ou md5
   ```

### Frontend erro 502 Bad Gateway

**Erro:** Nginx retorna 502 ao acessar /api/

**Solução:**
- Verificar se backend está rodando: `docker ps | grep backend`
- Verificar logs do backend: `docker logs nexo-rh-backend`
- Verificar se backend responde: `curl http://localhost:8002/api/v1/database/health`

### Porta 80 ou 8002 em uso

**Erro:** `bind: address already in use`

**Solução:**
```powershell
# Verificar processo usando a porta
netstat -ano | findstr :80
netstat -ano | findstr :8002

# Parar processo (substitua <PID> pelo número encontrado)
Stop-Process -Id <PID> -Force
```

## ✅ Checklist de Testes

- [ ] PostgreSQL local acessível de dentro do container
- [ ] Backend inicia sem erros
- [ ] Backend conecta no PostgreSQL
- [ ] Backend responde em /api/v1/database/health
- [ ] Frontend serve arquivos estáticos
- [ ] Frontend carrega em http://localhost
- [ ] Login funciona
- [ ] Dashboard carrega dados

## 🐛 Debug

### Ver logs do backend
```powershell
docker logs nexo-rh-backend -f
```

### Ver logs do frontend (Nginx)
```powershell
docker logs nexo-rh-frontend -f
```

### Entrar no container
```powershell
# Backend
docker exec -it nexo-rh-backend sh

# Frontend
docker exec -it nexo-rh-frontend sh
```

### Testar conexão entre containers
```powershell
# De dentro do frontend, testar backend
docker exec -it nexo-rh-frontend wget -O- http://backend:8002/api/v1/database/health
```

## 📝 Notas

1. **host.docker.internal** funciona no Docker Desktop para Windows/Mac
2. Se usar Docker no Linux, use `--network host` ou IP do host
3. O frontend sem docker-compose não terá proxy reverso (é normal)
4. Para produção, sempre usar docker-compose.prod.yml completo
