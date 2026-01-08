# 🚀 Deploy - Sistema de Jobs em Background

## 📋 Resumo da Atualização

Esta atualização resolve o **problema crítico de bloqueio do servidor** durante envios em massa de holerites.

### Problema Original
- Durante envio de 232 holerites (~4 horas com delays anti-ban)
- Servidor HTTP completamente travado
- Dashboard mostrava "banco offline"
- Estatísticas não atualizavam
- React frontend não conseguia fazer requisições

### Solução Implementada
✅ **Sistema de Jobs em Background com Threading**
- Envios processados em thread separada
- Servidor HTTP sempre responsivo
- Progress tracking em tempo real
- Modal de progresso no frontend
- Usuário pode navegar durante envio

---

## 🔧 Mudanças Técnicas

### Backend (`main_legacy.py`)

#### 1. Gerenciador de Jobs (linhas 248-294)
```python
class BulkSendJob:
    - job_id: UUID único
    - status: running/completed/failed
    - processed_files / total_files
    - successful_sends / failed_sends
    - progress_percentage
    - current_file
    - elapsed_seconds
```

#### 2. Função de Processamento em Background (linhas 625-892)
- Roda em `threading.Thread` separada
- Não bloqueia servidor HTTP
- Mantém delays anti-ban (47-73s)
- Registra no banco de dados
- Logs detalhados com [JOB id]

#### 3. Handler Modificado (linhas 3393-3472)
```python
POST /api/v1/payrolls/bulk-send
→ Retorna HTTP 202 (Accepted) em <1 segundo
→ Response: { job_id, total_files, status_endpoint }
```

#### 4. Novo Endpoint (linhas 3474-3503)
```python
GET /api/v1/payrolls/bulk-send/{job_id}/status
→ Retorna progresso em tempo real
```

### Frontend (`PayrollSender.jsx`)

#### 1. Estados de Polling
```javascript
const [activeJobId, setActiveJobId] = useState(null);
const [jobStatus, setJobStatus] = useState(null);
const [pollingInterval, setPollingInterval] = useState(null);
const [showProgressModal, setShowProgressModal] = useState(false);
```

#### 2. Função de Polling
- Checa status a cada 2 segundos
- Atualiza modal de progresso
- Para automaticamente quando job termina
- Cleanup em useEffect

#### 3. Modal de Progresso
- Barra de progresso visual
- Contador de arquivos processados
- Lista de envios bem-sucedidos/falhados
- Arquivo atual sendo processado
- Tempo decorrido
- Permite navegação durante envio

---

## 📦 Deploy no Servidor

### Passo 1: Fazer Pull das Novas Imagens

```bash
# Conectar no servidor via SSH
ssh usuario@192.168.230.253

# Entrar no diretório do projeto
cd /caminho/do/projeto

# Fazer pull das imagens atualizadas
docker pull lucasplcorrea/nexo-rh-backend:latest
docker pull lucasplcorrea/nexo-rh-frontend:latest
```

### Passo 2: Verificar Imagens

```bash
# Verificar se imagens foram baixadas
docker images | grep nexo-rh

# Deve mostrar:
# lucasplcorrea/nexo-rh-backend   latest   31639ea6e7b6   (nova)
# lucasplcorrea/nexo-rh-frontend  latest   1c62daabfb0e   (nova)
```

### Passo 3: Parar Containers Antigos

```bash
# Parar e remover containers antigos
docker-compose down

# OU, se estiver usando docker ps
docker stop backend frontend
docker rm backend frontend
```

### Passo 4: Subir Novos Containers

```bash
# Subir containers com novas imagens
docker-compose up -d

# Verificar se subiram corretamente
docker-compose ps

# Verificar logs
docker-compose logs -f --tail=50
```

### Passo 5: Testar Funcionalidade

1. **Acessar sistema**: http://192.168.230.253:7080
2. **Fazer login**
3. **Ir para "Enviar Holerites"**
4. **Selecionar alguns arquivos de teste** (3-5 arquivos)
5. **Clicar em "Enviar Selecionados"**
6. **Verificar se**:
   - Modal de progresso aparece
   - Barra de progresso atualiza a cada 2 segundos
   - Pode navegar para Dashboard durante envio
   - Dashboard continua funcionando
   - Estatísticas atualizam normalmente

---

## 🧪 Teste de Validação

### Teste 1: Responsividade Durante Envio
```bash
# Terminal 1: Iniciar envio de 10 holerites
# (via interface web)

# Terminal 2: Verificar se API responde
curl -X GET http://192.168.230.253:7080/api/v1/dashboard/stats \
  -H "Authorization: Bearer SEU_TOKEN"

# Deve retornar JSON com estatísticas (não deve travar!)
```

### Teste 2: Polling de Status
```bash
# Obter job_id da resposta do envio bulk
JOB_ID="cole-aqui-o-job-id"

# Verificar status
curl -X GET http://192.168.230.253:7080/api/v1/payrolls/bulk-send/$JOB_ID/status \
  -H "Authorization: Bearer SEU_TOKEN"

# Resposta esperada:
{
  "job_id": "uuid-aqui",
  "status": "running",
  "processed_files": 2,
  "total_files": 10,
  "successful_sends": 2,
  "failed_sends": 0,
  "progress_percentage": 20.0,
  "current_file": "arquivo_003.pdf",
  "elapsed_seconds": 150
}
```

### Teste 3: Navegação Durante Envio
1. Iniciar envio de holerites
2. Enquanto modal mostra progresso, abrir outra aba
3. Acessar Dashboard, Reports, Cadastro de Funcionários
4. Verificar que todas as páginas carregam normalmente
5. Voltar para página de envio
6. Modal ainda deve estar mostrando progresso atualizado

---

## 📊 Monitoramento

### Logs do Backend
```bash
# Ver logs em tempo real
docker-compose logs -f backend

# Procurar por mensagens de job
docker-compose logs backend | grep "JOB"

# Exemplo de saída esperada:
# 🚀 [JOB 1a2b3c4d] Thread iniciada - processando 10 arquivos...
# ⚡ [JOB 1a2b3c4d] Primeiro holerite - SEM DELAY
# 📄 [JOB 1a2b3c4d] [1/10] Enviando arquivo_001.pdf para João Silva...
# ✅ [JOB 1a2b3c4d] Holerite enviado para João Silva
# ⏳ [JOB 1a2b3c4d] AGUARDANDO 53.47s (53s) antes do envio #2...
# 📄 [JOB 1a2b3c4d] [2/10] Enviando arquivo_002.pdf para Maria Santos...
```

### Verificar Jobs Ativos
```bash
# Entrar no container
docker exec -it backend bash

# Abrir Python REPL
python3

# Verificar jobs em memória
>>> from main_legacy import bulk_send_jobs
>>> bulk_send_jobs
{'job-id-1': <BulkSendJob object>, ...}
```

---

## 🐛 Troubleshooting

### Problema: Modal não aparece após clicar em "Enviar"
**Causa**: Frontend não recebeu job_id do backend  
**Solução**:
1. Verificar logs do backend: `docker-compose logs backend | grep bulk-send`
2. Verificar se response tem `job_id` no Network tab do navegador
3. Verificar console do navegador (F12)

### Problema: Progresso não atualiza no modal
**Causa**: Polling não está funcionando  
**Solução**:
1. Abrir DevTools → Network → Verificar se há requests para `/status`
2. Verificar console para erros de JavaScript
3. Verificar se `pollingInterval` foi iniciado

### Problema: Sistema ainda trava durante envio
**Causa**: Imagem antiga ainda em uso  
**Solução**:
```bash
# Forçar recriação de containers
docker-compose down
docker-compose pull
docker-compose up -d --force-recreate

# Verificar digest das imagens
docker inspect lucasplcorrea/nexo-rh-backend:latest | grep Id
# Deve mostrar: sha256:31639ea6e7b6...
```

### Problema: Job fica "stuck" em "running"
**Causa**: Thread travou por algum erro  
**Solução**:
```bash
# Ver logs detalhados
docker-compose logs backend | grep -A 20 "JOB.*ERROR"

# Reiniciar container (job em memória será perdido)
docker-compose restart backend
```

---

## 📈 Melhorias Futuras (Opcional)

### 1. Persistência de Jobs
Atualmente jobs ficam em memória. Para produção, considere:
- Redis para armazenar jobs
- PostgreSQL para histórico de jobs
- Recuperação de jobs após restart

### 2. WebSocket para Updates em Tempo Real
Substituir polling por WebSocket:
```javascript
// Ao invés de polling a cada 2s
const ws = new WebSocket('ws://192.168.230.253:7080/ws/jobs');
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  setJobStatus(status);
};
```

### 3. Celery para Job Queue Robusto
Para escalar, migrar para Celery:
```python
# Backend com Celery + Redis
@celery.task
def process_bulk_send(selected_files, templates, user_id):
    # Código do job aqui
```

### 4. Cancelamento de Jobs
Adicionar botão para cancelar job em andamento:
```python
# Backend
job.status = 'cancelled'
thread.terminate()  # (requer cuidados!)
```

---

## ✅ Checklist de Deploy

- [ ] Pull das novas imagens Docker
- [ ] Parar containers antigos
- [ ] Subir containers novos
- [ ] Verificar logs sem erros
- [ ] Testar login no sistema
- [ ] Testar envio de 3-5 holerites
- [ ] Verificar modal de progresso aparece
- [ ] Verificar barra de progresso atualiza
- [ ] Navegar para Dashboard durante envio
- [ ] Verificar Dashboard responde normalmente
- [ ] Aguardar conclusão do job de teste
- [ ] Verificar arquivos movidos para `enviados/`
- [ ] Verificar registros no banco de dados
- [ ] Fazer envio de produção (232+ arquivos)

---

## 📞 Suporte

Se encontrar problemas:

1. **Coletar logs**:
   ```bash
   docker-compose logs backend > backend_logs.txt
   docker-compose logs frontend > frontend_logs.txt
   ```

2. **Verificar status dos containers**:
   ```bash
   docker-compose ps
   docker stats
   ```

3. **Verificar configuração**:
   ```bash
   docker-compose config
   ```

4. **Enviar informações**:
   - Logs coletados
   - Screenshot do erro no navegador (se houver)
   - Console do navegador (F12 → Console tab)

---

## 🎉 Resultado Esperado

Após deploy bem-sucedido:

✅ Envio de 232 holerites não trava mais o sistema  
✅ Dashboard sempre responsivo durante envio  
✅ Estatísticas atualizam em tempo real  
✅ Modal mostra progresso visual com barra  
✅ Usuário pode navegar livremente durante envio  
✅ Delays anti-ban preservados (47-73s)  
✅ Todos os registros salvos no banco  
✅ React funciona como esperado ("dinamismo")  

**Tempo de envio**: Continua ~4 horas para 232 arquivos (delays anti-ban mantidos)  
**Diferença**: Servidor fica 100% funcional durante todo o processo! 🚀
