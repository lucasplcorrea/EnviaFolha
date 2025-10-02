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

## 🏗️ Arquitetura v2.0

### **Stack Tecnológica**
- **Frontend**: React + Tailwind CSS + React Router
- **Backend**: FastAPI + Python 3.13 + JSON Database
- **API WhatsApp**: Evolution API v2.2.2+
- **Autenticação**: JWT (JSON Web Tokens)

### **Estrutura do Projeto**
```
/enviafolha
│
├── /backend
│   ├── main.py               # Ponto de entrada da API FastAPI
│   ├── models.py             # Modelos de dados e validações
│   ├── routes.py             # Definição das rotas da API
│   ├── services.py           # Lógica de negócio e integração com Evolution API
│   ├── utils.py              # Funções utilitárias (ex: geração de senhas)
│   └── database.py           # Configuração da conexão com o banco de dados JSON
│
├── /frontend
│   ├── src
│   │   ├── App.js             # Componente principal do React
│   │   ├── index.js           # Ponto de entrada do React
│   │   ├── components         # Componentes reutilizáveis (ex: Botões, Inputs)
│   │   ├── pages              # Páginas da aplicação (ex: Login, Dashboard)
│   │   └── services           # Serviços para chamadas à API
│   │
│   └── public
│       ├── index.html         # HTML principal
│       └── favicon.ico        # Ícone da aplicação
│
├── .env                       # Variáveis de ambiente
├── .gitignore                 # Arquivos e pastas a serem ignorados pelo Git
├── README.md                  # Documentação do projeto
└── requirements.txt           # Dependências do Python
```

## 🚀 Como Usar

### 1. **Configuração Inicial**
- Clone o repositório: `git clone <URL_DO_REPOSITORIO>`
- Acesse a pasta do projeto: `cd enviafolha`
- Crie um ambiente virtual: `python -m venv venv`
- Ative o ambiente virtual:
  - Windows: `venv\Scripts\activate`
  - Linux/Mac: `source venv/bin/activate`
- Instale as dependências: `pip install -r requirements.txt`
- Renomeie o arquivo `.env.example` para `.env` e preencha as variáveis necessárias

### 2. **Executar a Aplicação**
- Para o backend:
  ```bash
  cd backend
  uvicorn main:app --reload
  ```
- Para o frontend:
  ```bash
  cd frontend
  npm install
  npm start
  ```

### 3. **Fluxo de Trabalho**
1. **Login**: Acesse com suas credenciais
2. **Upload**: Envie os arquivos PDF de holerites
3. **Segmentação**: Clique em "Segmentar holerites"
4. **Verificação**: Confira a prévia dos holerites e destinatários
5. **Envio**: Clique em "Enviar holerites"
6. **Acompanhamento**: Monitore o progresso no dashboard
7. **Relatório**: Acesse relatórios detalhados de envio

### 4. **Monitoramento**
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
