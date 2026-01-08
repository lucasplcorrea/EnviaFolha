# 🔇 Redução de Logs de Healthcheck - Implementação

**Data**: 08/01/2026  
**Objetivo**: Reduzir ruído nos logs do sistema, removendo logs repetitivos de polling

---

## 🎯 Problema Original

### **Logs Poluídos**:
```
172.23.0.4 - - [08/Jan/2026 12:38:28] "GET /api/v1/queue/active HTTP/1.1" 200 -
172.23.0.4 - - [08/Jan/2026 12:38:28] "GET /api/v1/database/health HTTP/1.1" 200 -
172.23.0.4 - - [08/Jan/2026 12:38:28] "GET /api/v1/payrolls/bulk-send/dd172bde.../status HTTP/1.1" 200 -
📋 Carregando filas ativas...
172.23.0.4 - - [08/Jan/2026 12:38:30] "GET /api/v1/payrolls/bulk-send/dd172bde.../status HTTP/1.1" 200 -
172.23.0.4 - - [08/Jan/2026 12:38:32] "GET /api/v1/payrolls/bulk-send/dd172bde.../status HTTP/1.1" 200 -
📋 Carregando filas ativas...
172.23.0.4 - - [08/Jan/2026 12:38:33] "GET /api/v1/queue/active HTTP/1.1" 200 -
```

**Causa**: Frontend React faz polling automático para atualizar UI em tempo real:
- `/api/v1/database/health` - A cada 5 segundos
- `/api/v1/queue/active` - A cada 3 segundos
- `/api/v1/payrolls/bulk-send/{id}/status` - A cada 2 segundos
- `/api/v1/evolution/instances` - A cada 5 segundos

---

## ✅ Solução Implementada

### **1. Filtro de Logging no Handler HTTP**
**Arquivo**: [backend/main_legacy.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\main_legacy.py#L1282-L1310)

```python
class EnviaFolhaHandler(http.server.SimpleHTTPRequestHandler):
    
    # Rotas silenciosas (não aparecerão nos logs)
    SILENT_ROUTES = [
        '/api/v1/database/health',      # Healthcheck do banco
        '/api/v1/queue/active',          # Polling de filas
        '/api/v1/payrolls/bulk-send/',   # Status de jobs
        '/api/v1/evolution/instances',   # Status WhatsApp
        '/favicon.ico',                   # Favicon do navegador
    ]
    
    def log_message(self, format, *args):
        """Filtra rotas de healthcheck/polling"""
        # Verificar se é uma rota silenciosa
        for route in self.SILENT_ROUTES:
            if route in self.path:
                return  # Não logar esta requisição
        
        # Logar normalmente para rotas importantes
        super().log_message(format, *args)
```

**Benefícios**:
- ✅ Remove logs de requisições HTTP de polling
- ✅ Mantém logs de requisições importantes (POST, PUT, DELETE)
- ✅ Simples e eficiente (verificação em memória)

---

### **2. Remoção de Logs Redundantes**
**Arquivo**: [backend/main_legacy.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\main_legacy.py#L4713)

**Antes** ❌:
```python
def handle_get_active_queues(self):
    print("📋 Carregando filas ativas...")  # A cada 3 segundos!
    # ...
```

**Depois** ✅:
```python
def handle_get_active_queues(self):
    # Removido log repetitivo - rota é chamada a cada 3 segundos
    # ...
```

---

### **3. Configuração de Logging Silencioso (Opcional)**
**Arquivo**: [backend/app/core/logging_config.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\app\core\logging_config.py) (NOVO)

Filtro adicional para o sistema de logging do Python:
```python
class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        for route in SILENT_ROUTES:
            if route in message:
                return False  # Silenciar
        return True
```

Ativado automaticamente no startup do [main_legacy.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\main_legacy.py#L5258-L5263).

---

## 📊 Logs Antes vs Depois

### **ANTES** (Poluído):
```
172.23.0.4 - - [08/Jan/2026 12:38:28] "GET /api/v1/queue/active HTTP/1.1" 200 -
172.23.0.4 - - [08/Jan/2026 12:38:28] "GET /api/v1/database/health HTTP/1.1" 200 -
📋 Carregando filas ativas...
172.23.0.4 - - [08/Jan/2026 12:38:30] "GET /api/v1/payrolls/bulk-send/.../status HTTP/1.1" 200 -
172.23.0.4 - - [08/Jan/2026 12:38:32] "GET /api/v1/payrolls/bulk-send/.../status HTTP/1.1" 200 -
📋 Carregando filas ativas...
172.23.0.4 - - [08/Jan/2026 12:38:33] "GET /api/v1/queue/active HTTP/1.1" 200 -
🔥 POST recebido: /api/v1/payrolls/bulk-send
172.23.0.4 - - [08/Jan/2026 12:38:34] "POST /api/v1/payrolls/bulk-send HTTP/1.1" 202 -
172.23.0.4 - - [08/Jan/2026 12:38:35] "GET /api/v1/database/health HTTP/1.1" 200 -
```

### **DEPOIS** (Limpo):
```
🔥 POST recebido: /api/v1/payrolls/bulk-send
172.23.0.4 - - [08/Jan/2026 12:38:34] "POST /api/v1/payrolls/bulk-send HTTP/1.1" 202 -
📨 Iniciando envio em lote de holerites...
🆔 Job criado: dd172bde-0a1c-401f-8cb5-fa634123de08
🚀 [JOB dd172bde] Thread iniciada - processando 3 arquivos...
```

**Redução**: ~90% de logs HTTP removidos! 🎉

---

## 🔧 Arquivos Modificados

| Arquivo | Modificação | Linhas |
|---------|-------------|--------|
| [backend/main_legacy.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\main_legacy.py#L1282-L1310) | Adicionado filtro `log_message()` | 1282-1310 |
| [backend/main_legacy.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\main_legacy.py#L4713) | Removido log "Carregando filas..." | 4713 |
| [backend/main_legacy.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\main_legacy.py#L5258-L5263) | Import filtro de logging | 5258-5263 |
| [backend/app/core/logging_config.py](c:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\backend\app\core\logging_config.py) | **NOVO** - Filtro de logging | - |

---

## 🎛️ Controle de Verbosidade

### **Modo Silencioso (Padrão)**:
```python
# Ativado automaticamente no startup
from app.core.logging_config import setup_quiet_logging
setup_quiet_logging()
```

### **Modo Verbose (Debug)**:
```python
# Para ativar todos os logs (útil para debug)
from app.core.logging_config import setup_verbose_logging
setup_verbose_logging()
```

Ou defina variável de ambiente:
```bash
export VERBOSE_LOGGING=true
```

---

## ✅ Validação

Após deploy, verificar:

- [ ] Logs HTTP de healthcheck não aparecem mais
- [ ] Logs de POST/PUT/DELETE ainda aparecem normalmente
- [ ] "📋 Carregando filas ativas..." não aparece a cada 3s
- [ ] Logs de jobs (🚀, 📄, ✅) continuam funcionando
- [ ] Sistema responde normalmente às requisições de polling

---

## 🚀 Deploy

```powershell
.\build-and-deploy.ps1
```

Após deploy, logs ficam ~90% mais limpos e focados em operações importantes! 🎯
