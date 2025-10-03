-- Initial setup script for EnviaFolha PostgreSQL database
-- This script runs automatically when the container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'America/Sao_Paulo';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, action);
CREATE INDEX IF NOT EXISTS idx_payroll_sends_month ON payroll_sends(month);
CREATE INDEX IF NOT EXISTS idx_payroll_sends_status ON payroll_sends(status);
CREATE INDEX IF NOT EXISTS idx_communication_sends_status ON communication_sends(status);
CREATE INDEX IF NOT EXISTS idx_communication_recipients_status ON communication_recipients(status);

-- Insert default system settings
INSERT INTO system_settings (key, value, data_type, description, category, is_public) VALUES
('app_name', 'Sistema de Envio RH v2.0', 'string', 'Nome da aplicação', 'general', 'true'),
('app_version', '2.0.0', 'string', 'Versão da aplicação', 'general', 'true'),
('max_file_size', '26214400', 'integer', 'Tamanho máximo de arquivo em bytes (25MB)', 'uploads', 'false'),
('allowed_file_types', '["pdf", "jpg", "jpeg", "png"]', 'json', 'Tipos de arquivo permitidos', 'uploads', 'false'),
('whatsapp_delay_min', '20', 'integer', 'Delay mínimo entre mensagens em segundos', 'whatsapp', 'false'),
('whatsapp_delay_max', '40', 'integer', 'Delay máximo entre mensagens em segundos', 'whatsapp', 'false'),
('jwt_expiry_minutes', '30', 'integer', 'Tempo de expiração do token JWT em minutos', 'auth', 'false'),
('require_cpf_validation', 'true', 'boolean', 'Exigir validação de CPF', 'validation', 'false'),
('require_phone_validation', 'true', 'boolean', 'Exigir validação de telefone', 'validation', 'false'),
('audit_retention_days', '365', 'integer', 'Dias para retenção de logs de auditoria', 'audit', 'false')
ON CONFLICT (key) DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for automatic updated_at updating (applied after migration)
-- These will be applied by the migration script after tables are created