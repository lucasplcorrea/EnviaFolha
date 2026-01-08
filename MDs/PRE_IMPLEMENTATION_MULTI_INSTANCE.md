# 🔍 Análise Pré-Implementação: Sistema Multi-Instância WhatsApp + Email

**Data:** 19 de dezembro de 2025  
**Objetivo:** Preparar sistema para múltiplas instâncias WhatsApp e envio por email  
**Abordagem:** Análise completa antes de qualquer alteração

---

## 📊 ANÁLISE DO CÓDIGO ATUAL

### 1. Arquitetura Atual de Instância WhatsApp

#### 1.1 Configuração (backend/app/core/config.py)
```python
class Settings(BaseSettings):
    # CONFIGURAÇÃO ATUAL - INSTÂNCIA ÚNICA
    EVOLUTION_SERVER_URL: Optional[str] = None
    EVOLUTION_API_KEY: Optional[str] = None
    EVOLUTION_INSTANCE_NAME: Optional[str] = None  # ← ÚNICA INSTÂNCIA
```

**Status:** ✅ Configuração simples e funcional  
**Limitação:** Suporta apenas 1 instância

#### 1.2 Serviço Evolution API (backend/app/services/evolution_api.py)
```python
class EvolutionAPIService:
    def __init__(self):
        self.server_url = settings.EVOLUTION_SERVER_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance_name = settings.EVOLUTION_INSTANCE_NAME  # ← HARDCODED
        
    # Todos os métodos usam self.instance_name
    async def check_instance_status(self):
        url = f"{self.server_url}/instance/connectionState/{self.instance_name}"
```

**Status:** ⚠️ Instância hardcoded no construtor  
**Impacto:** Precisa ser refatorado para aceitar instância como parâmetro

#### 1.3 Uso do Serviço (múltiplos locais)

**Locais de instanciação:**
- `backend/main_legacy.py` linha 675, 3429, 3851
- `backend/app/routes/dashboard.py` linha 37
- `backend/app/routes/system.py` linha 124

**Padrão atual:**
```python
evolution_service = EvolutionAPIService()  # Sempre usa settings.EVOLUTION_INSTANCE_NAME
```

**Status:** ✅ Centralizado mas inflexível  
**Impacto:** Todas as instanciações precisam ser atualizadas

---

### 2. Fluxo de Envio de Holerites

#### 2.1 Função Principal (backend/main_legacy.py)
```python
def process_bulk_send_in_background(job_id, selected_files, message_templates, user_id):
    # Linha 675
    from app.services.evolution_api import EvolutionAPIService
    evolution_service = EvolutionAPIService()
    
    # Linha 700-800: DELAY SYSTEM
    if idx > 0:
        if idx % 20 == 0:
            long_delay = random.uniform(600.00, 900.00)  # 10-15min
        else:
            delay = random.uniform(120.00, 180.00)  # 2-3min
        time.sleep(delay)
    
    # Linha 913: ENVIO
    result = loop.run_until_complete(
        evolution_service.send_payroll_message(...)
    )
```

**Status:** ⚠️ Usa uma única instância durante todo o loop  
**Oportunidade:** Implementar round-robin AQUI

#### 2.2 Sistema de Delays
```python
# DELAY ATUAL (aplicado globalmente)
delay = random.uniform(120.00, 180.00)  # 2-3 minutos
time.sleep(delay)  # ← BLOQUEIA A THREAD
```

**Status:** ❌ Delay bloqueia toda a execução  
**Problema:** Não permite paralelização entre instâncias

---

### 3. Frontend - Monitoramento (frontend/src/pages/SystemInfo.jsx)

#### 3.1 Status Atual
```jsx
{/* Status da Evolution API */}
<div className="bg-white p-6 rounded-lg shadow-sm border">
  <h3 className="text-lg font-semibold">WhatsApp API</h3>
  <div>
    <span>Status:</span>
    <span>{systemStatus.evolution.connected ? 'Conectado' : 'Desconectado'}</span>
  </div>
  <div>
    <span>Instância:</span>
    <span>{systemStatus.evolution.instance}</span>  {/* ← ÚNICA INSTÂNCIA */}
  </div>
</div>
```

**Status:** ✅ Funcional mas limitado a 1 instância  
**Necessidade:** Replicar card para cada instância

#### 3.2 API de Status (backend/app/routes/system.py)
```python
def handle_evolution_status(self):
    """GET /api/v1/evolution/status"""
    instance_name = os.getenv('EVOLUTION_INSTANCE_NAME')  # ← ÚNICA
    evolution_service = EvolutionAPIService()
    is_connected = loop.run_until_complete(evolution_service.check_instance_status())
    
    self.send_json_response({
        "status": "connected" if is_connected else "disconnected",
        "instance_name": instance_name,  # ← RETORNA APENAS 1
        ...
    })
```

**Status:** ⚠️ Endpoint retorna apenas 1 instância  
**Necessidade:** Novo endpoint que retorna array de instâncias

---

### 4. Banco de Dados

#### 4.1 Tabelas Relevantes
```sql
-- employees: tabela de colaboradores
-- payroll_sends: registros de envios de holerites
-- send_queues: filas de envio (já implementado)
-- send_queue_items: itens das filas
```

**Status:** ✅ Estrutura suporta múltiplas instâncias (sem alteração necessária)

**Observação:** Não há campo `instance_name` nas tabelas, mas pode ser adicionado em `queue_metadata` (JSONB)

---

## 🎯 PROPOSTA DE IMPLEMENTAÇÃO

### Fase 1: Configuração Multi-Instância (SEM ALTERAR LÓGICA DE ENVIO)

#### 1.1 Variáveis de Ambiente (.env)
```env
# CONFIGURAÇÃO ATUAL (manter por compatibilidade)
EVOLUTION_SERVER_URL=https://api.evolution.com
EVOLUTION_API_KEY=sua_chave_api

# NOVA CONFIGURAÇÃO - MÚLTIPLAS INSTÂNCIAS
EVOLUTION_INSTANCES=instancia1,instancia2,instancia3

# OU FORMATO DETALHADO (JSON)
EVOLUTION_INSTANCES_JSON=[
  {"name": "instancia1", "phone": "+5511999990001"},
  {"name": "instancia2", "phone": "+5511999990002"},
  {"name": "instancia3", "phone": "+5511999990003"}
]

# EMAIL CONFIGURATION (para futuro)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
SMTP_FROM=RH Nexo <rh@nexo.com>
```

#### 1.2 Settings Class (backend/app/core/config.py)
```python
class Settings(BaseSettings):
    # Configurações existentes...
    
    # NOVA: Múltiplas instâncias WhatsApp
    EVOLUTION_INSTANCES: Optional[str] = None  # CSV: "inst1,inst2,inst3"
    EVOLUTION_INSTANCES_JSON: Optional[str] = None  # JSON detalhado
    
    # NOVA: Email SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = "Sistema RH <rh@empresa.com>"
    SMTP_USE_TLS: bool = True
    
    # Métodos auxiliares
    def get_evolution_instances(self) -> List[str]:
        """Retorna lista de instâncias WhatsApp"""
        if self.EVOLUTION_INSTANCES_JSON:
            try:
                return json.loads(self.EVOLUTION_INSTANCES_JSON)
            except:
                pass
        
        if self.EVOLUTION_INSTANCES:
            return [inst.strip() for inst in self.EVOLUTION_INSTANCES.split(',')]
        
        # Fallback: instância única (compatibilidade)
        if self.EVOLUTION_INSTANCE_NAME:
            return [{"name": self.EVOLUTION_INSTANCE_NAME, "phone": None}]
        
        return []
    
    def has_email_configured(self) -> bool:
        """Verifica se SMTP está configurado"""
        return all([
            self.SMTP_HOST,
            self.SMTP_USER,
            self.SMTP_PASSWORD
        ])
```

#### 1.3 Evolution API Service Refatorado
```python
class EvolutionAPIService:
    def __init__(self, instance_name: str = None):
        """
        Inicializa serviço para uma instância específica
        
        Args:
            instance_name: Nome da instância. Se None, usa settings.EVOLUTION_INSTANCE_NAME
        """
        self.server_url = settings.EVOLUTION_SERVER_URL.rstrip('/') if settings.EVOLUTION_SERVER_URL else None
        self.api_key = settings.EVOLUTION_API_KEY
        
        # MUDANÇA PRINCIPAL: instância como parâmetro
        self.instance_name = instance_name or settings.EVOLUTION_INSTANCE_NAME
        
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        } if self.api_key else None
        
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.warning(f"Configurações da Evolution API incompletas para instância {self.instance_name}")
    
    # Todos os métodos permanecem iguais (usam self.instance_name)
```

**Vantagens:**
- ✅ Backward compatible (se não passar instance_name, usa settings)
- ✅ Permite criar múltiplos serviços: `EvolutionAPIService("inst1")`, `EvolutionAPIService("inst2")`
- ✅ Código existente continua funcionando

#### 1.4 Gerenciador de Instâncias (NOVO SERVIÇO)
```python
# backend/app/services/instance_manager.py
class InstanceManager:
    """Gerencia múltiplas instâncias WhatsApp com round-robin"""
    
    def __init__(self):
        self.instances = settings.get_evolution_instances()
        self.current_index = 0
        self.last_send_time = {}  # {instance_name: timestamp}
        self.lock = threading.Lock()
    
    def get_next_instance(self) -> str:
        """Retorna próxima instância disponível (round-robin)"""
        with self.lock:
            if not self.instances:
                return settings.EVOLUTION_INSTANCE_NAME  # Fallback
            
            instance_data = self.instances[self.current_index]
            instance_name = instance_data if isinstance(instance_data, str) else instance_data.get('name')
            
            # Avançar para próxima
            self.current_index = (self.current_index + 1) % len(self.instances)
            
            return instance_name
    
    def get_instance_delay(self, instance_name: str) -> float:
        """Retorna tempo desde último envio nesta instância"""
        last_time = self.last_send_time.get(instance_name, 0)
        return time.time() - last_time
    
    def should_wait(self, instance_name: str, min_delay: float = 300) -> bool:
        """Verifica se deve aguardar antes de usar esta instância"""
        delay = self.get_instance_delay(instance_name)
        return delay < min_delay
    
    def register_send(self, instance_name: str):
        """Registra que um envio foi realizado nesta instância"""
        with self.lock:
            self.last_send_time[instance_name] = time.time()
    
    async def check_all_instances_status(self) -> Dict[str, bool]:
        """Verifica status de todas as instâncias"""
        status = {}
        for inst_data in self.instances:
            inst_name = inst_data if isinstance(inst_data, str) else inst_data.get('name')
            try:
                service = EvolutionAPIService(inst_name)
                is_online = await service.check_instance_status()
                status[inst_name] = is_online
            except Exception as e:
                logger.error(f"Erro ao verificar instância {inst_name}: {e}")
                status[inst_name] = False
        return status
```

#### 1.5 Novo Endpoint de Status (backend/app/routes/system.py)
```python
def handle_evolution_instances_status(self):
    """
    GET /api/v1/evolution/instances
    Retorna status de TODAS as instâncias configuradas
    """
    try:
        from app.services.instance_manager import InstanceManager
        import asyncio
        
        manager = InstanceManager()
        
        # Criar event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Verificar todas as instâncias
        status_dict = loop.run_until_complete(
            asyncio.wait_for(
                manager.check_all_instances_status(),
                timeout=10.0
            )
        )
        
        # Formatar resposta
        instances = []
        for inst_data in settings.get_evolution_instances():
            inst_name = inst_data if isinstance(inst_data, str) else inst_data.get('name')
            inst_phone = inst_data.get('phone') if isinstance(inst_data, dict) else None
            
            instances.append({
                "name": inst_name,
                "phone": inst_phone,
                "status": "connected" if status_dict.get(inst_name, False) else "disconnected",
                "last_check": datetime.now().isoformat()
            })
        
        self.send_json_response({
            "instances": instances,
            "total": len(instances),
            "connected": sum(1 for inst in instances if inst["status"] == "connected"),
            "server_url": settings.EVOLUTION_SERVER_URL
        })
        
    except Exception as e:
        print(f"❌ Erro ao verificar instâncias: {e}")
        self.send_json_response({"error": str(e)}, 500)
```

#### 1.6 Frontend - Múltiplos Cards (frontend/src/pages/SystemInfo.jsx)
```jsx
// ANTES: Card único
<div className="bg-white p-6 rounded-lg shadow-sm border">
  <h3>WhatsApp API</h3>
  <span>Instância: {systemStatus.evolution.instance}</span>
</div>

// DEPOIS: Cards dinâmicos
{systemStatus.evolution.instances && systemStatus.evolution.instances.length > 0 ? (
  systemStatus.evolution.instances.map((instance, index) => (
    <div key={index} className="bg-white p-6 rounded-lg shadow-sm border">
      <div className="flex items-center gap-2 mb-4">
        {instance.status === 'connected' ? (
          <span className="text-green-500">🟢</span>
        ) : (
          <span className="text-red-500">🔴</span>
        )}
        <h3 className="text-lg font-semibold">WhatsApp API #{index + 1}</h3>
      </div>
      <div className="space-y-2 text-sm">
        <div>
          <span className="font-medium">Status:</span>
          <span className={`ml-2 ${instance.status === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
            {instance.status === 'connected' ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
        <div>
          <span className="font-medium">Instância:</span>
          <span className="ml-2">{instance.name}</span>
        </div>
        {instance.phone && (
          <div>
            <span className="font-medium">Número:</span>
            <span className="ml-2">{instance.phone}</span>
          </div>
        )}
      </div>
    </div>
  ))
) : (
  /* Fallback: card único para compatibilidade */
  <div>...</div>
)}
```

---

## ⚠️ PONTOS CRÍTICOS IDENTIFICADOS

### 1. **Compatibilidade com Código Existente**
**Risco:** Quebrar funcionalidades atuais  
**Mitigação:**
- ✅ `EvolutionAPIService(None)` usa instância padrão (fallback)
- ✅ Manter variáveis antigas (`EVOLUTION_INSTANCE_NAME`)
- ✅ Testar todos os fluxos existentes antes de deploy

### 2. **Delays Bloqueantes**
**Problema:** `time.sleep()` bloqueia a thread  
**Impacto:** Não permite envio paralelo entre instâncias  
**Solução (FASE 2):**
- Implementar sistema de delays por instância
- Usar filas assíncronas
- **NÃO IMPLEMENTAR AGORA** (escopo desta fase é apenas preparar infraestrutura)

### 3. **Concorrência no Gerenciador de Instâncias**
**Risco:** Race conditions ao selecionar instância  
**Mitigação:**
- ✅ Usar `threading.Lock()` no `InstanceManager`
- ✅ Testar com múltiplas threads simultâneas

### 4. **Migração de Banco de Dados**
**Necessidade:** Nenhuma alteração de schema necessária  
**Observação:** `queue_metadata` (JSONB) pode armazenar `instance_name`

### 5. **Validação de Email**
**Necessidade:** Novo campo em `employees` para armazenar email  
**Escopo:** Adicionar coluna `email` (nullable)  
**Implementar:** Validação básica no frontend (Settings)

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO - FASE 1

### Backend

- [ ] **1.1** Atualizar `Settings` class com novas configs
- [ ] **1.2** Adicionar métodos `get_evolution_instances()` e `has_email_configured()`
- [ ] **1.3** Refatorar `EvolutionAPIService.__init__()` para aceitar `instance_name`
- [ ] **1.4** Criar `InstanceManager` service
- [ ] **1.5** Criar endpoint `GET /api/v1/evolution/instances`
- [ ] **1.6** Atualizar todas as chamadas de `EvolutionAPIService()` (opcional, usar fallback)
- [ ] **1.7** Adicionar coluna `email` na tabela `employees` (migration)
- [ ] **1.8** Criar `EmailService` (esqueleto, sem implementação de envio)

### Frontend

- [ ] **2.1** Atualizar `SystemInfo.jsx` para exibir múltiplos cards
- [ ] **2.2** Criar função para buscar `/api/v1/evolution/instances`
- [ ] **2.3** Adicionar validação de email em formulários (Settings/Employees)
- [ ] **2.4** Adicionar campo "Email" no cadastro de colaborador

### Testes

- [ ] **3.1** Testar instância única (compatibilidade)
- [ ] **3.2** Testar múltiplas instâncias (2-3)
- [ ] **3.3** Testar endpoint de status
- [ ] **3.4** Verificar frontend com 0, 1, 2, 3 instâncias
- [ ] **3.5** Testar importação de colaboradores com email

### Documentação

- [ ] **4.1** Atualizar README com novas variáveis .env
- [ ] **4.2** Documentar formato de EVOLUTION_INSTANCES_JSON
- [ ] **4.3** Criar guia de migração (1 → múltiplas instâncias)

---

## 🧪 PLANO DE TESTES LOCAIS

### Ambiente de Teste

```bash
# 1. Restaurar backup do banco
docker-compose -f docker-compose.postgres.yml up -d
docker exec -i postgres_container psql -U enviafolha_user -d enviafolha_db < backup.sql

# 2. Configurar .env.test com 3 instâncias
EVOLUTION_INSTANCES=instancia1,instancia2,instancia3

# 3. Rodar backend local
cd backend
python main.py

# 4. Rodar frontend local
cd frontend
npm start
```

### Casos de Teste

#### Teste 1: Compatibilidade (Instância Única)
```env
# .env (configuração antiga)
EVOLUTION_INSTANCE_NAME=instancia1
```
**Esperado:** Sistema funciona normalmente

#### Teste 2: Múltiplas Instâncias (CSV)
```env
EVOLUTION_INSTANCES=inst1,inst2,inst3
```
**Esperado:**
- Frontend mostra 3 cards
- Endpoint `/api/v1/evolution/instances` retorna array com 3 itens
- Round-robin funciona

#### Teste 3: Múltiplas Instâncias (JSON)
```env
EVOLUTION_INSTANCES_JSON=[{"name":"inst1","phone":"+5511999990001"},{"name":"inst2","phone":"+5511999990002"}]
```
**Esperado:**
- Frontend mostra 2 cards com números
- Status individual de cada instância

#### Teste 4: Sem Instâncias Configuradas
```env
# .env vazio (sem EVOLUTION_*)
```
**Esperado:**
- Sistema não quebra
- Frontend mostra "não configurado"
- Envios falham gracefully

#### Teste 5: Email (Validação)
```
1. Acessar cadastro de colaborador
2. Adicionar email: teste@empresa.com
3. Salvar
4. Verificar validação básica (formato de email)
```

---

## 🚀 CRONOGRAMA ESTIMADO

### Fase 1: Infraestrutura (3-4 dias)
- Dia 1: Backend (settings, services, endpoints)
- Dia 2: Frontend (múltiplos cards, validação email)
- Dia 3: Testes locais com banco restaurado
- Dia 4: Ajustes e documentação

### Fase 2: Lógica de Envio (NÃO INCLUÍDA NESTE ESCOPO)
- Implementar round-robin no `process_bulk_send_in_background`
- Sistema de delays por instância
- Envio paralelo (threads/async)
- Monitoramento de carga por instância

### Fase 3: Email (FUTURO)
- Implementar `EmailService`
- Integração com SMTP
- Fallback WhatsApp → Email
- Preferências de canal por colaborador

---

## 💾 BACKUP E ROLLBACK

### Antes de Implementar

```bash
# 1. Backup do código
git checkout -b backup/pre-multi-instance
git push origin backup/pre-multi-instance

# 2. Backup do banco (já feito pelo usuário)
# docker exec postgres pg_dump -U user db > backup_20251219.sql

# 3. Backup de .env
cp backend/.env backend/.env.backup
```

### Estratégia de Rollback

```bash
# Se algo der errado:
git checkout main
git reset --hard backup/pre-multi-instance

# Restaurar banco
docker exec -i postgres psql -U user -d db < backup_20251219.sql
```

---

## ✅ PRÓXIMOS PASSOS

1. **Revisar este documento** com o usuário
2. **Validar abordagem** e escopos de cada fase
3. **Confirmar testes locais** (banco restaurado disponível)
4. **Iniciar implementação** Fase 1 (infraestrutura apenas)
5. **NÃO ALTERAR** lógica de envio nesta fase

---

## 📝 NOTAS IMPORTANTES

- ⚠️ **NÃO mexer em lógica de envio** nesta fase
- ✅ **Manter compatibilidade** com configuração antiga
- 🧪 **Testar localmente** antes de build/push
- 📦 **Backup completo** antes de qualquer alteração
- 🔄 **Implementação incremental** (phase-by-phase)

**Aguardando aprovação para iniciar Fase 1...**
