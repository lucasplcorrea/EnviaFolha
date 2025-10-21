# 📊 Sistema de Importação e Logs - Documentação

## ✅ Melhorias Implementadas

### 1. 📥 Sistema de Importação Aprimorado

#### **Validação de Campos Obrigatórios**
O sistema agora valida **4 campos obrigatórios** na importação:
- `unique_id` - Código único/matrícula do colaborador
- `full_name` - Nome completo
- `cpf` - CPF (11 dígitos)
- `phone_number` - Telefone com DDD

#### **Campos Opcionais Suportados**
- `email` - Email do colaborador
- `department` - Departamento
- `position` - Cargo
- `birth_date` - Data de nascimento (formato: AAAA-MM-DD ou DD/MM/AAAA)
- `sex` - Sexo (M/F/Outro)
- `marital_status` - Estado civil
- `admission_date` - Data de admissão (formato: AAAA-MM-DD ou DD/MM/AAAA)
- `contract_type` - Tipo de contrato (CLT/PJ/Estágio/etc)
- `status_reason` - Observações/motivo de status

#### **Arquivo Modelo Excel**
Criado arquivo `modelo_importacao_colaboradores.xlsx` com:
- ✅ Todas as colunas já configuradas
- ✅ Exemplo de linha preenchida
- ✅ Disponível para download no frontend
- ✅ Localização: `/frontend/public/modelo_importacao_colaboradores.xlsx`

### 2. 🔄 Diferenciação entre Criação e Atualização

#### **Lógica de Importação**
```python
if employee.unique_id já existe:
    ➡️ ATUALIZAR colaborador existente
    ✅ Mantém ID do banco
    ✅ Atualiza apenas campos fornecidos
else:
    ➡️ CRIAR novo colaborador
    ✅ Gera novo ID no banco
    ✅ Preenche todos os campos
```

#### **Feedback Detalhado**
O resultado da importação agora retorna:
- `created` - Quantidade de colaboradores **criados**
- `updated` - Quantidade de colaboradores **atualizados**
- `created_list[]` - Lista com detalhes dos **criados** (unique_id, nome, linha)
- `updated_list[]` - Lista com detalhes dos **atualizados** (unique_id, nome, linha)
- `errors[]` - Lista de erros (linha, mensagem, dados)

#### **Interface do Usuário**
Modal de importação mostra:
- ✅ Resumo: "X novos criados, Y atualizados"
- ✅ Lista expansível de colaboradores criados (com ícone 📝)
- ✅ Lista expansível de colaboradores atualizados (com ícone 🔄)
- ✅ Lista expansível de erros (com ícone ❌)
- ✅ Toast notifications diferenciadas

### 3. 📝 Sistema de Logs Completo

#### **Tabela `system_logs`**
Nova tabela criada com os campos:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer | ID único do log |
| `level` | Enum | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `category` | Enum | SYSTEM, AUTH, EMPLOYEE, IMPORT, PAYROLL, COMMUNICATION, WHATSAPP, DATABASE, API |
| `message` | Text | Mensagem principal |
| `details` | Text | JSON com detalhes adicionais |
| `user_id` | Integer | ID do usuário (se aplicável) |
| `username` | String | Nome do usuário |
| `entity_type` | String | Tipo de entidade (Employee, Payroll, etc) |
| `entity_id` | String | ID da entidade afetada |
| `ip_address` | String(45) | IP da requisição |
| `user_agent` | String(500) | User agent do navegador |
| `request_method` | String(10) | GET, POST, PUT, DELETE |
| `request_path` | String(500) | Caminho da requisição |
| `created_at` | DateTime | Timestamp do log |

#### **LoggingService**
Novo serviço em `backend/app/services/logging_service.py`:

**Métodos principais:**
```python
# Métodos por nível
logger.debug(category, message, **kwargs)
logger.info(category, message, **kwargs)
logger.warning(category, message, **kwargs)
logger.error(category, message, **kwargs)
logger.critical(category, message, **kwargs)

# Métodos específicos
logger.log_auth(message, user_id, username)
logger.log_employee_action(action, employee_id, user_id)
logger.log_import(message, details, user_id)
logger.log_payroll(message, payroll_id)
logger.log_communication(message, communication_id)
logger.log_whatsapp(message, details)

# Consulta
logger.get_logs(level, category, user_id, limit, offset)
logger.get_recent_logs(limit=50)
```

#### **Eventos Logados na Importação**
1. **Início da importação**
   - Categoria: `IMPORT`
   - Nível: `INFO`
   - Detalhes: `{'total_rows': N}`

2. **Colaborador criado**
   - Categoria: `EMPLOYEE`
   - Nível: `INFO`
   - Mensagem: "Colaborador criado via importação: [nome]"
   - Detalhes: unique_id, dados completos, linha

3. **Colaborador atualizado**
   - Categoria: `EMPLOYEE`
   - Nível: `INFO`
   - Mensagem: "Colaborador atualizado via importação: [nome]"
   - Detalhes: unique_id, dados antigos, dados novos, linha

4. **Erro na importação**
   - Categoria: `IMPORT`
   - Nível: `ERROR`
   - Mensagem: "Erro ao importar linha X: [erro]"
   - Detalhes: linha, erro, dados

5. **Conclusão da importação**
   - Categoria: `IMPORT`
   - Nível: `INFO`
   - Mensagem: "Importação concluída: X criados, Y atualizados, Z erros"
   - Detalhes: listas completas, primeiros 10 erros

## 📖 Como Usar

### **Importação de Colaboradores**

1. **Baixar modelo Excel**
   - Acesse: Colaboradores → "Importar Excel"
   - Clique em "Baixar Modelo Excel"
   - Arquivo: `modelo_importacao_colaboradores.xlsx`

2. **Preencher dados**
   - Abra o arquivo no Excel/LibreOffice
   - Preencha os campos obrigatórios (unique_id, full_name, cpf, phone_number)
   - Preencha campos opcionais conforme necessário
   - **Dica**: Use unique_id existente para ATUALIZAR, novo para CRIAR

3. **Importar arquivo**
   - Clique em "Importar Excel"
   - Selecione o arquivo preenchido
   - Aguarde processamento
   - Visualize resultado detalhado:
     - ✅ Quantos foram criados
     - 🔄 Quantos foram atualizados
     - ❌ Erros encontrados

4. **Verificar logs** (futuro)
   - Acesse painel de Logs do Sistema
   - Filtre por categoria: IMPORT ou EMPLOYEE
   - Veja histórico completo com usuário e timestamp

### **Consultar Logs (Backend)**

```python
from app.services.logging_service import LoggingService
from app.models.system_log import LogLevel, LogCategory

# Criar serviço
logger = LoggingService(db_session)

# Buscar logs de importação
import_logs = logger.get_logs(
    category=LogCategory.IMPORT,
    limit=100
)

# Buscar logs de um usuário específico
user_logs = logger.get_logs(
    user_id=1,
    limit=50
)

# Buscar apenas erros
error_logs = logger.get_logs(
    level=LogLevel.ERROR,
    limit=20
)

# Logs recentes (últimos 50)
recent = logger.get_recent_logs(50)
```

## 🔧 Melhorias Técnicas

### **Backend**

#### `DataImportService` (`backend/app/services/data_import.py`)
- ✅ Validação completa de campos obrigatórios
- ✅ Diferenciação entre criação e atualização
- ✅ Logs detalhados de todas as operações
- ✅ Retorno estruturado com listas de criados/atualizados
- ✅ Tratamento robusto de erros

#### Novos Arquivos:
- `backend/app/models/system_log.py` - Model de logs
- `backend/app/services/logging_service.py` - Serviço de logging
- `frontend/public/modelo_importacao_colaboradores.xlsx` - Arquivo modelo

### **Frontend**

#### `Employees.jsx` (`frontend/src/pages/Employees.jsx`)
- ✅ Modal expandido com instruções detalhadas
- ✅ Link para download do modelo Excel
- ✅ Indicação clara de campos obrigatórios vs opcionais
- ✅ Dica sobre atualização vs criação
- ✅ Resultado detalhado com listas expansíveis
- ✅ Badges coloridos (verde=criado, amarelo=atualizado, vermelho=erro)
- ✅ Toast notifications diferenciadas

## 🎯 Próximos Passos

### **1. Interface de Visualização de Logs**
Criar página no frontend para:
- [ ] Listar logs do sistema
- [ ] Filtrar por categoria, nível, usuário, data
- [ ] Exportar logs para Excel/CSV
- [ ] Dashboard de atividades

### **2. Expandir Logging**
Adicionar logs para:
- [ ] Autenticação (login, logout, falhas)
- [ ] Envio de holerites (sucesso, falha, detalhes WhatsApp)
- [ ] Envio de comunicados
- [ ] Alterações em colaboradores (via interface)
- [ ] Alterações em usuários
- [ ] Operações de bulk edit/delete

### **3. Alertas e Monitoramento**
- [ ] Email em caso de erros críticos
- [ ] Dashboard de saúde do sistema
- [ ] Métricas de uso (importações por dia, envios, etc)

### **4. Auditoria Completa**
- [ ] Rastreamento de todas as mudanças de dados
- [ ] Histórico de versões (quem alterou, quando, o quê)
- [ ] Compliance e LGPD

## 📊 Exemplo de Uso Completo

### **Cenário: Importar 50 colaboradores, sendo 30 novos e 20 atualizações**

1. **Preparação:**
   ```
   - Baixar modelo_importacao_colaboradores.xlsx
   - Preencher 50 linhas (30 com unique_id novos, 20 com existentes)
   - Salvar arquivo como "colaboradores_outubro_2025.xlsx"
   ```

2. **Importação:**
   ```
   - Acessar Colaboradores → Importar Excel
   - Selecionar "colaboradores_outubro_2025.xlsx"
   - Aguardar processamento (~5s)
   ```

3. **Resultado:**
   ```
   ✅ Importação concluída
   • 30 novos colaboradores criados
   • 20 colaboradores atualizados
   
   📝 Ver 30 colaboradores criados
   🔄 Ver 20 colaboradores atualizados
   ```

4. **Logs Gravados:**
   ```sql
   -- No banco PostgreSQL (tabela system_logs):
   
   INSERT INTO system_logs (level, category, message, details, user_id, username)
   VALUES 
     ('INFO', 'IMPORT', 'Iniciando importação de 50 colaboradores', '{"total_rows": 50}', 1, 'admin'),
     ('INFO', 'EMPLOYEE', 'Colaborador criado via importação: João Silva', '{"unique_id": "12345", ...}', 1, 'admin'),
     ('INFO', 'EMPLOYEE', 'Colaborador atualizado via importação: Maria Santos', '{"unique_id": "67890", ...}', 1, 'admin'),
     ...
     ('INFO', 'IMPORT', 'Importação concluída: 30 criados, 20 atualizados, 0 erros', '{"created": 30, ...}', 1, 'admin');
   ```

## 🔒 Rastreabilidade e Compliance

### **Benefícios do Sistema de Logs**

1. **Auditoria Completa**
   - Quem fez o quê e quando
   - Histórico imutável de ações
   - Rastreamento de mudanças

2. **Debugging e Suporte**
   - Identificar erros rapidamente
   - Reproduzir problemas
   - Entender fluxo de operações

3. **Compliance LGPD**
   - Registrar acesso a dados pessoais
   - Demonstrar controles de segurança
   - Relatórios de atividades

4. **Métricas de Negócio**
   - Quantidade de importações
   - Taxa de sucesso/erro
   - Usuários mais ativos
   - Picos de uso

## 📞 Suporte

Para dúvidas ou problemas:
1. Consultar logs do sistema
2. Verificar console do navegador (F12)
3. Verificar logs do backend (terminal)
4. Consultar tabela `system_logs` no banco

---

**Última atualização:** 21 de outubro de 2025  
**Versão:** 2.0  
**Status:** ✅ Implementado e Testado
