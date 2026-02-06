-- =============================================================================
-- HOTFIX: Adicionar coluna 'company' na tabela payroll_periods
-- Execute IMEDIATAMENTE no banco de produção
-- =============================================================================

-- Adicionar coluna company se não existir
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='payroll_periods' AND column_name='company'
    ) THEN
        ALTER TABLE payroll_periods ADD COLUMN company VARCHAR(50) NOT NULL DEFAULT '0060';
        RAISE NOTICE 'Coluna company adicionada em payroll_periods';
    ELSE
        RAISE NOTICE 'Coluna company já existe em payroll_periods';
    END IF;
END $$;

-- Verificar se foi criada
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'payroll_periods' AND column_name = 'company';
