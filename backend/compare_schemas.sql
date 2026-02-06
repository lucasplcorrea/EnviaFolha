-- =============================================================================
-- SCRIPT DE COMPARAÇÃO DE SCHEMA - PostgreSQL
-- Execute este script em AMBOS os bancos (desenvolvimento e produção)
-- e compare os resultados
-- =============================================================================

-- 1. LISTAR TODAS AS TABELAS
SELECT 
    '=== TABELAS ===' as secao,
    table_name,
    NULL as column_name,
    NULL as data_type,
    NULL as is_nullable,
    NULL as column_default
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name

UNION ALL

-- 2. LISTAR TODAS AS COLUNAS DE CADA TABELA
SELECT 
    table_name as secao,
    table_name,
    column_name,
    data_type || 
        CASE 
            WHEN character_maximum_length IS NOT NULL 
            THEN '(' || character_maximum_length || ')'
            WHEN numeric_precision IS NOT NULL 
            THEN '(' || numeric_precision || 
                CASE WHEN numeric_scale IS NOT NULL AND numeric_scale > 0 
                THEN ',' || numeric_scale ELSE '' END || ')'
            ELSE ''
        END as data_type,
    is_nullable,
    COALESCE(column_default, 'NULL') as column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- =============================================================================
-- 3. INDICES (execute separadamente se necessário)
-- =============================================================================
SELECT 
    '=== INDICES ===' as tipo,
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- =============================================================================
-- 4. FOREIGN KEYS (execute separadamente se necessário)
-- =============================================================================
SELECT 
    '=== FOREIGN KEYS ===' as tipo,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;

-- =============================================================================
-- 5. TIPOS ENUM (execute separadamente se necessário)
-- =============================================================================
SELECT 
    '=== ENUMS ===' as tipo,
    t.typname as enum_name,
    e.enumlabel as enum_value,
    e.enumsortorder
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public'
ORDER BY t.typname, e.enumsortorder;

-- =============================================================================
-- 6. VERSÃO SIMPLIFICADA - APENAS TABELAS E COLUNAS
-- Execute esta se as queries acima derem muito output
-- =============================================================================
/*
SELECT 
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
*/
