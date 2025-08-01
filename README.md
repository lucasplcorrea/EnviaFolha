# 📄 Sistema de Envio de Holerites

## 🚀 Funcionalidades

### 1. **Controle de Execução e Status em Tempo Real**
- ✅ **Prevenção de duplicidade**: O sistema impede que múltiplas execuções sejam iniciadas simultaneamente
- ✅ **Acompanhamento em tempo real**: Interface mostra progresso atual, funcionário sendo processado e estatísticas
- ✅ **Barra de progresso**: Visualização clara do percentual de conclusão
- ✅ **Botão de emergência**: Possibilidade de interromper execução em caso de necessidade

### 2. **Painel de Acompanhamento de Destinatários**
- ✅ **Status detalhado por funcionário**: Cada colaborador tem seu status individual (Aguardando, Processando, Enviado, Falha)
- ✅ **Filtros avançados**: Busca por nome e filtro por status de envio
- ✅ **Informações completas**: Telefone, arquivo esperado, disponibilidade e última atualização
- ✅ **Interface expansível**: Detalhes de cada funcionário em painéis organizados

### 3. **Movimentação Automática de Arquivos**
- ✅ **Pasta "enviados"**: Holerites enviados com sucesso são automaticamente movidos para pasta separada
- ✅ **Organização automática**: Mantém a pasta principal limpa e organizada
- ✅ **Log de movimentação**: Registra quando arquivos são movidos

### 4. **Sistema de Log via WhatsApp**
- ✅ **Relatório automático**: Ao final da execução, um relatório é enviado via WhatsApp
- ✅ **Resumo executivo**: Mensagem com estatísticas principais (sucessos, falhas, total)
- ✅ **Arquivo detalhado**: Relatório completo em arquivo de texto com lista de todos os funcionários
- ✅ **Configuração flexível**: Número do administrador configurável via variável de ambiente

### 5. **Otimização de Mensagens**
- ✅ **Redução de 3 para 2 mensagens**: Combinou saudação e finalização em uma única mensagem
- ✅ **Delays otimizados**: Tempos de espera reduzidos para acelerar o processo
- ✅ **Caption informativo**: Arquivo enviado com legenda explicativa
- ✅ **Processo mais eficiente**: Redução significativa no tempo total de execução

## 🔧 Configuração

### Variáveis de Ambiente Necessárias

Crie um arquivo `.env` na pasta do projeto com as seguintes variáveis:

```env
# Configurações da Evolution API (obrigatórias)
EVOLUTION_SERVER_URL=https://sua-api.evolution.com
EVOLUTION_API_KEY=sua_chave_de_api
EVOLUTION_INSTANCE_NAME=nome_da_sua_instancia

# Configuração do administrador para relatórios (opcional)
ADMIN_WHATSAPP_NUMBER=5511999999999

# Configuração de retomada (opcional)
START_FROM_INDEX=0
```

### Arquivos Necessários

1. **Colaboradores.xlsx**: Planilha com dados dos funcionários
   - Colunas: `ID_Unico`, `Nome_Colaborador`, `Telefone`
   O `ID_Unico` é composto de 9 dígitos, 4 referentes a empresa e 5 referentes a matrícula do colaborador, adotando o seguinte padrão EEEEMMMMM.

2. **Estrutura de Pastas**:
   ```
   projeto/
   ├── uploads/              # PDFs originais
   ├── holerites_formatados_final/  # Holerites segmentados
   ├── enviados/             # Holerites enviados (criada automaticamente)
   ├── Colaboradores.xlsx
   ├── .env
   ├── app.py
   ├── send_holerites_evolution.py
   ├── status_manager.py
   └── manus.py
   ```

## 🚀 Como Usar

### 1. **Executar a Interface**
```bash
streamlit run app.py
```

### 2. **Fluxo de Trabalho**
1. **Upload**: Envie os arquivos PDF de holerites
2. **Segmentação**: Clique em "Segmentar todos os holerites enviados"
3. **Verificação**: Confira a prévia dos destinatários
4. **Envio**: Clique em "Enviar holerites via Evolution API"
5. **Acompanhamento**: Monitore o progresso em tempo real
6. **Relatório**: Receba o relatório final via WhatsApp

### 3. **Monitoramento**
- **Status de Execução**: Acompanhe o progresso na interface principal
- **Painel de Destinatários**: Veja o status individual de cada funcionário
- **Filtros**: Use os filtros para encontrar funcionários específicos
- **Atualização**: Clique em "Atualizar Status" para ver as últimas informações

## 📊 Benefícios das Melhorias

### **Controle e Segurança**
- ❌ **Antes**: Possibilidade de execuções duplicadas
- ✅ **Agora**: Controle rigoroso de execução única

### **Visibilidade**
- ❌ **Antes**: Sem visibilidade do progresso
- ✅ **Agora**: Acompanhamento completo em tempo real

### **Organização**
- ❌ **Antes**: Arquivos misturados após envio
- ✅ **Agora**: Separação automática de arquivos enviados

### **Relatórios**
- ❌ **Antes**: Apenas logs locais
- ✅ **Agora**: Relatório automático via WhatsApp

### **Performance**
- ❌ **Antes**: 3 mensagens por funcionário
- ✅ **Agora**: 2 mensagens por funcionário (até 33% mais rápido)

## 🛠️ Arquivos Modificados

1. **`app.py`**: Interface Streamlit com controle de execução e painel de acompanhamento
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

**Desenvolvido com ❤️ para otimizar o processo de envio de holerites**
