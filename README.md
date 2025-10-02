# 🚀 Sistema de Envio RH v2.0

Sistema completo para envio automatizado de holerites e comunicados via WhatsApp usando Evolution API.

## ✨ Funcionalidades

### 🔐 **Autenticação e Segurança**
- Login JWT com controle de sessão
- Controle de acesso por usuário
- Logs de auditoria completos
- Sistema de permissões (admin/usuário)

### 👥 **Gestão de Colaboradores**
- Cadastro unificado de colaboradores
- Validação internacional de telefones
- Importação via planilha Excel
- Verificação de WhatsApp disponível

### 📄 **Envio de Holerites**
- Upload e segmentação automática de PDFs
- Proteção com senha (4 primeiros dígitos do CPF)
- **Mensagem única otimizada** (redução de 50% no tempo)
- Movimentação automática de arquivos enviados

### 📢 **Envio de Comunicados**
- Suporte a múltiplos formatos (PDF, imagens)
- Seleção flexível de destinatários
- Templates de mensagem personalizáveis
- Agendamento de envios

### 📊 **Dashboard e Analytics**
- Gráficos de performance em tempo real
- Relatórios de sucesso/falha
- Histórico completo de envios
- Estatísticas por departamento

### 🛠️ **Recursos Avançados**
- Sistema de backup automático
- Retry inteligente com delays
- Monitoramento de sistema
- API REST completa

## 🏗️ Arquitetura

### **Visão Geral**
- **Frontend**: Interface web em React para interação do usuário
- **Backend**: API em Node.js com Express para lógica de negócio e integração com Evolution API
- **Banco de Dados**: MongoDB para armazenamento de dados dos colaboradores e logs de envio
- **Autenticação**: JWT (JSON Web Tokens) para controle de acesso seguro

### **Fluxo de Dados**
1. O usuário faz o upload do holerite em PDF.
2. O sistema segmenta o PDF e extrai os dados necessários.
3. Os dados são validados e um holerite protegido por senha é gerado.
4. O holerite é enviado ao colaborador via WhatsApp, utilizando a API da Evolution.
5. O status do envio é atualizado no sistema e um relatório é gerado.

## 🚀 Como Usar

### 1. **Executar a Interface**
```bash
npm start
```

### 2. **Fluxo de Trabalho**
1. **Login**: Acesse com suas credenciais
2. **Upload**: Envie os arquivos PDF de holerites
3. **Segmentação**: Clique em "Segmentar holerites"
4. **Verificação**: Confira a prévia dos holerites e destinatários
5. **Envio**: Clique em "Enviar holerites"
6. **Acompanhamento**: Monitore o progresso no dashboard
7. **Relatório**: Acesse relatórios detalhados de envio

### 3. **Monitoramento**
- **Dashboard**: Acompanhe métricas de desempenho e status de envios
- **Logs**: Consulte logs de auditoria para rastrear atividades
- **Notificações**: Receba alertas sobre falhas ou problemas no envio

## 📊 Benefícios das Melhorias

### **Controle e Segurança**
- ❌ **Antes**: Sistema sem controle de acesso
- ✅ **Agora**: Autenticação e autorização de usuários

### **Gestão de Colaboradores**
- ❌ **Antes**: Cadastro e validação manuais
- ✅ **Agora**: Processo automatizado e validado

### **Envio de Holerites**
- ❌ **Antes**: Envio sem proteção e sem otimização
- ✅ **Agora**: Holerites protegidos por senha e envio otimizado

### **Envio de Comunicados**
- ❌ **Antes**: Sem suporte a comunicados
- ✅ **Agora**: Envio de comunicados em múltiplos formatos

### **Dashboard e Analytics**
- ❌ **Antes**: Sem visibilidade sobre envios
- ✅ **Agora**: Dashboard com gráficos e relatórios detalhados

### **Recursos Avançados**
- ❌ **Antes**: Sem recursos avançados de envio
- ✅ **Agora**: Sistema de backup, retry inteligente e monitoramento

## 🛠️ Arquivos Modificados

1. **`app.py`**: Interface React com controle de execução e painel de acompanhamento
2. **`send_holerites_evolution.py`**: Script principal com todas as melhorias
3. **`status_manager.py`**: Novo módulo para gerenciamento de status (NOVO)

## 🔍 Resolução de Problemas

### **Execução Travada**
- Use o botão "Parar Execução (Emergência)" na interface
- Ou delete o arquivo `execution_status.json`

### **Relatório não enviado**
- Verifique se `ADMIN_WHATSAPP_NUMBER` está configurado no `.env`
- Confirme se o número está no formato internacional (5511999999999)

### **Status não atualiza**
- Clique no botão "Atualizar Status"
- Verifique se o arquivo `execution_status.json` existe

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs de execução
2. Confirme as configurações do arquivo `.env`
3. Teste a conectividade com a Evolution API
4. Verifique as permissões de pasta

---

# 🚀 Prováveis Melhorias Futuras

## 💡 Novas Funcionalidades e Aprimoramentos

### 1. **Histórico de Envios Detalhado**
- **Descrição**: Armazenar um histórico persistente de todas as execuções, incluindo relatórios de sucesso/falha, data/hora e usuário que iniciou o envio. Isso permitiria consultar envios passados.
- **Benefícios**: Auditoria completa, rastreabilidade e capacidade de reenvio de lotes específicos em caso de falha.
- **Considerações**: Necessitaria de um banco de dados (SQLite, PostgreSQL) para persistência dos dados.

### 2. **Agendamento de Envios**
- **Descrição**: Permitir que o usuário agende o envio de holerites para uma data e hora futuras, ou em intervalos recorrentes (ex: todo dia 5 do mês).
- **Benefícios**: Automação completa do processo, reduzindo a necessidade de intervenção manual.
- **Considerações**: Requer um scheduler (ex: APScheduler, Celery) e um processo em background para executar as tarefas agendadas.

### 3. **Configuração de Mensagens Dinâmicas**
- **Descrição**: Oferecer uma interface na Streamlit para que o usuário possa editar os textos das mensagens (saudação, anexo) e adicionar variáveis dinâmicas (ex: `{{nome_colaborador}}`, `{{mes_referencia}}`).
- **Benefícios**: Maior flexibilidade e personalização das comunicações sem a necessidade de alterar o código.

### 4. **Suporte a Múltiplos Meses/Anos**
- **Descrição**: Atualmente, o nome do arquivo PDF inclui `junho_2025`. Permitir que o usuário selecione o mês e ano de referência na interface, e que o sistema ajuste os nomes dos arquivos e mensagens automaticamente.
- **Benefícios**: Torna o sistema mais genérico e reutilizável para diferentes períodos.

### 5. **Validação de Dados Aprimorada**
- **Descrição**: Implementar validações mais robustas para o arquivo `Colaboradores.xlsx` (ex: verificar formato do telefone, existência de IDs únicos) e para os PDFs segmentados antes do envio.
- **Benefícios**: Reduz erros durante o envio e melhora a qualidade dos dados.

### 6. **Interface de Usuário Aprimorada (UI/UX)**
- **Descrição**: Melhorar a experiência do usuário com feedback visual mais rico, animações, e talvez um design mais moderno para a interface Streamlit.
- **Benefícios**: Torna o sistema mais agradável e intuitivo de usar.

### 7. **Notificações por E-mail**
- **Descrição**: Além do WhatsApp, enviar o relatório final de envio também por e-mail para um ou mais endereços configurados.
- **Benefícios**: Redundância nas notificações e opção para usuários que preferem e-mail.


**Desenvolvido com ❤️ para otimizar o processo de envio de holerites**
- **Benefícios**: Torna o sistema mais genérico e reutilizável para diferentes períodos.

### 6. **Validação de Dados Aprimorada**
- **Descrição**: Implementar validações mais robustas para o arquivo `Colaboradores.xlsx` (ex: verificar formato do telefone, existência de IDs únicos) e para os PDFs segmentados antes do envio.
- **Benefícios**: Reduz erros durante o envio e melhora a qualidade dos dados.

### 7. **Interface de Usuário Aprimorada (UI/UX)**
- **Descrição**: Melhorar a experiência do usuário com feedback visual mais rico, animações, e talvez um design mais moderno para a interface Streamlit.
- **Benefícios**: Torna o sistema mais agradável e intuitivo de usar.

### 8. **Notificações por E-mail**
- **Descrição**: Além do WhatsApp, enviar o relatório final de envio também por e-mail para um ou mais endereços configurados.
- **Benefícios**: Redundância nas notificações e opção para usuários que preferem e-mail.


**Desenvolvido com ❤️ para otimizar o processo de envio de holerites**
