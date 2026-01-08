# 📁 Estrutura de Deploy - Servidor

## 🗂️ Estrutura de Diretórios no Servidor

```
/app/docker/nexo-rh/
├── .env                           # Variáveis de ambiente (CRIAR no servidor)
├── docker-compose.prod.yml        # Orquestração dos containers
├── frontend/
│   └── nginx.conf                 # Configuração Nginx com proxy reverso
└── data/                          # Volumes de dados (criados automaticamente)
    ├── postgres/                  # Dados do PostgreSQL
    ├── uploads/                   # PDFs enviados
    ├── enviados/                  # Histórico de envios
    ├── holerites/                 # Holerites processados
    ├── processed/                 # Arquivos processados
    └── sent/                      # Arquivos enviados
```

## 📦 Arquivos Necessários

### 1. docker-compose.prod.yml
- ✅ Já existe no projeto
- Orquestra PostgreSQL + Backend + Frontend

### 2. frontend/nginx.conf
- ✅ Já existe no projeto  
- Configuração Nginx com proxy reverso para backend

### 3. .env (CRIAR NO SERVIDOR)
- ⚠️ NÃO commitar no Git
- Copiar de `.env.production.example` e preencher com credenciais reais

### 4. .gitignore (OPCIONAL)
- Para ignorar arquivos sensíveis se usar Git no servidor

## 🚀 Passos para Deploy

### Passo 1: Criar estrutura no servidor
```bash
# SSH no servidor
ssh user@seu-servidor

# Criar diretório
sudo mkdir -p /app/docker/nexo-rh
cd /app/docker/nexo-rh

# Criar subdiretórios
mkdir -p frontend data/{postgres,uploads,enviados,holerites,processed,sent}

# Ajustar permissões
sudo chown -R $USER:$USER /app/docker/nexo-rh
```

### Passo 2: Copiar arquivos do local para servidor
```powershell
# Do seu Windows, copiar arquivos via SCP
scp docker-compose.prod.yml user@servidor:/app/docker/nexo-rh/
scp frontend/nginx.conf user@servidor:/app/docker/nexo-rh/frontend/
scp .env.production.example user@servidor:/app/docker/nexo-rh/.env
```

### Passo 3: Configurar .env no servidor
```bash
# SSH no servidor
ssh user@servidor
cd /app/docker/nexo-rh

# Editar .env com credenciais reais
nano .env
```

**Variáveis críticas para editar:**
- `DB_PASSWORD` - Senha forte do PostgreSQL
- `SECRET_KEY` - Chave JWT forte (gerar com: `openssl rand -hex 32`)
- `EVOLUTION_SERVER_URL` - URL da sua Evolution API
- `EVOLUTION_API_KEY` - API Key da Evolution
- `EVOLUTION_INSTANCE_NAME` - Nome da instância

### Passo 4: Pull das imagens Docker
```bash
cd /app/docker/nexo-rh

# Pull das imagens do Docker Hub
docker pull lucasplcorrea/nexo-rh-backend:latest
docker pull lucasplcorrea/nexo-rh-frontend:latest
docker pull postgres:16-alpine
```

### Passo 5: Iniciar aplicação
```bash
# Iniciar stack completa
docker-compose -f docker-compose.prod.yml up -d

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f

# Verificar status
docker-compose -f docker-compose.prod.yml ps
```

## 🔒 Segurança - IMPORTANTE

### No Servidor:
1. **Firewall** - Abrir apenas portas necessárias:
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS (se usar)
   sudo ufw enable
   ```

2. **Permissões do .env**:
   ```bash
   chmod 600 /app/docker/nexo-rh/.env
   ```

3. **HTTPS** (RECOMENDADO):
   - Usar Traefik, Nginx Proxy Manager ou Caddy
   - Certificados Let's Encrypt gratuitos

### No Git:
- ✅ `.env` está no `.gitignore`
- ✅ Nunca commitar senhas ou API keys
- ✅ Usar `.env.production.example` como template

## 📝 Checklist de Deploy

- [ ] Servidor com Docker e Docker Compose instalados
- [ ] Estrutura de diretórios criada em `/app/docker/nexo-rh`
- [ ] `docker-compose.prod.yml` copiado
- [ ] `frontend/nginx.conf` copiado
- [ ] `.env` criado e configurado com credenciais reais
- [ ] `SECRET_KEY` gerada com `openssl rand -hex 32`
- [ ] `DB_PASSWORD` forte definida
- [ ] Evolution API configurada
- [ ] Imagens Docker baixadas (pull)
- [ ] Firewall configurado
- [ ] Permissões do `.env` ajustadas (chmod 600)
- [ ] Stack iniciada com `docker-compose up -d`
- [ ] Health checks passando
- [ ] Frontend acessível
- [ ] Backend respondendo
- [ ] Login funcionando

## 🔄 Comandos Úteis no Servidor

```bash
# Ver logs em tempo real
docker-compose -f docker-compose.prod.yml logs -f

# Reiniciar serviços
docker-compose -f docker-compose.prod.yml restart

# Parar tudo
docker-compose -f docker-compose.prod.yml down

# Atualizar para nova versão
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Backup do banco
docker exec nexo-rh-postgres pg_dump -U enviafolha_user enviafolha_db > backup_$(date +%Y%m%d).sql

# Ver status
docker-compose -f docker-compose.prod.yml ps

# Ver recursos
docker stats nexo-rh-backend nexo-rh-frontend nexo-rh-postgres
```

## 📊 Monitoramento

```bash
# Health checks
curl http://localhost/health                              # Frontend
curl http://localhost:8002/api/v1/database/health         # Backend

# Verificar PostgreSQL
docker exec nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db -c "SELECT COUNT(*) FROM employees;"
```

## 🐛 Troubleshooting

### Container não inicia
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

### Banco não conecta
```bash
docker exec -it nexo-rh-postgres psql -U enviafolha_user -d enviafolha_db
```

### Espaço em disco
```bash
df -h
docker system df
docker system prune -a  # Limpar imagens antigas
```
