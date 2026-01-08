# 🧪 Teste de Visibilidade Cross-Browser - Guia Rápido

## 📋 Checklist de Validação

### ✅ Pré-requisitos
- [ ] Backend rodando (porta 8000)
- [ ] Frontend rodando (porta 3000)
- [ ] PostgreSQL com tabelas send_queues e send_queue_items
- [ ] Usuário admin e usuário regular criados
- [ ] Holerites carregados no sistema

---

## 🎯 Teste 1: Visibilidade Cross-Browser (Mesmo Computador)

### Setup
- Navegador 1: Chrome
- Navegador 2: Firefox ou Edge
- Ambos logados com usuários diferentes (ou mesmo usuário)

### Passos

**No Chrome (Navegador 1):**
1. Faça login
2. Acesse `/payrolls/sender`
3. Selecione 5-10 holerites
4. Clique em "Enviar Holerites"
5. Observe o card de progresso aparecer

**No Firefox (Navegador 2) - ENQUANTO O CHROME ESTÁ ENVIANDO:**
1. Faça login
2. Acesse `/payrolls/sender`
3. **✅ DEVE VER:** Card laranja "⚠️ Envios em Andamento no Sistema"
4. **✅ DEVE CONTER:**
   - Descrição: "Envio de X holerites"
   - Progresso: "Y de X enviados (Z%)"
   - Usuário: Nome do usuário do Chrome
   - Computador: Nome da máquina
   - Contadores: "✅ N | ❌ M"
5. **✅ DEVE ATUALIZAR:** A cada 5 segundos

### Resultado Esperado
```
✅ Card aparece automaticamente no Firefox
✅ Progresso atualiza em tempo real
✅ Percentual aumenta gradualmente
✅ Quando Chrome termina, card desaparece após 5 segundos
```

---

## 🌐 Teste 2: Visibilidade Cross-Computer

### Setup
- Computador A: Desktop do escritório
- Computador B: Laptop ou outro desktop
- Ambos na mesma rede (ou servidor em nuvem acessível)

### Passos

**No Computador A:**
1. Acesse `http://<servidor>:3000`
2. Faça login
3. Vá para `/payrolls/sender`
4. Inicie envio de holerites

**No Computador B:**
1. Acesse `http://<servidor>:3000`
2. Faça login (usuário diferente ou mesmo)
3. Vá para `/payrolls/sender`
4. **✅ DEVE VER:** Status do envio do Computador A
5. **✅ CAMPO "Computador":** Deve mostrar nome do Computador A

### Resultado Esperado
```
✅ Computador B vê envio do Computador A
✅ Nome do computador diferente aparece
✅ Progresso sincronizado
✅ Múltiplos computadores monitoram simultaneamente
```

---

## 📊 Teste 3: Múltiplos Envios Simultâneos

### Setup
- 3 navegadores ou 3 usuários em computadores diferentes

### Passos

**Simultaneamente:**
1. Usuário A: Inicia envio de 10 holerites
2. Usuário B: Inicia envio de 15 holerites (2 minutos depois)
3. Usuário C: Apenas observa (não envia nada)

**No navegador do Usuário C:**
- **✅ DEVE VER:** 2 cards laranja
- Card 1: Envio do Usuário A
- Card 2: Envio do Usuário B
- Ambos atualizando independentemente

### Resultado Esperado
```
✅ Múltiplos cards aparecem
✅ Cada card mostra usuário e computador corretos
✅ Progressos independentes
✅ Cards desaparecem conforme envios terminam
```

---

## 🔍 Teste 4: Verificação de Banco de Dados

### Durante um Envio Ativo

**Query 1: Ver fila ativa**
```sql
SELECT 
    queue_id,
    queue_type,
    description,
    status,
    total_items,
    processed_items,
    success_count,
    failure_count,
    computer_name,
    created_at
FROM send_queues
WHERE status IN ('pending', 'processing')
ORDER BY created_at DESC;
```

**Resultado Esperado:**
```
✅ Registro existe com status 'processing'
✅ processed_items aumentando gradualmente
✅ success_count incrementando
✅ computer_name preenchido
```

**Query 2: Ver itens da fila**
```sql
SELECT 
    qi.item_id,
    qi.status,
    qi.phone_number,
    qi.file_path,
    qi.error_message,
    e.full_name
FROM send_queue_items qi
JOIN employees e ON e.id = qi.employee_id
WHERE qi.queue_id = '<queue_id_from_query_1>'
ORDER BY qi.created_at;
```

**Resultado Esperado:**
```
✅ Itens com status 'pending' (ainda não processados)
✅ Itens com status 'sent' (já enviados com sucesso)
✅ Itens com status 'failed' (se houver falhas)
✅ error_message preenchido quando status = 'failed'
```

---

## 🔧 Teste 5: API Endpoints

### Endpoint: GET /api/v1/queue/active

**Request:**
```bash
curl -H "Authorization: Bearer <seu_token>" \
     http://localhost:8000/api/v1/queue/active
```

**Response Esperado (durante envio):**
```json
{
  "queues": [
    {
      "queue_id": "abc123...",
      "queue_type": "holerite",
      "description": "Envio de 10 holerites",
      "status": "processing",
      "total_items": 10,
      "processed_items": 3,
      "success_count": 3,
      "failure_count": 0,
      "progress_percentage": 30.0,
      "computer_name": "DESKTOP-ABC123",
      "ip_address": "192.168.1.100",
      "user": {
        "id": 1,
        "full_name": "João Silva",
        "email": "joao@example.com"
      },
      "created_at": "2025-01-20T10:30:00Z",
      "updated_at": "2025-01-20T10:35:00Z"
    }
  ]
}
```

**Response Esperado (sem envios):**
```json
{
  "queues": []
}
```

### Endpoint: GET /api/v1/queue/list

**Request:**
```bash
curl -H "Authorization: Bearer <seu_token>" \
     "http://localhost:8000/api/v1/queue/list?status=completed&limit=5"
```

**Response Esperado:**
```json
{
  "queues": [
    {
      "queue_id": "def456...",
      "status": "completed",
      "total_items": 10,
      "processed_items": 10,
      "success_count": 9,
      "failure_count": 1,
      "progress_percentage": 100.0,
      ...
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 5
}
```

---

## 🐛 Debugging: Se Card Não Aparecer

### Checklist de Debug

**1. Verificar Console do Navegador (F12)**
```javascript
// Deve aparecer:
"Loading active queues..."
"Active queues loaded: [...]"
```

**2. Verificar Network Tab**
```
GET /api/v1/queue/active
Status: 200
Response: { "queues": [...] }
```

**3. Verificar Console do Backend**
```
🚀 [JOB abc123de] Thread iniciada...
📋 [JOB abc123de] Fila criada: def456gh
✅ [JOB abc123de] 10 itens adicionados à fila
```

**4. Verificar Estado React (React DevTools)**
```javascript
PayrollSender
├── activeQueues: [{ queue_id: "...", ... }]  // Deve ter dados
└── queuesPollingInterval: <intervalId>        // Deve existir
```

**5. Verificar Banco de Dados**
```sql
-- Deve ter registro:
SELECT * FROM send_queues WHERE status = 'processing';
```

---

## 🎯 Cenários de Erro Comuns

### Problema 1: Card Aparece mas Não Atualiza

**Causa:** Intervalo de polling não está rodando

**Verificar:**
```javascript
// No console do navegador:
console.log(queuesPollingInterval);  // Deve ser um número, não null
```

**Solução:**
- Recarregar a página
- Verificar se useEffect está desmontando corretamente

### Problema 2: Card Não Aparece em Outro Navegador

**Causa:** Fila não foi criada no banco

**Verificar:**
```sql
SELECT * FROM send_queues ORDER BY created_at DESC LIMIT 1;
```

**Se vazio:**
- Verificar logs do backend por erros na criação da fila
- Verificar permissões do usuário no banco
- Verificar conexão DB em `process_bulk_send_in_background`

### Problema 3: Progresso Não Atualiza no Banco

**Causa:** Erro ao commitar updates

**Verificar:**
```python
# Logs do backend devem mostrar:
"⚠️ [JOB ...] Erro ao atualizar fila: ..."
```

**Solução:**
- Verificar transações do banco
- Verificar foreign keys (employee_id válido)
- Verificar constraints de JSONB

---

## 📊 Métricas de Sucesso

### Latência de Atualização
```
✅ Card deve aparecer em: < 5 segundos (primeiro polling)
✅ Progresso deve atualizar em: ~5 segundos (intervalo de polling)
✅ Card deve desaparecer após conclusão em: < 5 segundos
```

### Precisão de Dados
```
✅ Progresso no frontend == processed_items/total_items no banco
✅ Nome do usuário correto
✅ Nome do computador correto
✅ Contadores de sucesso/falha precisos
```

### Concorrência
```
✅ Suportar 5+ usuários enviando simultaneamente
✅ Suportar 10+ observadores simultâneos
✅ Polling não sobrecarrega servidor
```

---

## 🚀 Teste de Aceitação Final

### Critérios para Aprovação

- [ ] ✅ Envio iniciado no Chrome aparece no Firefox
- [ ] ✅ Envio iniciado no Computador A aparece no Computador B
- [ ] ✅ Progresso atualiza em tempo real (< 10s de defasagem)
- [ ] ✅ Múltiplos envios simultâneos aparecem como múltiplos cards
- [ ] ✅ Card desaparece quando envio termina
- [ ] ✅ Nome do usuário e computador corretos
- [ ] ✅ Contadores de sucesso/falha precisos
- [ ] ✅ Página `/queue-management` lista todas as filas
- [ ] ✅ Banco de dados registra corretamente
- [ ] ✅ Sem erros no console (frontend e backend)

### Se Todos os Critérios Forem Atendidos

**✅ SISTEMA APROVADO PARA PRODUÇÃO**

---

## 📝 Relatório de Teste (Modelo)

```markdown
# Relatório de Teste - Visibilidade Cross-Browser

**Data:** [DATA]
**Testador:** [NOME]
**Ambiente:** [Produção/Staging/Local]

## Resultados

| Teste | Status | Observações |
|-------|--------|-------------|
| Cross-Browser (mesmo PC) | ✅/❌ | |
| Cross-Computer | ✅/❌ | |
| Múltiplos Envios | ✅/❌ | |
| Atualização Tempo Real | ✅/❌ | |
| Precisão de Dados | ✅/❌ | |
| Performance | ✅/❌ | |

## Bugs Encontrados
- [Listar bugs, se houver]

## Recomendações
- [Sugestões de melhoria]

## Conclusão
✅ Aprovado / ❌ Reprovar / 🔄 Requer ajustes
```

---

## 🎉 Sucesso!

Se todos os testes passarem, o sistema está **100% funcional** e pronto para uso em produção! 🚀
