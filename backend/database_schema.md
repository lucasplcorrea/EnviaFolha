# Schema do Banco de Dados PostgreSQL

## Visão Geral
Sistema de Envio RH com PostgreSQL - Estrutura completa para gestão de colaboradores, usuários e auditoria.

## Tabelas Principais

### 1. **users** - Usuários do Sistema
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);
```

### 2. **employees** - Colaboradores
```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    unique_id VARCHAR(20) UNIQUE NOT NULL, -- ID único do colaborador (ex: CPF parcial)
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone_number VARCHAR(20),
    department VARCHAR(100),
    position VARCHAR(100),
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);
```

### 3. **audit_logs** - Logs de Auditoria
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL, -- 'LOGIN', 'LOGOUT', 'SEND_PAYROLL', 'SEND_COMMUNICATION', etc.
    entity_type VARCHAR(50), -- 'employee', 'user', 'payroll', 'communication'
    entity_id INTEGER,
    details JSONB, -- Detalhes específicos da ação
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 4. **payroll_sends** - Histórico de Envios de Holerites
```sql
CREATE TABLE payroll_sends (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id),
    user_id INTEGER REFERENCES users(id), -- Quem enviou
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    month_year VARCHAR(10), -- '2025-10'
    phone_number VARCHAR(20),
    message_text TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    evolution_message_id VARCHAR(100),
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 5. **communication_sends** - Histórico de Comunicados
```sql
CREATE TABLE communication_sends (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id), -- Quem enviou
    title VARCHAR(255),
    message_text TEXT NOT NULL,
    attachment_filename VARCHAR(255),
    attachment_path VARCHAR(500),
    total_recipients INTEGER DEFAULT 0,
    successful_sends INTEGER DEFAULT 0,
    failed_sends INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sending', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

### 6. **communication_recipients** - Destinatários de Comunicados
```sql
CREATE TABLE communication_recipients (
    id SERIAL PRIMARY KEY,
    communication_send_id INTEGER REFERENCES communication_sends(id) ON DELETE CASCADE,
    employee_id INTEGER REFERENCES employees(id),
    phone_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    evolution_message_id VARCHAR(100),
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE
);
```

### 7. **system_settings** - Configurações do Sistema
```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Índices Recomendados

```sql
-- Índices para performance
CREATE INDEX idx_employees_unique_id ON employees(unique_id);
CREATE INDEX idx_employees_active ON employees(is_active);
CREATE INDEX idx_employees_department ON employees(department);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

CREATE INDEX idx_payroll_sends_employee_id ON payroll_sends(employee_id);
CREATE INDEX idx_payroll_sends_month_year ON payroll_sends(month_year);
CREATE INDEX idx_payroll_sends_status ON payroll_sends(status);

CREATE INDEX idx_communication_recipients_send_id ON communication_recipients(communication_send_id);
CREATE INDEX idx_communication_recipients_employee_id ON communication_recipients(employee_id);
```

## Triggers para Updated_at

```sql
-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para tabelas que precisam de updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_employees_updated_at BEFORE UPDATE ON employees 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Dados Iniciais (Seeds)

```sql
-- Usuário administrador padrão
INSERT INTO users (username, email, password_hash, full_name, is_admin) VALUES 
('admin', 'admin@empresa.com', '$2b$12$...', 'Administrador', TRUE);

-- Configurações iniciais do sistema
INSERT INTO system_settings (key, value, description) VALUES 
('EVOLUTION_SERVER_URL', '', 'URL do servidor Evolution API'),
('EVOLUTION_API_KEY', '', 'Chave da API Evolution'),
('EVOLUTION_INSTANCE_NAME', '', 'Nome da instância Evolution'),
('MAX_FILE_SIZE', '26214400', 'Tamanho máximo de arquivo em bytes (25MB)'),
('DEFAULT_MESSAGE_DELAY', '30', 'Delay padrão entre mensagens em segundos');
```

## Vantagens desta Estrutura

1. **Auditoria Completa**: Todos os logs de ações dos usuários
2. **Histórico de Envios**: Rastreamento completo de holerites e comunicados
3. **Escalabilidade**: Suporta múltiplos usuários e departamentos
4. **Integridade**: Foreign keys garantem consistência
5. **Performance**: Índices otimizados para consultas frequentes
6. **Flexibilidade**: JSONB para dados dinâmicos
7. **Configuração**: Sistema de configurações centralizadas