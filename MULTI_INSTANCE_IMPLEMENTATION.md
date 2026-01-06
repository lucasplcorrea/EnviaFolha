# Multi-Instance Implementation Summary

## Implementação Concluída - Backend e Frontend

### Data: 2024
### Status: ✅ Backend Completo | ✅ Frontend Completo

---

## 1. Arquivos Modificados

### Backend

#### `backend/app/core/config.py` (MODIFICADO)
**Alterações:**
- Adicionadas variáveis `EVOLUTION_INSTANCE_NAME2` e `EVOLUTION_INSTANCE_NAME3` (Optional[str])
- Adicionadas variáveis SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`
- Novo método `get_evolution_instances()`: Retorna lista com 1-3 instâncias configuradas
- Novo método `has_smtp_configured()`: Valida se SMTP está completamente configurado

**Código:**
```python
EVOLUTION_INSTANCE_NAME2: Optional[str] = None
EVOLUTION_INSTANCE_NAME3: Optional[str] = None

SMTP_HOST: Optional[str] = None
SMTP_PORT: Optional[int] = 587
SMTP_USER: Optional[str] = None
SMTP_PASSWORD: Optional[str] = None
SMTP_FROM: Optional[str] = None
SMTP_USE_TLS: bool = True

def get_evolution_instances(self) -> List[str]:
    instances = [self.EVOLUTION_INSTANCE_NAME]
    if self.EVOLUTION_INSTANCE_NAME2:
        instances.append(self.EVOLUTION_INSTANCE_NAME2)
    if self.EVOLUTION_INSTANCE_NAME3:
        instances.append(self.EVOLUTION_INSTANCE_NAME3)
    return instances
```

---

#### `backend/app/services/evolution_api.py` (MODIFICADO)
**Alterações:**
- Refatorado `__init__(self)` para `__init__(self, instance_name: str = None)`
- Permite instanciar serviço com instância específica
- Mantém compatibilidade retroativa (se None, usa instância padrão)

**Código:**
```python
def __init__(self, instance_name: str = None):
    self.settings = get_settings()
    self.server_url = self.settings.EVOLUTION_SERVER_URL
    self.api_key = self.settings.EVOLUTION_API_KEY
    self.instance_name = instance_name or self.settings.EVOLUTION_INSTANCE_NAME
```

**Uso:**
```python
# Forma antiga (ainda funciona)
service = EvolutionAPIService()

# Forma nova (multi-instância)
service = EvolutionAPIService("RH-Segunda")
```

---

#### `backend/app/services/instance_manager.py` (NOVO ARQUIVO)
**Descrição:** Gerenciador de múltiplas instâncias com round-robin e controle de delays.

**Funcionalidades:**
- Round-robin automático entre 1-3 instâncias
- Tracking de delays por instância (thread-safe)
- Verificação de status assíncrona de todas as instâncias
- Singleton pattern para gerenciamento centralizado

**Métodos Principais:**
```python
def get_next_instance() -> str:
    """Retorna próxima instância no round-robin"""

def should_wait(instance: str, min_delay: int = 300) -> bool:
    """Verifica se instância precisa aguardar delay mínimo"""

def register_send(instance: str):
    """Registra timestamp de envio para instância"""

def get_instance_stats() -> Dict:
    """Retorna estatísticas de todas as instâncias"""

async def check_all_instances_status() -> List[Dict]:
    """Verifica status de todas as instâncias (assíncrono)"""
```

**Exemplo de Uso:**
```python
from app.services.instance_manager import get_instance_manager

manager = get_instance_manager()
next_instance = manager.get_next_instance()
service = EvolutionAPIService(next_instance)

# Após envio
manager.register_send(next_instance)
```

---

#### `backend/app/routes/system.py` (MODIFICADO)
**Alterações:**
- Adicionado método `handle_evolution_instances_status()`
- Novo endpoint para verificar status de todas as instâncias
- Timeout de 10 segundos por instância
- Retorna JSON com array de instâncias e estatísticas

**Endpoint:** `GET /api/v1/evolution/instances`

**Response Format:**
```json
{
  "instances": [
    {
      "name": "RH-Abecker",
      "status": "connected",
      "ready": true,
      "seconds_since_last_send": null
    },
    {
      "name": "RH-Segunda",
      "status": "disconnected",
      "ready": true,
      "seconds_since_last_send": 350.5
    }
  ],
  "total": 2,
  "connected": 1,
  "has_multiple": true
}
```

**Status Possíveis:**
- `"connected"`: Instância online e conectada
- `"disconnected"`: Instância offline ou erro
- `"timeout"`: Timeout de 10 segundos excedido

---

#### `backend/main_legacy.py` (MODIFICADO)
**Alterações:**
- Adicionada rota `/api/v1/evolution/instances`
- Mapeada para `SystemRouter().handle_evolution_instances_status()`
- Posicionada junto com outras rotas do Evolution

**Código:**
```python
self.app.add_route(
    '/api/v1/evolution/instances',
    SystemRouter().handle_evolution_instances_status,
    methods=['GET']
)
```

---

#### `backend/.env.example` (NOVO ARQUIVO)
**Descrição:** Template de configuração com novas variáveis documentadas.

**Seções Principais:**
- Database Configuration
- JWT Authentication
- Evolution API (1-3 instâncias)
- Email Configuration (SMTP)
- File Upload Configuration
- Server Configuration
- CORS Configuration

**Exemplo Multi-Instância:**
```env
# Primary Instance (Required)
EVOLUTION_INSTANCE_NAME=RH-Abecker

# Additional Instances (Optional)
EVOLUTION_INSTANCE_NAME2=RH-Segunda
EVOLUTION_INSTANCE_NAME3=RH-Terceira
```

---

### Frontend

#### `frontend/src/pages/SystemInfo.jsx` (MODIFICADO)
**Alterações:**
1. Estado atualizado para suportar múltiplas instâncias
2. Novo endpoint `/api/v1/evolution/instances` (substituiu `/api/v1/evolution/status`)
3. Loop dinâmico para renderizar 1-3 cards de WhatsApp
4. Função `formatTimeSinceLastSend()` para exibir tempo desde último envio
5. Card de resumo quando `has_multiple === true`

**Estado Anterior:**
```javascript
evolution: { status: 'checking', connected: false, instance: '' }
```

**Estado Novo:**
```javascript
evolution: { 
  instances: [], 
  total: 0, 
  connected: 0, 
  has_multiple: false 
}
```

**Renderização Dinâmica:**
```jsx
{systemStatus.evolution.instances.map((instance, index) => (
  <div key={instance.name} className="bg-white p-6 rounded-lg shadow-sm border">
    <h3>WhatsApp {has_multiple ? `#${index + 1}` : ''}</h3>
    <div>Status: {instance.status}</div>
    <div>Instância: {instance.name}</div>
    <div>Pronta: {instance.ready ? 'Sim' : 'Aguardando'}</div>
    <div>Último envio: {formatTimeSinceLastSend(instance.seconds_since_last_send)}</div>
  </div>
))}
```

**Card de Resumo Multi-Instâncias:**
- Exibido apenas quando `has_multiple === true`
- Mostra: Total de instâncias, Conectadas, Desconectadas
- Explicação sobre round-robin para evitar softban

---

## 2. Fluxo de Funcionamento

### 2.1 Round-Robin Distribution

```
┌─────────────────────────────────────────────────────┐
│           INSTANCE MANAGER (Singleton)              │
│                                                     │
│  Current Index: 0                                   │
│  Instances: ["RH-Abecker", "RH-Segunda"]          │
│  Last Send Times: {                                │
│    "RH-Abecker": 1735000000.0,                    │
│    "RH-Segunda": None                             │
│  }                                                  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  get_next_instance()         │
         │  Returns: "RH-Abecker"       │
         │  Increments index to 1       │
         └──────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  EvolutionAPIService         │
         │  (instance: "RH-Abecker")    │
         └──────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  Send Message                │
         └──────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  register_send()             │
         │  Updates timestamp           │
         └──────────────────────────────┘
```

### 2.2 Delay Checking

```python
# Antes de enviar
manager = get_instance_manager()
instance = manager.get_next_instance()

if manager.should_wait(instance, min_delay=300):
    wait_time = 300 - manager.get_instance_delay(instance)
    await asyncio.sleep(wait_time)

# Enviar mensagem
service = EvolutionAPIService(instance)
await service.send_document(...)

# Registrar envio
manager.register_send(instance)
```

---

## 3. Configuração de Ambiente

### 3.1 Instância Única (Padrão)
```env
EVOLUTION_INSTANCE_NAME=RH-Abecker
```

### 3.2 Multi-Instância (Anti-Softban)
```env
EVOLUTION_INSTANCE_NAME=RH-Abecker
EVOLUTION_INSTANCE_NAME2=RH-Segunda
EVOLUTION_INSTANCE_NAME3=RH-Terceira
```

### 3.3 Email (Futuro)
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=rh@empresa.com
SMTP_PASSWORD=senha_app_google
SMTP_FROM=RH Nexo <rh@nexo.com.br>
SMTP_USE_TLS=true
```

---

## 4. Testes Recomendados

### 4.1 Backend

```bash
# 1. Verificar configuração
cd backend
python -c "from app.core.config import get_settings; print(get_settings().get_evolution_instances())"

# 2. Testar endpoint
curl http://localhost:8000/api/v1/evolution/instances

# 3. Testar round-robin
python -c "
from app.services.instance_manager import get_instance_manager
m = get_instance_manager()
print(f'1: {m.get_next_instance()}')
print(f'2: {m.get_next_instance()}')
print(f'3: {m.get_next_instance()}')
"
```

### 4.2 Frontend

```bash
# 1. Iniciar frontend
cd frontend
npm start

# 2. Acessar SystemInfo
# http://localhost:3000/system-info

# 3. Verificar:
# - Cards dinâmicos (1-3) baseado em instâncias
# - Status de cada instância (🟢/🔴/🟡)
# - Card de resumo (se has_multiple)
# - Tempo desde último envio formatado
```

---

## 5. Backward Compatibility

### ✅ Código antigo continua funcionando

**Antes:**
```python
service = EvolutionAPIService()
await service.send_document(...)
```

**Depois (sem mudanças necessárias):**
```python
service = EvolutionAPIService()  # Usa EVOLUTION_INSTANCE_NAME padrão
await service.send_document(...)
```

**Novo código (multi-instância):**
```python
manager = get_instance_manager()
instance = manager.get_next_instance()
service = EvolutionAPIService(instance)
await service.send_document(...)
manager.register_send(instance)
```

---

## 6. Próximos Passos

### Phase 2 (NÃO IMPLEMENTADO AINDA)
- [ ] Integrar InstanceManager no fluxo de envio em massa
- [ ] Implementar delays específicos por instância (5-10min)
- [ ] Adicionar delays aleatórios entre envios (30±10s)
- [ ] Envios paralelos em múltiplas instâncias
- [ ] Tratamento de falhas por instância

### Phase 3 (Futuro)
- [ ] Adicionar coluna `email` na tabela `employees`
- [ ] Validação de email no frontend
- [ ] Implementação de envio por email (SMTP)
- [ ] Fallback: WhatsApp → Email
- [ ] Dashboard de estatísticas por instância

---

## 7. Checklist de Deploy

### Backend
- [ ] Atualizar `.env` com 2-3 instâncias
- [ ] Verificar conectividade de todas as instâncias
- [ ] Testar endpoint `/api/v1/evolution/instances`
- [ ] Validar round-robin funciona corretamente
- [ ] Build Docker image: `docker build -t nexo-rh-backend:multi-instance .`
- [ ] Push para registry

### Frontend
- [ ] Build de produção: `npm run build`
- [ ] Testar SystemInfo com múltiplas instâncias
- [ ] Verificar responsividade (1-3 cards)
- [ ] Build Docker image: `docker build -t nexo-rh-frontend:multi-instance .`
- [ ] Push para registry

### Docker Compose
- [ ] Atualizar `docker-compose.yml` com novas ENV vars
- [ ] Testar stack completa: `docker-compose up --build`
- [ ] Validar persistência de delays (volume)
- [ ] Testar reinício de containers

---

## 8. Documentação Gerada

- ✅ `PRE_IMPLEMENTATION_MULTI_INSTANCE.md` - Análise prévia
- ✅ `MULTI_INSTANCE_IMPLEMENTATION.md` - Este documento
- ✅ `.env.example` - Template de configuração
- ⏳ `ROADMAP_MULTI_INSTANCE_EMAIL.md` - Roadmap futuro (email)

---

## 9. Contato e Suporte

Para dúvidas ou problemas:
1. Verificar logs do backend: `docker logs nexo-rh-backend`
2. Verificar logs do frontend: `docker logs nexo-rh-frontend`
3. Testar endpoint de status: `curl http://localhost:8000/api/v1/evolution/instances`
4. Revisar este documento para troubleshooting

---

**Implementado por:** GitHub Copilot (Claude Sonnet 4.5)  
**Data:** 2024  
**Status:** ✅ Backend Completo | ✅ Frontend Completo | ⏳ Integração de Envio (Phase 2)
