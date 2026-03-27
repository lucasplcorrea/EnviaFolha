# 📋 Guia de Deploy em Produção — EnviaFolha HRMS

> **Instruções:** Aplique os passos **em ordem**. Cada seção corresponde a uma entrega commitada na branch `ajustes-cadastros`.
> Antes de começar, faça backup completo do banco de produção.

---

## ✅ Entrega 1 — Estrutura de Dados (27/03/2026)
**Branch:** `ajustes-cadastros` | **Commit:** `feat(db): add Company, WorkLocation models and absolute_id to Employee`

### 1.1 — Rodar a migração Alembic
```bash
# Na pasta /backend, com o .venv ativado:
python -m alembic upgrade head
```

**O que essa migration faz:**
- Cria a tabela `companies` (Empresas do grupo com prefixo de matrícula)
- Cria a tabela `work_locations` (Obras e locais de atuação com coordenadas)
- Adiciona coluna `absolute_id VARCHAR(80) UNIQUE` em `employees`
- Adiciona coluna `company_id INTEGER FK → companies` em `employees`
- Adiciona coluna `work_location_id INTEGER FK → work_locations` em `employees`
- Remove a constraint `UNIQUE` de `employees.unique_id`
- Remove a constraint `UNIQUE` de `employees.cpf`
- Remove tabelas obsoletas: `timecard_data`, `timecard_periods`, `timecard_processing_logs`, `audit_logs`, `system_settings`

### 1.2 — Wipe dos dados de colaboradores (OPCIONAL)
> ⚠️ **ATENÇÃO:** Esta etapa apaga **todos** os colaboradores e históricos. Só execute se você vai reimportar toda a base.

```bash
python wipe_data.py
```

**Tabelas zeradas:** `employees`, `payroll_data`, `payroll_records`, `payroll_sends`, `payroll_processing_logs`, `leave_records`, `benefit_records`, `benefits_data`, `benefits_periods`, `benefits_processing_logs`, `communication_recipients`, `communication_sends`, `tax_statements`, `tax_statement_uploads`, `send_queue_items`, `send_queues`, `hr_indicator_snapshots`, `movement_records`

### 1.3 — Verificar
```bash
python inspect_emp_raw.py
# Deve exibir as tabelas: companies, work_locations, e as novas colunas em employees
```

---

## ✅ Entrega 2 — Novo Importador de Colaboradores (27/03/2026)
**Commit:** `feat(import): auto-generate absolute_id; new employee xlsx template`

### 2.1 — Substituir o template de importação
Copie o arquivo `backend/modelo_importacao_colaboradores.xlsx` para `frontend/public/` da produção (ou apenas faça o pull do repositório — ele já está versionado).

**Novos campos obrigatórios no XLSX:** `nome`, `cpf`, `matricula`, `company_code`, `data_admissao`
**Campos removidos como obrigatórios:** `phone_number`, `unique_id`
**Campo automático:** `absolute_id` — gerado pelo backend, não inclua na planilha.

### 2.2 — Não requer migration de banco
Apenas atualização de código (backend + frontend).

---

## ✅ Entrega 3 — Remoção da Coluna `sector` de `employees` (27/03/2026)
**Commit:** `refactor(db): drop sector column from employees`

### 3.1 — Rodar a migração Alembic
```bash
python -m alembic upgrade head
```

**O que essa migration faz:**
- Remove a coluna `sector` da tabela `employees` (substituída por `department`, que tem o mesmo papel)

---

*(Este documento será atualizado a cada nova entrega commitada)*

---

## 📝 Referência Rápida de Comandos

```bash
# Ativar ambiente virtual
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Ver estado atual das migrations
python -m alembic current

# Ver histórico de migrations
python -m alembic history --verbose

# Aplicar todas as migrations pendentes
python -m alembic upgrade head

# Reverter 1 migration
python -m alembic downgrade -1
```
