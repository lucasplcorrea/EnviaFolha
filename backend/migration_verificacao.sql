-- =============================================================================
-- SCRIPT DE VERIFICAÇÃO - Nexo RH Production Database
-- Execute após o migration_production.sql para verificar se tudo está OK
-- =============================================================================

-- 1. Listar todas as tabelas existentes
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. Verificar colunas da tabela employees (novas colunas adicionadas)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'employees'
ORDER BY ordinal_position;

-- 3. Verificar se hr_indicator_snapshots existe e está correta
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'hr_indicator_snapshots'
ORDER BY ordinal_position;

-- 4. Verificar tabelas de timecard
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'timecard_periods';

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'timecard_data';

-- 5. Verificar se communication_sends.user_id é nullable
SELECT column_name, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'communication_sends' AND column_name = 'user_id';

-- 6. Contar registros em tabelas principais
SELECT 
    'employees' as tabela, COUNT(*) as registros FROM employees
UNION ALL
SELECT 'payroll_periods', COUNT(*) FROM payroll_periods
UNION ALL
SELECT 'payroll_data', COUNT(*) FROM payroll_data
UNION ALL
SELECT 'users', COUNT(*) FROM users;
