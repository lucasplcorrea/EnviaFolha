-- =============================================================================
-- MIGRATION SCRIPT - Nexo RH Production Database Update
-- Data: 2026-02-05
-- IMPORTANTE: Execute este script ANTES de atualizar os containers Docker
-- =============================================================================

-- EXECUTE COM CUIDADO! FAÇA BACKUP ANTES!
-- pg_dump -h host -U user -d database > backup_antes_migration.sql

-- =============================================================================
-- 1. TABELA: employees - Novas colunas para status e métricas
-- =============================================================================

-- 1.1 Campos demográficos (se não existirem)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='birth_date') THEN
        ALTER TABLE employees ADD COLUMN birth_date DATE;
        RAISE NOTICE 'Coluna birth_date adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='sex') THEN
        ALTER TABLE employees ADD COLUMN sex VARCHAR(10);
        RAISE NOTICE 'Coluna sex adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='marital_status') THEN
        ALTER TABLE employees ADD COLUMN marital_status VARCHAR(50);
        RAISE NOTICE 'Coluna marital_status adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='admission_date') THEN
        ALTER TABLE employees ADD COLUMN admission_date DATE;
        RAISE NOTICE 'Coluna admission_date adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='contract_type') THEN
        ALTER TABLE employees ADD COLUMN contract_type VARCHAR(50);
        RAISE NOTICE 'Coluna contract_type adicionada';
    END IF;
END $$;

-- 1.2 Campos de status (se não existirem)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='employment_status') THEN
        ALTER TABLE employees ADD COLUMN employment_status VARCHAR(50);
        RAISE NOTICE 'Coluna employment_status adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='termination_date') THEN
        ALTER TABLE employees ADD COLUMN termination_date DATE;
        RAISE NOTICE 'Coluna termination_date adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='leave_start_date') THEN
        ALTER TABLE employees ADD COLUMN leave_start_date DATE;
        RAISE NOTICE 'Coluna leave_start_date adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='leave_end_date') THEN
        ALTER TABLE employees ADD COLUMN leave_end_date DATE;
        RAISE NOTICE 'Coluna leave_end_date adicionada';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='employees' AND column_name='status_reason') THEN
        ALTER TABLE employees ADD COLUMN status_reason TEXT;
        RAISE NOTICE 'Coluna status_reason adicionada';
    END IF;
END $$;

-- =============================================================================
-- 2. TABELA: hr_indicator_snapshots - Cache de indicadores RH
-- =============================================================================

DROP TABLE IF EXISTS hr_indicator_snapshots CASCADE;

CREATE TABLE hr_indicator_snapshots (
    id SERIAL PRIMARY KEY,
    indicator_type VARCHAR(50) NOT NULL,
    calculation_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    metrics JSONB NOT NULL,
    total_records INTEGER,
    calculation_time_ms INTEGER,
    is_valid INTEGER DEFAULT 1,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hr_snapshots_indicator_type ON hr_indicator_snapshots(indicator_type);
CREATE INDEX IF NOT EXISTS idx_hr_snapshots_calculation_date ON hr_indicator_snapshots(calculation_date);
CREATE INDEX IF NOT EXISTS idx_type_date ON hr_indicator_snapshots(indicator_type, calculation_date);
CREATE INDEX IF NOT EXISTS idx_type_period ON hr_indicator_snapshots(indicator_type, period_start, period_end);

RAISE NOTICE 'Tabela hr_indicator_snapshots criada/recriada';

-- =============================================================================
-- 3. TABELA: payroll_records - Registros de folha (métrica)
-- =============================================================================

CREATE TABLE IF NOT EXISTS payroll_records (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    unified_code VARCHAR(255),
    competence VARCHAR(7) NOT NULL,
    salary_base DOUBLE PRECISION,
    additions DOUBLE PRECISION,
    deductions DOUBLE PRECISION,
    hours_extra DOUBLE PRECISION,
    hours_absence DOUBLE PRECISION,
    net_salary DOUBLE PRECISION,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payroll_records_employee_id ON payroll_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_payroll_records_unified_code ON payroll_records(unified_code);
CREATE INDEX IF NOT EXISTS idx_payroll_records_competence ON payroll_records(competence);

-- =============================================================================
-- 4. TABELA: benefit_records - Registros de benefícios (métrica)
-- =============================================================================

CREATE TABLE IF NOT EXISTS benefit_records (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    unified_code VARCHAR(255),
    benefit_type VARCHAR(255) NOT NULL,
    value DOUBLE PRECISION,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_benefit_records_employee_id ON benefit_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_benefit_records_unified_code ON benefit_records(unified_code);

-- =============================================================================
-- 5. TABELA: movement_records - Registros de movimentações
-- =============================================================================

CREATE TABLE IF NOT EXISTS movement_records (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    unified_code VARCHAR(255),
    movement_type VARCHAR(100) NOT NULL,
    previous_position VARCHAR(255),
    new_position VARCHAR(255),
    previous_department VARCHAR(255),
    new_department VARCHAR(255),
    date DATE NOT NULL,
    reason TEXT,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_movement_records_employee_id ON movement_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_movement_records_unified_code ON movement_records(unified_code);

-- =============================================================================
-- 6. TABELA: leave_records - Registros de afastamentos/férias
-- =============================================================================

CREATE TABLE IF NOT EXISTS leave_records (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    unified_code VARCHAR(255),
    leave_type VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days DOUBLE PRECISION,
    notes VARCHAR(500),
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leave_records_employee_id ON leave_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_records_unified_code ON leave_records(unified_code);

-- =============================================================================
-- 7. TABELA: timecard_periods - Períodos de cartão ponto
-- =============================================================================

CREATE TABLE IF NOT EXISTS timecard_periods (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    period_name VARCHAR(100) NOT NULL,
    start_date DATE,
    end_date DATE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 8. TABELA: timecard_data - Dados de cartão ponto
-- =============================================================================

CREATE TABLE IF NOT EXISTS timecard_data (
    id SERIAL PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES timecard_periods(id) ON DELETE CASCADE,
    employee_id INTEGER REFERENCES employees(id),
    employee_number VARCHAR(20) NOT NULL,
    employee_name VARCHAR(255),
    company VARCHAR(50) NOT NULL,
    normal_hours DECIMAL(10, 2) DEFAULT 0,
    overtime_50 DECIMAL(10, 2) DEFAULT 0,
    overtime_100 DECIMAL(10, 2) DEFAULT 0,
    night_overtime_50 DECIMAL(10, 2) DEFAULT 0,
    night_overtime_100 DECIMAL(10, 2) DEFAULT 0,
    night_hours DECIMAL(10, 2) DEFAULT 0,
    absences DECIMAL(10, 2) DEFAULT 0,
    dsr_debit DECIMAL(10, 2) DEFAULT 0,
    bonus_hours DECIMAL(10, 2) DEFAULT 0,
    upload_filename VARCHAR(500),
    processed_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_timecard_data_period_id ON timecard_data(period_id);
CREATE INDEX IF NOT EXISTS idx_timecard_data_employee_id ON timecard_data(employee_id);
CREATE INDEX IF NOT EXISTS idx_timecard_data_employee_number ON timecard_data(employee_number);

-- =============================================================================
-- 9. TABELA: timecard_processing_logs - Logs de processamento cartão ponto
-- =============================================================================

CREATE TABLE IF NOT EXISTS timecard_processing_logs (
    id SERIAL PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES timecard_periods(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    total_rows INTEGER,
    processed_rows INTEGER,
    error_rows INTEGER,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    processing_summary JSONB,
    processed_by INTEGER REFERENCES users(id),
    processing_time DECIMAL(5, 2),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 10. TABELA: send_queues - Filas de envio
-- =============================================================================

CREATE TABLE IF NOT EXISTS send_queues (
    id SERIAL PRIMARY KEY,
    queue_id VARCHAR(100) UNIQUE NOT NULL,
    queue_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_items INTEGER NOT NULL DEFAULT 0,
    processed_items INTEGER NOT NULL DEFAULT 0,
    successful_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    description VARCHAR(500),
    file_name VARCHAR(255),
    queue_metadata JSONB,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    user_id INTEGER REFERENCES users(id),
    computer_name VARCHAR(255),
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_send_queues_queue_id ON send_queues(queue_id);
CREATE INDEX IF NOT EXISTS idx_send_queues_status ON send_queues(status);

-- =============================================================================
-- 11. TABELA: send_queue_items - Itens das filas de envio
-- =============================================================================

CREATE TABLE IF NOT EXISTS send_queue_items (
    id SERIAL PRIMARY KEY,
    queue_id VARCHAR(100) NOT NULL REFERENCES send_queues(queue_id),
    employee_id INTEGER REFERENCES employees(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    phone_number VARCHAR(20),
    file_path VARCHAR(500),
    sent_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    item_metadata JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_send_queue_items_queue_id ON send_queue_items(queue_id);
CREATE INDEX IF NOT EXISTS idx_send_queue_items_status ON send_queue_items(status);

-- =============================================================================
-- 12. TABELA: system_logs - Logs do sistema (ENUM TYPES PRIMEIRO!)
-- =============================================================================

-- Criar tipos ENUM se não existirem
DO $$ BEGIN
    CREATE TYPE loglevel AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE logcategory AS ENUM ('SYSTEM', 'AUTH', 'EMPLOYEE', 'IMPORT', 'PAYROLL', 'COMMUNICATION', 'WHATSAPP', 'DATABASE', 'API');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level loglevel NOT NULL DEFAULT 'INFO',
    category logcategory NOT NULL DEFAULT 'SYSTEM',
    message TEXT NOT NULL,
    details TEXT,
    user_id INTEGER,
    username VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- =============================================================================
-- 13. TABELA: benefits_periods - Períodos de benefícios iFood
-- =============================================================================

CREATE TABLE IF NOT EXISTS benefits_periods (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    period_name VARCHAR(100) NOT NULL,
    company VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 14. TABELA: benefits_data - Dados de benefícios iFood
-- =============================================================================

CREATE TABLE IF NOT EXISTS benefits_data (
    id SERIAL PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES benefits_periods(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    cpf VARCHAR(20) NOT NULL,
    refeicao DECIMAL(10, 2) DEFAULT 0,
    alimentacao DECIMAL(10, 2) DEFAULT 0,
    mobilidade DECIMAL(10, 2) DEFAULT 0,
    livre DECIMAL(10, 2) DEFAULT 0,
    upload_filename VARCHAR(500),
    processed_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_benefits_data_period_id ON benefits_data(period_id);
CREATE INDEX IF NOT EXISTS idx_benefits_data_cpf ON benefits_data(cpf);

-- =============================================================================
-- 15. TABELA: benefits_processing_logs - Logs de processamento benefícios
-- =============================================================================

CREATE TABLE IF NOT EXISTS benefits_processing_logs (
    id SERIAL PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES benefits_periods(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    total_rows INTEGER,
    processed_rows INTEGER,
    error_rows INTEGER,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    processing_summary JSONB,
    processed_by INTEGER REFERENCES users(id),
    processing_time DECIMAL(5, 2),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 16. TABELAS EXISTENTES - Verificar colunas adicionais
-- =============================================================================

-- 16.1 communication_sends - verificar user_id nullable
DO $$ 
BEGIN
    -- Tornar user_id nullable se já existir
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='communication_sends' AND column_name='user_id') THEN
        ALTER TABLE communication_sends ALTER COLUMN user_id DROP NOT NULL;
        RAISE NOTICE 'communication_sends.user_id tornado nullable';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Erro ao alterar communication_sends.user_id: %', SQLERRM;
END $$;

-- 16.2 Verificar coluna title em communication_sends
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='communication_sends' AND column_name='title') THEN
        ALTER TABLE communication_sends ADD COLUMN title VARCHAR(255);
        RAISE NOTICE 'Coluna title adicionada em communication_sends';
    END IF;
END $$;

-- 16.3 payroll_processing_logs - verificar processed_by nullable
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='payroll_processing_logs' AND column_name='processed_by') THEN
        ALTER TABLE payroll_processing_logs ALTER COLUMN processed_by DROP NOT NULL;
        RAISE NOTICE 'payroll_processing_logs.processed_by tornado nullable';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Erro ao alterar payroll_processing_logs.processed_by: %', SQLERRM;
END $$;

-- =============================================================================
-- FINALIZAÇÃO
-- =============================================================================

-- Verificar todas as tabelas criadas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- =============================================================================
-- FIM DO SCRIPT
-- Após executar, atualize os containers:
-- docker pull lucasplcorrea/enviafolha-backend:latest
-- docker pull lucasplcorrea/enviafolha-frontend:latest
-- docker-compose down && docker-compose up -d
-- =============================================================================
