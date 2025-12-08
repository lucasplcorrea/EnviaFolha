# 🚨 CORREÇÃO URGENTE - Deploy do Sistema de Jobs

## Problema Identificado

O container `nexo-rh-backend` estava tentando executar um arquivo inexistente:
```
python: can't open file '/app/minimal_server_postgres.py': [Errno 2] No such file or directory
```

**Causa**: A imagem Docker no Docker Hub tinha o comando CMD incorreto (apontando para arquivo antigo).

**Solução**: Imagem corrigida foi reconstruída e enviada para o Docker Hub com o comando correto: `python main_legacy.py`

---

## ✅ Correção Aplicada

**Nova imagem disponível**:
- `lucasplcorrea/nexo-rh-backend:latest`
- Digest: `sha256:f0533456c4d94d9f0bb24862c40e3ca96f546925d77731fec3fd5eb086e6446a`
- Comando correto: `CMD ["python", "main_legacy.py"]`

---

## 🔧 Como Corrigir no Servidor

### Opção 1: Script Automatizado (Recomendado)

```bash
# Baixar e executar script de correção
cd /app/docker/nexorh
wget https://raw.githubusercontent.com/lucasplcorrea/EnviaFolha/main/fix-deploy.sh
chmod +x fix-deploy.sh
./fix-deploy.sh
```

### Opção 2: Manual (Passo a Passo)

```bash
# 1. Parar containers
cd /app/docker/nexorh
docker compose down

# 2. Remover imagem antiga (força download da nova)
docker rmi lucasplcorrea/nexo-rh-backend:latest

# 3. Baixar imagens corrigidas
docker pull lucasplcorrea/nexo-rh-backend:latest
docker pull lucasplcorrea/nexo-rh-frontend:latest

# 4. Verificar se comando está correto
docker inspect lucasplcorrea/nexo-rh-backend:latest | grep -A 2 '"Cmd"'
# Deve mostrar: "python", "main_legacy.py"

# 5. Iniciar containers
docker compose up -d

# 6. Verificar status
docker compose ps

# 7. Ver logs
docker logs nexo-rh-backend --tail 50
```

---

## 🧪 Validação

### 1. Verificar se containers estão rodando

```bash
docker ps | grep nexo-rh
```

**Saída esperada**:
```
nexo-rh-backend    Up X seconds (healthy)
nexo-rh-frontend   Up X seconds (healthy)
nexo-rh-postgres   Up X seconds (healthy)
```

### 2. Testar endpoint do backend

```bash
curl http://localhost:8002/health
```

**Resposta esperada**:
```json
{
  "status": "ok",
  "timestamp": "2025-12-08T..."
}
```

### 3. Verificar logs sem erros

```bash
docker logs nexo-rh-backend --tail 20
```

**Logs esperados** (sem erros):
```
🚀 Servidor HTTP rodando em http://0.0.0.0:8002
✅ PostgreSQL conectado com sucesso
📊 Sistema pronto para receber requisições
```

### 4. Testar no navegador

1. Acesse: http://192.168.230.253:7080
2. Faça login
3. Vá para "Enviar Holerites"
4. Selecione 2-3 arquivos de teste
5. Clique em "Enviar Selecionados"
6. **Verifique se**:
   - Modal de progresso aparece
   - Barra de progresso atualiza
   - Pode navegar para Dashboard
   - Dashboard continua funcionando

---

## 🐛 Troubleshooting

### Erro: "Container keeps restarting"

```bash
# Ver logs completos
docker logs nexo-rh-backend -f

# Verificar se variáveis de ambiente estão corretas
docker inspect nexo-rh-backend | grep -A 20 '"Env"'
```

### Erro: "Healthcheck failing"

```bash
# Testar healthcheck manualmente
docker exec nexo-rh-backend curl -f http://localhost:8002/api/v1/database/health

# Se falhar, verificar conexão com PostgreSQL
docker exec nexo-rh-backend env | grep DB_
```

### Erro: "Cannot connect to PostgreSQL"

```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres

# Testar conexão
docker exec nexo-rh-postgres pg_isready -U enviafolha_user -d enviafolha_db

# Ver logs do PostgreSQL
docker logs nexo-rh-postgres
```

### Container está rodando mas não responde

```bash
# Entrar no container
docker exec -it nexo-rh-backend bash

# Verificar se arquivo existe
ls -la main_legacy.py

# Tentar executar manualmente
python main_legacy.py

# Verificar portas
netstat -tulpn | grep 8002
```

---

## 📊 Checklist de Validação

Após a correção, verifique:

- [ ] Container `nexo-rh-backend` está com status "Up" (não "Restarting")
- [ ] Healthcheck do backend está "healthy"
- [ ] Logs do backend não mostram erros
- [ ] Endpoint `/health` responde HTTP 200
- [ ] Frontend carrega no navegador
- [ ] Login funciona
- [ ] Pode acessar Dashboard
- [ ] Pode enviar holerites de teste
- [ ] Modal de progresso aparece
- [ ] Progresso atualiza em tempo real
- [ ] Sistema continua responsivo durante envio

---

## 📝 Notas Importantes

1. **Imagem corrigida**: A nova imagem já está no Docker Hub e pronta para uso
2. **Sem perda de dados**: Seus dados no PostgreSQL e volumes estão preservados
3. **Sistema de jobs**: Toda a funcionalidade de background jobs está incluída
4. **Compatibilidade**: Nenhuma alteração no banco de dados é necessária

---

## 🆘 Se Nada Funcionar

Como último recurso (reconstrução completa):

```bash
# ATENÇÃO: Isso vai parar todos os containers
cd /app/docker/nexorh

# Backup do .env (importante!)
cp .env .env.backup

# Parar tudo
docker compose down -v

# Limpar imagens antigas
docker rmi lucasplcorrea/nexo-rh-backend:latest
docker rmi lucasplcorrea/nexo-rh-frontend:latest

# Baixar imagens novas
docker pull lucasplcorrea/nexo-rh-backend:latest
docker pull lucasplcorrea/nexo-rh-frontend:latest

# Subir tudo novamente
docker compose up -d

# Aguardar 30 segundos
sleep 30

# Verificar status
docker compose ps
docker compose logs -f
```

---

## 📞 Suporte

Se o problema persistir após seguir todos os passos:

1. Colete logs completos:
   ```bash
   docker compose logs > logs_completos.txt
   docker inspect nexo-rh-backend > inspect_backend.txt
   ```

2. Tire screenshot do erro no navegador (se houver)

3. Envie os arquivos coletados

---

## ✅ Status da Correção

- [x] Problema identificado
- [x] Imagem corrigida criada
- [x] Push para Docker Hub concluído
- [x] Script de correção criado
- [x] Documentação atualizada
- [ ] Deploy no servidor (aguardando execução)
- [ ] Testes de validação (aguardando deploy)
