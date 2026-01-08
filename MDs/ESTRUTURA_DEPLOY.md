# ==============================================================================
# Estrutura de Deploy - nexo-rh
# ==============================================================================

## 📁 Estrutura no Servidor (/app/docker/nexo-rh)

```
/app/docker/nexo-rh/
│
├── docker-compose.prod.yml        # Orquestração (PostgreSQL + Backend + Frontend)
├── .env                           # Variáveis de ambiente (CRIAR MANUALMENTE)
├── deploy-server.sh               # Script de deploy automático
│
├── frontend/
│   └── nginx.conf                 # Config Nginx com proxy reverso
│
└── data/                          # Volumes (criados automaticamente)
    ├── postgres/                  # Dados PostgreSQL
    ├── uploads/                   # PDFs enviados
    ├── enviados/                  # Histórico
    ├── holerites/                 # Holerites processados
    ├── processed/                 # Arquivos processados
    └── sent/                      # Arquivos enviados
```

---

## 📦 Arquivos Necessários no Servidor

### ✅ Arquivos para Copiar:

1. **docker-compose.prod.yml** ✅
   - Stack completa (PostgreSQL + Backend + Frontend)

2. **frontend/nginx.conf** ✅
   - Configuração Nginx com proxy reverso

3. **.env** ⚠️
   - Copiar `.env.production.example` → `.env`
   - Editar com credenciais reais

4. **deploy-server.sh** (opcional) ✅
   - Script automatizado de deploy

---

## 🚀 Deploy Rápido

### Método 1: Manual (Recomendado para primeiro deploy)

```bash
# 1. Criar estrutura no servidor
ssh user@servidor
sudo mkdir -p /app/docker/nexo-rh/frontend
cd /app/docker/nexo-rh

# 2. Do Windows, copiar arquivos
scp docker-compose.prod.yml user@servidor:/app/docker/nexo-rh/
scp frontend/nginx.conf user@servidor:/app/docker/nexo-rh/frontend/
scp .env.production.example user@servidor:/app/docker/nexo-rh/.env

# 3. No servidor, editar .env
ssh user@servidor
cd /app/docker/nexo-rh
nano .env  # Configurar variáveis

# 4. Iniciar
docker-compose -f docker-compose.prod.yml up -d
```

### Método 2: Script Automático

```powershell
# No Windows
.\prepare-deploy.ps1

# Seguir instruções para copiar arquivos e executar deploy-server.sh no servidor
```

---

## 🔑 Configuração do .env

```env
# PostgreSQL
DB_HOST=postgres
DB_PORT=5432
DB_NAME=enviafolha_db
DB_USER=enviafolha_user
DB_PASSWORD=TROCAR_SENHA_FORTE_AQUI

# JWT
SECRET_KEY=GERAR_COM_openssl_rand_-hex_32

# Evolution API
EVOLUTION_SERVER_URL=https://sua-api.com
EVOLUTION_API_KEY=sua-api-key
EVOLUTION_INSTANCE_NAME=seu-instance

# App
LOG_LEVEL=info
PORT=8002
```

**Gerar SECRET_KEY:**
```bash
openssl rand -hex 32
```

---

## ✅ Checklist de Deploy

### Antes do Deploy:
- [ ] Servidor com Docker instalado
- [ ] Servidor com Docker Compose instalado
- [ ] Estrutura de diretórios criada
- [ ] Arquivos copiados
- [ ] `.env` configurado com credenciais reais
- [ ] Firewall configurado (portas 22, 80, 443)

### Durante o Deploy:
- [ ] Pull das imagens: `docker-compose pull`
- [ ] Iniciar stack: `docker-compose up -d`
- [ ] Verificar logs: `docker-compose logs -f`
- [ ] Verificar status: `docker-compose ps`

### Após o Deploy:
- [ ] Frontend acessível (http://servidor)
- [ ] Backend respondendo (http://servidor:8002)
- [ ] Health checks passando
- [ ] Login funcionando
- [ ] Teste de envio de holerite
- [ ] Backup configurado

---

## 🔒 Segurança

### Firewall (ufw):
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Permissões:
```bash
chmod 600 /app/docker/nexo-rh/.env
sudo chown -R $USER:$USER /app/docker/nexo-rh
```

### HTTPS (Recomendado):
- Usar Traefik, Caddy ou Nginx Proxy Manager
- Certificados Let's Encrypt gratuitos

---

## 📊 Comandos Úteis

```bash
# Ver logs em tempo real
docker-compose -f docker-compose.prod.yml logs -f

# Ver apenas backend
docker-compose -f docker-compose.prod.yml logs -f backend

# Reiniciar
docker-compose -f docker-compose.prod.yml restart

# Parar
docker-compose -f docker-compose.prod.yml down

# Atualizar
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Status
docker-compose -f docker-compose.prod.yml ps

# Backup do banco
docker exec nexo-rh-postgres pg_dump -U enviafolha_user enviafolha_db > backup.sql

# Restaurar backup
cat backup.sql | docker exec -i nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

---

## 🐛 Troubleshooting

### Container não inicia:
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

### Erro de conexão com banco:
```bash
docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

### Frontend 502 Bad Gateway:
- Verificar se backend está rodando
- Verificar logs do Nginx: `docker logs nexo-rh-frontend`

### Espaço em disco:
```bash
df -h
docker system df
docker system prune -a  # Limpar
```

---

## 📞 Suporte

- Logs: `docker-compose logs -f`
- Status: `docker-compose ps`
- Health: `curl http://localhost:8002/api/v1/database/health`
