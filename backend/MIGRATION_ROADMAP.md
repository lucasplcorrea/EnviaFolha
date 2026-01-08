# 🗺️ Roadmap de Migração - Sistema EnviaFolha

## ✅ FASE 1 - Refatoração Inicial (CONCLUÍDA)
- [x] Criar estrutura modular (`app/routes/`, `app/handlers/`)
- [x] Criar `BaseRouter` com métodos auxiliares
- [x] Reduzir `main.py` de 3346 para 126 linhas
- [x] Manter `main_legacy.py` funcionando (backup seguro)

## ✅ FASE 2.1 - Autenticação (CONCLUÍDA)
- [x] Migrar POST `/api/v1/auth/login`
- [x] Migrar GET `/api/v1/auth/me`
- [x] Criar `app/routes/auth.py` com `AuthRouter`
- [x] Testar login e autenticação

## 🔄 FASE 2.2 - Sistema & Health Checks (PRÓXIMA - RECOMENDADA)

**Por que começar por aqui?**
- ✅ Rotas **simples** (apenas leitura)
- ✅ **Sem lógica complexa** (ideal para testar padrão)
- ✅ **Não afeta envios** (baixo risco)
- ✅ **Validação rápida** (dashboard usa essas rotas)

### Rotas a Migrar:
```
GET /api/v1/system/status          → SystemRouter.handle_system_status()
GET /api/v1/database/health        → SystemRouter.handle_database_health()
GET /api/v1/evolution/status       → SystemRouter.handle_evolution_status()
GET /api/v1/system/logs            → SystemRouter.handle_system_logs()
GET /api/v1/dashboard/stats        → DashboardRouter.handle_dashboard_stats()
```

### Arquivos a Criar:
1. **`app/routes/system.py`** - SystemRouter
   - `handle_system_status()` - Status geral do sistema
   - `handle_database_health()` - Health check do PostgreSQL
   - `handle_evolution_status()` - Status da API Evolution
   - `handle_system_logs()` - Logs do sistema

2. **`app/routes/dashboard.py`** - DashboardRouter
   - `handle_dashboard_stats()` - Estatísticas para cards do dashboard

### Estimativa:
- ⏱️ Tempo: 30-40 minutos
- 🧪 Teste: Acessar dashboard e verificar cards
- 🎯 Impacto: Baixo risco, alta visibilidade

---

## 🔄 FASE 2.3 - Colaboradores (Employees)

### Rotas a Migrar:
```
GET    /api/v1/employees                    → EmployeesRouter.handle_list()
POST   /api/v1/employees                    → EmployeesRouter.handle_create()
GET    /api/v1/employees/:id                → EmployeesRouter.handle_detail()
PUT    /api/v1/employees/:id                → EmployeesRouter.handle_update()
DELETE /api/v1/employees/:id                → EmployeesRouter.handle_delete()
POST   /api/v1/employees/import             → EmployeesRouter.handle_import()
POST   /api/v1/employees/cache/invalidate   → EmployeesRouter.handle_cache_invalidate()
GET    /api/v1/employees/cache/status       → EmployeesRouter.handle_cache_status()
PATCH  /api/v1/employees/bulk               → EmployeesRouter.handle_bulk_update()
```

### Arquivos a Criar:
1. **`app/routes/employees.py`** - EmployeesRouter
2. **`app/handlers/employees_handler.py`** - Lógica de negócio

### Estimativa:
- ⏱️ Tempo: 1-1.5 horas
- 🧪 Teste: CRUD completo de colaboradores
- 🎯 Impacto: Médio (muitas funcionalidades dependem)

---

## 🔄 FASE 2.4 - Holerites (Payrolls)

### Rotas a Migrar:
```
POST /api/v1/payroll/process       → PayrollsRouter.handle_process()
POST /api/v1/payrolls/bulk-send    → PayrollsRouter.handle_bulk_send()
GET  /api/v1/payrolls/processed    → PayrollsRouter.handle_list_processed()
GET  /api/v1/payroll/periods       → PayrollsRouter.handle_periods_list()
POST /api/v1/payroll/periods       → PayrollsRouter.handle_create_period()
GET  /api/v1/payroll/periods/:id   → PayrollsRouter.handle_period_summary()
GET  /api/v1/payroll/templates     → PayrollsRouter.handle_templates_list()
POST /api/v1/payroll/templates     → PayrollsRouter.handle_create_template()
```

### Arquivos a Criar:
1. **`app/routes/payrolls.py`** - PayrollsRouter
2. **`app/handlers/payroll_handler.py`** - Processamento de PDFs
3. **`app/handlers/payroll_sender.py`** - Envio com delays

### Estimativa:
- ⏱️ Tempo: 1.5-2 horas
- 🧪 Teste: Upload + processamento + envio com delays
- 🎯 Impacto: Alto (funcionalidade principal)
- ⚠️ **CRÍTICO**: Manter delays de 7-41s funcionando!

---

## 🔄 FASE 2.5 - Comunicações

### Rotas a Migrar:
```
POST /api/v1/communications/send      → CommunicationsRouter.handle_send()
POST /api/v1/files/upload             → CommunicationsRouter.handle_file_upload()
POST /api/v1/evolution/test-message   → CommunicationsRouter.handle_test_message()
```

### Arquivos a Criar:
1. **`app/routes/communications.py`** - CommunicationsRouter
2. **`app/handlers/communication_sender.py`** - Envio com delays

### Estimativa:
- ⏱️ Tempo: 45-60 minutos
- 🧪 Teste: Envio de comunicados com/sem arquivo
- 🎯 Impacto: Alto (funcionalidade principal)
- ⚠️ **CRÍTICO**: Manter delays de 7-41s funcionando!

---

## 🔄 FASE 2.6 - Relatórios

### Rotas a Migrar:
```
GET /api/v1/reports/statistics   → ReportsRouter.handle_statistics()
```

### Arquivos a Criar:
1. **`app/routes/reports.py`** - ReportsRouter

### Estimativa:
- ⏱️ Tempo: 20-30 minutos
- 🧪 Teste: Página de relatórios
- 🎯 Impacto: Baixo (apenas leitura)

---

## 🔄 FASE 2.7 - Usuários & Permissões

### Rotas a Migrar:
```
GET    /api/v1/users                      → UsersRouter.handle_list()
POST   /api/v1/users                      → UsersRouter.handle_create()
PUT    /api/v1/users/:id                  → UsersRouter.handle_update()
DELETE /api/v1/users/:id                  → UsersRouter.handle_delete()
GET    /api/v1/roles                      → UsersRouter.handle_roles_list()
GET    /api/v1/users/permissions          → UsersRouter.handle_available_permissions()
POST   /api/v1/users/permissions          → UsersRouter.handle_update_permissions()
```

### Arquivos a Criar:
1. **`app/routes/users.py`** - UsersRouter
2. **`app/handlers/users_handler.py`** - Gestão de usuários

### Estimativa:
- ⏱️ Tempo: 1-1.5 horas
- 🧪 Teste: CRUD de usuários + permissões
- 🎯 Impacto: Médio (funcionalidade administrativa)

---

## 🎯 FASE 3 - Criação de Handlers

Após todas as rotas migradas, extrair lógica complexa:

1. **`app/handlers/pdf_processor.py`**
   - Processamento de PDFs de holerites
   - Segmentação por colaborador
   - Proteção com senha

2. **`app/handlers/evolution_handler.py`**
   - Wrapper da EvolutionAPIService
   - Retry automático
   - Validação de números

3. **`app/handlers/cache_manager.py`**
   - Gestão de cache de employees
   - Invalidação inteligente

4. **`app/handlers/import_handler.py`**
   - Importação de colaboradores
   - Validação de planilhas Excel

---

## 🧪 FASE 4 - Testes Unitários

1. Criar `tests/routes/` com testes para cada router
2. Criar `tests/handlers/` com testes de lógica de negócio
3. Usar pytest + fixtures
4. Coverage mínimo de 70%

---

## 📊 PROGRESSO ATUAL

```
MIGRADO:  2/40 rotas (5%)
TESTADO:  2/2 rotas migradas (100%)
PENDENTE: 38 rotas

Próxima fase recomendada: FASE 2.2 (Sistema & Health Checks)
```

---

## 🎯 ESTRATÉGIA DE MIGRAÇÃO

### Princípios:
1. ✅ **Uma rota por vez** (ou grupo pequeno de rotas relacionadas)
2. ✅ **Testar após cada migração** (validação incremental)
3. ✅ **Manter legacy funcionando** (rollback fácil)
4. ✅ **Comentar código migrado** (clareza no diff)
5. ✅ **Priorizar rotas simples primeiro** (ganhar confiança)

### Ordem de Complexidade:
1. 🟢 **Simples**: Sistema, Health Checks, Relatórios (apenas leitura)
2. 🟡 **Médio**: Colaboradores, Usuários (CRUD básico)
3. 🔴 **Complexo**: Holerites, Comunicações (envio + delays + arquivos)

### Estimativa Total:
- ⏱️ **Tempo total**: 6-8 horas
- 📅 **Duração**: 2-3 sessões de trabalho
- 🎯 **Meta**: 100% das rotas migradas até final da semana

---

## ✅ CHECKLIST POR FASE

Ao concluir cada fase:
- [ ] Criar router em `app/routes/`
- [ ] Criar handler em `app/handlers/` (se necessário)
- [ ] Modificar `main_legacy.py` para usar novo router
- [ ] Atualizar `app/routes/__init__.py`
- [ ] Reiniciar backend
- [ ] Testar todas as rotas migradas
- [ ] Atualizar este documento marcando ✅
- [ ] Commit das alterações

---

**Última atualização**: 23/10/2025 00:35
**Próxima ação**: Iniciar FASE 2.2 (Sistema & Health Checks)
