# Estrutura de Filtros - Overview de Indicadores

## Tabelas Envolvidas

### 1. `employees` (Tabela de Colaboradores)
Campos principais:
- `id` (Integer, PK) - ID auto-increment (chave primária)
- `unique_id` (String) - Matrícula do colaborador (ex: "0001", "0023")
- `name` (String) - Nome completo
- `cpf` (String) - CPF
- `company_code` (String) - Código da empresa ("0060" ou "0059")
- `department` (String) - Departamento/Setor (ex: "OBRAS", "ADMINISTRATIVO")
- `admission_date` (Date) - Data de admissão
- `termination_date` (Date) - Data de desligamento (NULL se ativo)

### 2. `payroll_periods` (Tabela de Períodos)
Campos principais:
- `id` (Integer, PK) - ID do período
- `year` (Integer) - Ano (ex: 2025)
- `month` (Integer) - Mês (1-12)
- `period_name` (String) - Nome do período (ex: "Novembro 2025", "13º Salário 2025")
- `company` (String) - Código da empresa

### 3. `payroll_data` (Tabela de Dados da Folha)
Campos principais:
- `id` (Integer, PK) - ID do registro
- `employee_id` (Integer, FK) - **ATENÇÃO**: Pode referenciar `employees.id` OU `employees.unique_id`
- `period_id` (Integer, FK) - Referência para `payroll_periods.id`
- `gross_salary` (Decimal) - Salário bruto
- `net_salary` (Decimal) - Salário líquido
- `earnings_data` (JSON) - Proventos detalhados
- `deductions_data` (JSON) - Descontos detalhados

## Problema Identificado

**CRÍTICO**: O campo `payroll_data.employee_id` deveria sempre referenciar `employees.id`, mas os dados importados podem estar usando `employees.unique_id` (matrícula).

Exemplo:
- Employee: `id=1234`, `unique_id="0001"`, `company_code="0059"`
- PayrollData: `employee_id=1` (se usando unique_id) ou `employee_id=1234` (se usando id)

## SELECT Exemplo: Obras, Novembro 2025, Infraestrutura

```sql
-- Buscar colaboradores filtrados
SELECT 
    e.id,
    e.unique_id,
    e.name,
    e.company_code,
    e.department
FROM employees e
WHERE e.company_code = '0059'  -- Infraestrutura
  AND e.department = 'OBRAS'
  AND e.is_active = 1;

-- Buscar períodos de novembro/2025
SELECT 
    id,
    year,
    month,
    period_name,
    company
FROM payroll_periods
WHERE year = 2025
  AND month = 11;

-- Buscar dados de folha (versão completa com JOIN)
SELECT 
    pd.id,
    pd.employee_id,
    pd.period_id,
    pd.net_salary,
    e.name,
    e.company_code,
    e.department,
    pp.period_name
FROM payroll_data pd
INNER JOIN employees e ON (pd.employee_id = e.id OR pd.employee_id = e.unique_id)
INNER JOIN payroll_periods pp ON pd.period_id = pp.id
WHERE pp.year = 2025
  AND pp.month = 11
  AND e.company_code = '0059'
  AND e.department = 'OBRAS';
```

## Solução Atual (Overview)

A lógica atual faz:

1. **Busca colaboradores filtrados**:
   ```python
   employee_query = db.query(Employee).filter(
       Employee.company_code == '0059',
       Employee.department == 'OBRAS'
   )
   filtered_employees = employee_query.all()
   ```

2. **Extrai IDs e unique_ids**:
   ```python
   employee_ids = [emp.id for emp in filtered_employees]  # [1234, 1235, 1236...]
   employee_unique_ids = [emp.unique_id for emp in filtered_employees]  # ["0001", "0002", "0003"...]
   ```

3. **Busca dados de folha usando OR**:
   ```python
   payroll_query = db.query(PayrollData).filter(
       PayrollData.period_id.in_(period_ids),
       or_(
           PayrollData.employee_id.in_(employee_ids),  # Tenta com IDs numéricos
           PayrollData.employee_id.in_(employee_unique_ids)  # Tenta com unique_ids
       )
   )
   ```

## Problema Atual

A query acima está **ERRADA** se os tipos de dados não coincidirem:
- Se `PayrollData.employee_id` é `Integer`, não vai dar match com `unique_id` que é `String`
- Se `PayrollData.employee_id` está como String (matrícula), não vai dar match com `id` que é Integer

## Necessário Verificar

Execute no banco:
```sql
-- Ver tipo de dados de employee_id em payroll_data
SELECT typeof(employee_id) as tipo, employee_id, COUNT(*) 
FROM payroll_data 
GROUP BY employee_id 
LIMIT 10;

-- Ver se employee_id corresponde a id ou unique_id
SELECT 
    pd.employee_id,
    e.id as emp_id,
    e.unique_id as emp_unique,
    COUNT(*) as total
FROM payroll_data pd
LEFT JOIN employees e ON pd.employee_id = e.id
GROUP BY pd.employee_id
LIMIT 10;
```
