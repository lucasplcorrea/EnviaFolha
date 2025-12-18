-- ============================================================================
-- Script SQL para corrigir unique_id de colaboradores
-- Remove zeros à esquerda que foram perdidos na importação Excel
-- ============================================================================

-- 1. PREVIEW: Ver quais registros seriam afetados (NÃO FAZ ALTERAÇÕES)
-- ============================================================================
SELECT 
    id,
    full_name,
    unique_id AS id_atual,
    CONCAT('00', unique_id) AS id_corrigido,
    LENGTH(unique_id) AS tamanho_atual
FROM employees
WHERE (unique_id LIKE '59%' OR unique_id LIKE '60%')
  AND LENGTH(unique_id) = 7
ORDER BY unique_id;

-- Contagem de registros que serão corrigidos
SELECT COUNT(*) AS total_para_corrigir
FROM employees
WHERE (unique_id LIKE '59%' OR unique_id LIKE '60%')
  AND LENGTH(unique_id) = 7;


-- ============================================================================
-- 2. VERIFICAR CONFLITOS: Checar se algum ID corrigido já existe
-- ============================================================================
SELECT 
    e1.unique_id AS id_que_sera_corrigido,
    CONCAT('00', e1.unique_id) AS novo_id,
    e1.full_name AS colaborador_para_corrigir,
    e2.full_name AS colaborador_com_conflito
FROM employees e1
LEFT JOIN employees e2 ON e2.unique_id = CONCAT('00', e1.unique_id)
WHERE (e1.unique_id LIKE '59%' OR e1.unique_id LIKE '60%')
  AND LENGTH(e1.unique_id) = 7
  AND e2.id IS NOT NULL;

-- Se a query acima retornar registros, há conflitos que precisam ser resolvidos manualmente!


-- ============================================================================
-- 3. APLICAR CORREÇÃO: Atualizar os unique_id (MODIFICA DADOS!)
-- ============================================================================

-- IMPORTANTE: Execute apenas depois de verificar o preview e conflitos!
-- Descomente a linha abaixo para executar:

-- BEGIN;

UPDATE employees
SET 
    unique_id = CONCAT('00', unique_id),
    updated_at = CURRENT_TIMESTAMP
WHERE (unique_id LIKE '59%' OR unique_id LIKE '60%')
  AND LENGTH(unique_id) = 7;

-- Verificar quantos registros foram atualizados
-- SELECT ROW_COUNT();

-- Se tudo estiver correto, commit:
-- COMMIT;

-- Se algo estiver errado, rollback:
-- ROLLBACK;


-- ============================================================================
-- 4. VALIDAÇÃO: Verificar se as correções foram aplicadas
-- ============================================================================
SELECT 
    id,
    full_name,
    unique_id,
    LENGTH(unique_id) AS tamanho,
    updated_at
FROM employees
WHERE unique_id LIKE '0059%' OR unique_id LIKE '0060%'
ORDER BY unique_id;

-- Verificar se ainda existem IDs de 7 caracteres começando com 59/60
SELECT COUNT(*) AS ids_ainda_incorretos
FROM employees
WHERE (unique_id LIKE '59%' OR unique_id LIKE '60%')
  AND LENGTH(unique_id) = 7;


-- ============================================================================
-- 5. ESTATÍSTICAS FINAIS
-- ============================================================================
SELECT 
    CASE 
        WHEN LENGTH(unique_id) = 9 AND unique_id LIKE '00%' THEN 'Correto (9 chars, inicia com 00)'
        WHEN LENGTH(unique_id) = 7 THEN 'Incorreto (7 chars, faltam 00)'
        ELSE 'Outro formato'
    END AS status_unique_id,
    COUNT(*) AS quantidade
FROM employees
WHERE unique_id LIKE '59%' OR unique_id LIKE '60%'
GROUP BY status_unique_id;
