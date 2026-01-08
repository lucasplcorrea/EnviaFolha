# Implementação de Load Balancing para Múltiplas Instâncias WhatsApp

## 📅 Data: 08/01/2026

## 🎯 Problema Identificado

Ao enviar múltiplos holerites com 2+ instâncias WhatsApp ativas, **todos os envios** eram feitos pela **mesma instância/número**, causando:
- Sobrecarga em uma única instância
- Risco de softban/strike por volume
- Desperdício de capacidade das outras instâncias

## 🔍 Diagnóstico

### Código Anterior (main_legacy.py)

**Linha 687** - Inicialização do job:
```python
# ❌ PROBLEMA: Instância selecionada UMA VEZ no início do job
initial_instance = instance_manager.get_next_instance()  # Round-robin sem verificar status
evolution_service = EvolutionAPIService(instance_name=initial_instance)
```

**Resultado**: Mesmo com múltiplas instâncias configuradas, o `evolution_service` era criado **uma única vez** no início do job, então **TODOS** os envios usavam a mesma instância.

### Por que Não Estava Funcionando?

1. **`get_next_instance()`** apenas rotacionava o índice, mas **não verificava** se a instância estava online
2. **`evolution_service`** era reutilizado para todos os envios no loop
3. O código de retry/fallback **só trocava** instância em caso de **falha**, não por design

## ✅ Solução Implementada

### Mudanças no Processo de Envio de Holerites

**1. Removida inicialização única** (linha 684-687):
```python
# ✅ NOVO: Não criar evolution_service no início
instance_manager = InstanceManager()
evolution_service = None  # Será criado a cada envio
queue_service = QueueManagerService(db)
```

**2. Verificação inicial melhorada** (linha 690-709):
```python
# ✅ Verificar se há PELO MENOS 1 instância online
all_instances_status = loop.run_until_complete(instance_manager.check_all_instances_status())
online_count = sum(1 for is_online in all_instances_status.values() if is_online)

if online_count == 0:
    job.status = 'failed'
    job.error_message = 'Nenhuma instância WhatsApp está conectada'
    return

print(f"✅ [JOB {job_id[:8]}] {online_count} instância(s) online disponível(is)")
```

**3. Seleção de instância A CADA ENVIO** (linha 956-989):
```python
# 🔄 SELECIONAR PRÓXIMA INSTÂNCIA ONLINE (ROUND-ROBIN INTELIGENTE)
next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())

if not next_instance:
    print(f"❌ [JOB {job_id[:8]}] Nenhuma instância online disponível")
    # ... registrar falha e continuar
    continue

print(f"📱 [JOB {job_id[:8]}] Usando instância: {next_instance}")

# Criar serviço com a instância selecionada
evolution_service = EvolutionAPIService(instance_name=next_instance)

# ... enviar mensagem ...

# Registrar envio na instância (para tracking de delays)
instance_manager.register_send(next_instance)
```

**4. Código de retry removido**: 
- Sistema agora seleciona instância online de primeira
- Se falhar, próximo envio tentará outra instância naturalmente (round-robin)
- Mais simples e eficiente

### Mudanças no Processo de Envio de Comunicados

**Linha 3945-3982** - Mesma lógica aplicada:
```python
# 📱 SELECIONAR PRÓXIMA INSTÂNCIA ONLINE (ROUND-ROBIN)
from app.services.instance_manager import get_instance_manager

instance_manager = get_instance_manager()
next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())

if not next_instance:
    failed_employees.append({
        'id': emp_id,
        'name': employee.get('full_name'),
        'reason': 'Nenhuma instância WhatsApp online'
    })
    continue

print(f"📱 Usando instância: {next_instance}")
evolution_service = EvolutionAPIService(instance_name=next_instance)

# ... enviar ...

# Registrar envio
instance_manager.register_send(next_instance)
```

## 📊 Como Funciona Agora

### Fluxo de Envio

```
┌─────────────────────────────────────────────────┐
│  Início do Job de Envio de Holerites           │
│  - Verificar ≥1 instância online                │
│  - Criar instance_manager                       │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Loop: Para cada holerite a enviar              │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  🎯 get_next_available_instance()               │
│  1. Verificar status de todas as instâncias     │
│  2. Filtrar apenas as ONLINE                    │
│  3. Round-robin entre instâncias online         │
│  4. Retornar próxima instância disponível       │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Criar EvolutionAPIService(instance_name)       │
│  Enviar mensagem                                │
│  Registrar envio: register_send(instance)       │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Próximo holerite → NOVA INSTÂNCIA              │
└─────────────────────────────────────────────────┘
```

### Exemplo Prático

**Cenário**: 3 instâncias configuradas (Inst1, Inst2, Inst3), sendo Inst2 offline

**Envios**:
1. **Holerite #1** → `get_next_available_instance()` → Inst1 (online, índice 0)
2. **Holerite #2** → `get_next_available_instance()` → Inst3 (online, índice 2, pulou Inst2 offline)
3. **Holerite #3** → `get_next_available_instance()` → Inst1 (online, volta ao início)
4. **Holerite #4** → `get_next_available_instance()` → Inst3 (online)
5. ...

**Resultado**: Distribuição automática entre instâncias **ONLINE**, pulando as offline.

## 🔧 Classe InstanceManager

### Métodos Principais

**`get_next_available_instance()` (async)**:
- Verifica status de TODAS as instâncias
- Filtra apenas as online
- Aplica round-robin entre as online
- Retorna nome da instância ou `None` se todas offline

**`register_send(instance_name)`**:
- Registra timestamp do último envio
- Usado para tracking e delays entre envios

**`check_all_instances_status()` (async)**:
- Chama Evolution API para cada instância
- Retorna `Dict[instance_name, is_online]`

### Código Relevante (instance_manager.py)

```python
async def get_next_available_instance(self) -> Optional[str]:
    """
    Retorna próxima instância ONLINE disponível (round-robin inteligente)
    """
    if not self.instances:
        return None
    
    # Verificar status de todas
    all_status = await self.check_all_instances_status()
    online_instances = [inst for inst, is_online in all_status.items() if is_online]
    
    if not online_instances:
        logger.error("❌ TODAS as instâncias estão offline!")
        return None
    
    # Round-robin entre as online
    attempts = 0
    max_attempts = len(self.instances)
    
    while attempts < max_attempts:
        with self.lock:
            instance_name = self.instances[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.instances)
        
        if instance_name in online_instances:
            return instance_name
        
        attempts += 1
    
    return None  # Fallback
```

## 📦 Build e Deploy

### Imagem Docker Criada
```bash
docker build -f Dockerfile.prod \
  -t lucasplcorrea/nexo-rh-backend:20260108-153243 \
  -t lucasplcorrea/nexo-rh-backend:latest .

docker push lucasplcorrea/nexo-rh-backend:20260108-153243
docker push lucasplcorrea/nexo-rh-backend:latest
```

### Versões
- **Backend com Load Balancing**: `lucasplcorrea/nexo-rh-backend:20260108-153243`
- **Frontend (versão atual)**: `lucasplcorrea/nexo-rh-frontend:20260108-141804`
- **Backend com PDF Regex Fix (pendente)**: `lucasplcorrea/nexo-rh-backend:20260108-145442`

## ✅ Benefícios

1. **Distribuição Automática**: Envios balanceados entre todas as instâncias online
2. **Tolerância a Falhas**: Se uma instância cair, outras assumem automaticamente
3. **Redução de Risco**: Nenhuma instância sobrecarregada, menor chance de softban
4. **Escalabilidade**: Adicionar nova instância no `.env` = mais capacidade automática
5. **Simplicidade**: Código mais limpo, sem retry complexo

## 🧪 Como Testar

1. Configure 2+ instâncias no `.env`:
   ```env
   EVOLUTION_INSTANCE_NAME=nexo-rh-instance-1
   EVOLUTION_INSTANCE_NAME2=nexo-rh-instance-2
   EVOLUTION_INSTANCE_NAME3=nexo-rh-instance-3
   ```

2. Certifique-se que todas estão conectadas (tela de Configurações → Instâncias)

3. Envie 10+ holerites

4. Observe os logs do backend:
   ```bash
   docker logs -f <backend-container> | grep "Usando instância"
   ```

5. **Esperado**: Alternância entre instâncias:
   ```
   📱 [JOB abc12345] Usando instância: nexo-rh-instance-1
   📱 [JOB abc12345] Usando instância: nexo-rh-instance-2
   📱 [JOB abc12345] Usando instância: nexo-rh-instance-3
   📱 [JOB abc12345] Usando instância: nexo-rh-instance-1
   ...
   ```

## 📝 Notas Importantes

- **Delay entre envios** ainda funciona normalmente (47-73 segundos)
- **Limite diário** futuro será por instância (quando implementado)
- **Registro de envios** (`register_send`) prepara terreno para controle de rate limiting por instância
- **Verificação de status** é feita a cada envio (pode adicionar cache futuro se necessário)

## 🔮 Melhorias Futuras

1. **Cache de Status**: Evitar verificar status a cada envio (cache de 30s)
2. **Limite Diário por Instância**: Implementar `sends_today` com reset automático
3. **Prioridade**: Usar campo `priority` do modelo WhatsAppInstance
4. **Estatísticas**: Dashboard mostrando distribuição de envios por instância
5. **Alertas**: Notificar quando instância ficar offline

---

## 📚 Arquivos Modificados

- `backend/main_legacy.py` (linhas 684-1070, 3945-4010)

## 🔗 Relacionado

- [MULTI_INSTANCE_IMPLEMENTATION.md](MULTI_INSTANCE_IMPLEMENTATION.md)
- [instance_manager.py](backend/app/services/instance_manager.py)
- [evolution_api.py](backend/app/services/evolution_api.py)
