-- FASE 1: Migração de Banco de Dados - Adicionar coluna name_id
-- 
-- Objetivo:
-- - Adicionar coluna name_id à tabela employees
-- - Criar índice para busca rápida
-- - Documentar objetivo e formato
--
-- Data: 2026-04-01
-- Status: REVERSÍVEL (com DROP para rollback)

-- ============================================================================
-- 1. ADICIONAR COLUNA name_id
-- ============================================================================

ALTER TABLE employees
ADD COLUMN IF NOT EXISTS name_id VARCHAR(255) NULL;

COMMENT ON COLUMN employees.name_id IS 'Chave auxiliar: company_code + registration_number (5 dig) + normalized_name';

-- ============================================================================
-- 2. CRIAR ÍNDICE PARA BUSCA RÁPIDA
-- ============================================================================

CREATE INDEX idx_employees_name_id ON employees(name_id);

-- ============================================================================
-- 3. ÍNDICE COMPOSTO (future-proof) - OPCIONAL
-- ============================================================================
-- Descomentar se quiser garantir name_id único POR EMPRESA
-- ALTER TABLE employees ADD CONSTRAINT uq_employees_name_id_company 
--   UNIQUE (company_id, name_id);

-- ============================================================================
-- 4. VERIFICAÇÃO
-- ============================================================================

-- Verificar que coluna foi criada:
-- SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_NAME = 'employees' AND COLUMN_NAME = 'name_id';

-- Verificar que índice foi criado:
-- SHOW INDEX FROM employees WHERE Column_name = 'name_id';

-- ============================================================================
-- ROLLBACK (se necessário)
-- ============================================================================
-- DROP INDEX IF EXISTS idx_employees_name_id;
-- ALTER TABLE employees DROP COLUMN IF EXISTS name_id;
