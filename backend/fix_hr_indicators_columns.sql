-- ============================================
-- Fix hr_indicator_snapshots Column Types
-- ============================================
-- Este script corrige os tipos de colunas da tabela hr_indicator_snapshots
-- que foram criadas incorretamente durante export/import

-- 1. Dropar a tabela se existir (como está vazia, não há problema)
DROP TABLE IF EXISTS hr_indicator_snapshots CASCADE;

-- 2. Recriar a tabela com tipos corretos
CREATE TABLE hr_indicator_snapshots (
    id SERIAL PRIMARY KEY,
    
    -- Identificação do snapshot
    indicator_type VARCHAR(50) NOT NULL,
    calculation_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    
    -- Dados agregados (JSON flexível)
    metrics JSONB NOT NULL,
    
    -- Metadados
    total_records INTEGER,
    calculation_time_ms INTEGER,
    is_valid INTEGER DEFAULT 1,
    
    -- Timestamps (CORRETO: TIMESTAMP, não VARCHAR!)
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Criar índices
CREATE INDEX idx_hr_indicator_type ON hr_indicator_snapshots(indicator_type);
CREATE INDEX idx_hr_indicator_date ON hr_indicator_snapshots(calculation_date);
CREATE INDEX idx_hr_indicator_created ON hr_indicator_snapshots(created_at);
CREATE INDEX idx_type_date ON hr_indicator_snapshots(indicator_type, calculation_date);
CREATE INDEX idx_type_period ON hr_indicator_snapshots(indicator_type, period_start, period_end);

-- 4. Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_hr_indicator_snapshots_updated_at 
    BEFORE UPDATE ON hr_indicator_snapshots 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Fim da migração
-- ============================================

-- Para executar no servidor:
-- psql -U nexo_rh -d nexo_rh_db -f fix_hr_indicators_columns.sql
