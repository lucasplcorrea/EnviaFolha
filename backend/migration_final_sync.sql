-- =====================================================
-- MIGRATION FINAL - Sincronização Desenvolvimento → Produção
-- =====================================================
-- Este script sincroniza o banco de produção com o desenvolvimento
-- baseado na comparação do DBeaver
-- =====================================================

-- 1. ADICIONAR COLUNA company EM payroll_periods (CRÍTICO - estava causando erro)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'payroll_periods' AND column_name = 'company'
    ) THEN
        ALTER TABLE payroll_periods ADD COLUMN company VARCHAR(50) NOT NULL DEFAULT '0060';
        RAISE NOTICE 'Coluna company adicionada à tabela payroll_periods';
    ELSE
        RAISE NOTICE 'Coluna company já existe em payroll_periods';
    END IF;
END $$;

-- 2. CORRIGIR NULLABILITY DAS COLUNAS em employees
DO $$
BEGIN
    -- Tornar cpf nullable (dev: NOT NULL = false)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employees' AND column_name = 'cpf' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE employees ALTER COLUMN cpf DROP NOT NULL;
        RAISE NOTICE 'Coluna cpf em employees agora permite NULL';
    END IF;

    -- Tornar phone nullable (dev: NOT NULL = false)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'employees' AND column_name = 'phone' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE employees ALTER COLUMN phone DROP NOT NULL;
        RAISE NOTICE 'Coluna phone em employees agora permite NULL';
    END IF;
END $$;

-- 3. CORRIGIR TIPOS DE DADOS: timestamp → timestamptz
-- (Dev usa timestamptz, produção usa timestamp em várias tabelas)

DO $$
BEGIN
    -- benefits_data
    ALTER TABLE benefits_data 
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    -- benefits_periods
    ALTER TABLE benefits_periods
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    -- benefits_processing_logs
    ALTER TABLE benefits_processing_logs
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    -- hr_indicator_snapshots
    ALTER TABLE hr_indicator_snapshots
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    -- timecard_data
    ALTER TABLE timecard_data
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    -- timecard_periods
    ALTER TABLE timecard_periods
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    -- timecard_processing_logs
    ALTER TABLE timecard_processing_logs
        ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN created_at SET DEFAULT now(),
        ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at DROP DEFAULT;
    
    RAISE NOTICE 'Tipos de dados timestamp convertidos para timestamptz';
END $$;

-- 4. CORRIGIR TIPOS JSON: jsonb → json em processing_summary
DO $$
BEGIN
    -- benefits_processing_logs
    ALTER TABLE benefits_processing_logs
        ALTER COLUMN processing_summary TYPE jsonb USING processing_summary::jsonb;
    
    -- timecard_processing_logs
    ALTER TABLE timecard_processing_logs
        ALTER COLUMN processing_summary TYPE jsonb USING processing_summary::jsonb;
    
    -- hr_indicator_snapshots
    ALTER TABLE hr_indicator_snapshots
        ALTER COLUMN metrics TYPE jsonb USING metrics::jsonb;
    
    RAISE NOTICE 'Tipos JSON convertidos para JSONB';
END $$;

-- 5. ADICIONAR VALORES DEFAULT faltantes
DO $$
BEGIN
    -- benefits_data: adicionar defaults
    ALTER TABLE benefits_data
        ALTER COLUMN refeicao SET DEFAULT 0,
        ALTER COLUMN alimentacao SET DEFAULT 0,
        ALTER COLUMN mobilidade SET DEFAULT 0,
        ALTER COLUMN livre SET DEFAULT 0;
    
    -- benefits_periods
    ALTER TABLE benefits_periods
        ALTER COLUMN is_active SET DEFAULT true;
    
    -- hr_indicator_snapshots
    ALTER TABLE hr_indicator_snapshots
        ALTER COLUMN is_valid SET DEFAULT 1;
    
    -- timecard_data
    ALTER TABLE timecard_data
        ALTER COLUMN normal_hours SET DEFAULT 0,
        ALTER COLUMN overtime_50 SET DEFAULT 0,
        ALTER COLUMN overtime_100 SET DEFAULT 0,
        ALTER COLUMN night_overtime_50 SET DEFAULT 0,
        ALTER COLUMN night_overtime_100 SET DEFAULT 0,
        ALTER COLUMN night_hours SET DEFAULT 0,
        ALTER COLUMN absences SET DEFAULT 0,
        ALTER COLUMN dsr_debit SET DEFAULT 0,
        ALTER COLUMN bonus_hours SET DEFAULT 0;
    
    -- timecard_periods
    ALTER TABLE timecard_periods
        ALTER COLUMN is_active SET DEFAULT true;
    
    RAISE NOTICE 'Valores padrão adicionados';
END $$;

-- 6. CRIAR ÍNDICES FALTANTES (dev tem, produção não tem)
DO $$
BEGIN
    -- benefit_records
    CREATE INDEX IF NOT EXISTS idx_benefit_records_employee_id ON benefit_records(employee_id);
    CREATE INDEX IF NOT EXISTS idx_benefit_records_unified_code ON benefit_records(unified_code);
    
    -- benefits_data
    CREATE INDEX IF NOT EXISTS idx_benefits_data_cpf ON benefits_data(cpf);
    CREATE INDEX IF NOT EXISTS idx_benefits_data_period_id ON benefits_data(period_id);
    
    -- hr_indicator_snapshots
    CREATE INDEX IF NOT EXISTS idx_hr_snapshots_calculation_date ON hr_indicator_snapshots(calculation_date);
    CREATE INDEX IF NOT EXISTS idx_hr_snapshots_indicator_type ON hr_indicator_snapshots(indicator_type);
    
    -- leave_records
    CREATE INDEX IF NOT EXISTS idx_leave_records_employee_id ON leave_records(employee_id);
    CREATE INDEX IF NOT EXISTS idx_leave_records_unified_code ON leave_records(unified_code);
    
    -- movement_records
    CREATE INDEX IF NOT EXISTS idx_movement_records_employee_id ON movement_records(employee_id);
    CREATE INDEX IF NOT EXISTS idx_movement_records_unified_code ON movement_records(unified_code);
    
    -- payroll_records
    CREATE INDEX IF NOT EXISTS idx_payroll_records_competence ON payroll_records(competence);
    CREATE INDEX IF NOT EXISTS idx_payroll_records_employee_id ON payroll_records(employee_id);
    CREATE INDEX IF NOT EXISTS idx_payroll_records_unified_code ON payroll_records(unified_code);
    
    -- send_queue_items
    CREATE INDEX IF NOT EXISTS idx_send_queue_items_queue_id ON send_queue_items(queue_id);
    CREATE INDEX IF NOT EXISTS idx_send_queue_items_status ON send_queue_items(status);
    
    -- send_queues
    CREATE INDEX IF NOT EXISTS idx_send_queues_queue_id ON send_queues(queue_id);
    CREATE INDEX IF NOT EXISTS idx_send_queues_status ON send_queues(status);
    
    -- system_logs
    CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);
    CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
    CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);
    
    -- timecard_data
    CREATE INDEX IF NOT EXISTS idx_timecard_data_employee_id ON timecard_data(employee_id);
    CREATE INDEX IF NOT EXISTS idx_timecard_data_employee_number ON timecard_data(employee_number);
    CREATE INDEX IF NOT EXISTS idx_timecard_data_period_id ON timecard_data(period_id);
    
    RAISE NOTICE 'Índices criados';
END $$;

-- 7. REMOVER ÍNDICES DUPLICADOS (produção tem ix_*, dev tem idx_*)
DO $$
BEGIN
    -- benefits_data: remover ix_*, manter idx_*
    DROP INDEX IF EXISTS ix_benefits_data_cpf;
    DROP INDEX IF EXISTS ix_benefits_data_id;
    
    -- benefits_periods
    DROP INDEX IF EXISTS ix_benefits_periods_id;
    
    -- benefits_processing_logs
    DROP INDEX IF EXISTS ix_benefits_processing_logs_id;
    
    -- hr_indicator_snapshots: remover ix_*, manter idx_*
    DROP INDEX IF EXISTS ix_hr_indicator_snapshots_calculation_date;
    DROP INDEX IF EXISTS ix_hr_indicator_snapshots_id;
    DROP INDEX IF EXISTS ix_hr_indicator_snapshots_indicator_type;
    
    -- timecard_data: remover ix_*, manter idx_*
    DROP INDEX IF EXISTS ix_timecard_data_employee_number;
    DROP INDEX IF EXISTS ix_timecard_data_id;
    
    -- timecard_periods
    DROP INDEX IF EXISTS ix_timecard_periods_id;
    
    -- timecard_processing_logs
    DROP INDEX IF EXISTS ix_timecard_processing_logs_id;
    
    RAISE NOTICE 'Índices duplicados removidos';
END $$;

-- 8. CRIAR FUNÇÃO update_hr_snapshots_updated_at (existe em dev, não em prod)
DO $$
BEGIN
    -- Criar função para atualizar updated_at automaticamente
    CREATE OR REPLACE FUNCTION update_hr_snapshots_updated_at()
    RETURNS TRIGGER AS $trigger$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $trigger$ LANGUAGE plpgsql;
    
    -- Criar trigger
    DROP TRIGGER IF EXISTS update_hr_snapshots_timestamp ON hr_indicator_snapshots;
    CREATE TRIGGER update_hr_snapshots_timestamp
        BEFORE UPDATE ON hr_indicator_snapshots
        FOR EACH ROW
        EXECUTE FUNCTION update_hr_snapshots_updated_at();
    
    RAISE NOTICE 'Função e trigger update_hr_snapshots_updated_at criados';
END $$;

-- =====================================================
-- VERIFICAÇÃO FINAL
-- =====================================================

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '=== VERIFICAÇÃO PÓS-MIGRAÇÃO ===';
    
    -- Verificar coluna company
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.columns 
    WHERE table_name = 'payroll_periods' AND column_name = 'company';
    RAISE NOTICE 'Coluna payroll_periods.company: %', CASE WHEN v_count > 0 THEN 'OK' ELSE 'FALTANDO' END;
    
    -- Verificar nullability cpf
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.columns 
    WHERE table_name = 'employees' AND column_name = 'cpf' AND is_nullable = 'YES';
    RAISE NOTICE 'employees.cpf nullable: %', CASE WHEN v_count > 0 THEN 'OK' ELSE 'ERRO' END;
    
    -- Verificar timestamptz
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.columns 
    WHERE table_name = 'benefits_data' AND column_name = 'created_at' AND data_type = 'timestamp with time zone';
    RAISE NOTICE 'benefits_data.created_at timestamptz: %', CASE WHEN v_count > 0 THEN 'OK' ELSE 'ERRO' END;
    
    -- Verificar jsonb
    SELECT COUNT(*) INTO v_count 
    FROM information_schema.columns 
    WHERE table_name = 'hr_indicator_snapshots' AND column_name = 'metrics' AND data_type = 'jsonb';
    RAISE NOTICE 'hr_indicator_snapshots.metrics jsonb: %', CASE WHEN v_count > 0 THEN 'OK' ELSE 'ERRO' END;
    
    -- Contar índices criados
    SELECT COUNT(*) INTO v_count 
    FROM pg_indexes 
    WHERE indexname LIKE 'idx_%' AND schemaname = 'public';
    RAISE NOTICE 'Total de índices idx_*: %', v_count;
    
    -- Verificar função
    SELECT COUNT(*) INTO v_count 
    FROM pg_proc 
    WHERE proname = 'update_hr_snapshots_updated_at';
    RAISE NOTICE 'Função update_hr_snapshots_updated_at: %', CASE WHEN v_count > 0 THEN 'OK' ELSE 'FALTANDO' END;
    
    RAISE NOTICE '=== FIM DA VERIFICAÇÃO ===';
END $$;
