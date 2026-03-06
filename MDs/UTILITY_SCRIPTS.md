# Scripts Úteis - Sistema de Envio RH

## 📋 Visão Geral

A funcionalidade **Scripts Úteis** permite que administradores executem scripts de manutenção e correção de dados diretamente pela interface web, sem necessidade de acesso SSH ao servidor ou execução manual de comandos.

## 🎯 Acesso

**Configurações → Scripts Úteis** (aba disponível apenas para administradores)

## 🛠️ Scripts Disponíveis

### 1. Corrigir Zeros à Esquerda nas Matrículas

**ID:** `fix_unique_id_zeros`  
**Categoria:** Colaboradores  
**Nível de Risco:** Médio  

#### Descrição
Corrige matrículas de colaboradores que perderam os zeros à esquerda durante importações Excel. 

#### Problema Comum
O Excel remove automaticamente zeros à esquerda ao abrir arquivos CSV. Exemplo:
- Matrícula correta: `005900123` (9 dígitos)
- Excel converte para: `5900123` (7 dígitos)
- Sistema espera: `005900123`

#### Lógica de Correção
```
SE matrícula começa com '59' OU '60' E tem 7 caracteres:
    Adicionar '00' à esquerda
    Exemplo: '5900123' → '005900123'
```

#### Como Usar

1. **Preview (Recomendado)**
   - Clique em "🔍 Preview"
   - Visualize quais colaboradores serão afetados
   - Veja a lista de alterações antes de aplicar
   - Mostra até 50 registros como exemplo

2. **Executar**
   - Clique em "⚡ Executar"
   - Confirme a operação no popup
   - Aguarde processamento
   - Veja resultado com quantidade de registros alterados

#### Resultado

**Preview:**
```json
{
  "affected_count": 15,
  "preview_items": [
    {
      "full_name": "João Silva",
      "old_id": "5900123",
      "new_id": "005900123"
    }
  ],
  "details": {
    "already_correct": 237,
    "to_fix": 15,
    "unexpected_format": 0
  }
}
```

**Execução:**
```json
{
  "message": "Correção concluída com sucesso! 15 colaboradores atualizados.",
  "affected_count": 15,
  "details": {
    "corrected": 15,
    "conflicts": 0
  }
}
```

#### Segurança
- ✅ Verifica conflitos (se novo ID já existe)
- ✅ Rollback automático em caso de erro
- ✅ Log completo no sistema
- ✅ Apenas administradores podem executar
- ✅ Confirmação obrigatória antes de executar

## 🔧 Arquitetura Técnica

### Frontend
```
frontend/src/pages/UtilityScripts.jsx
```
- Interface React com cards para cada script
- Botões de Preview e Execução
- Exibição de resultados em tempo real
- Loading states e feedback visual

### Backend
```
backend/app/services/utility_scripts.py
backend/main_legacy.py (rotas HTTP)
```

#### Endpoints

**GET** `/api/v1/scripts/{script_id}/preview`
- Retorna preview das alterações
- Não modifica dados
- Requer autenticação de admin

**POST** `/api/v1/scripts/{script_id}`
- Executa o script
- Modifica dados no banco
- Requer autenticação de admin
- Registra log de auditoria

### Service Layer
```python
class UtilityScriptsService:
    def preview_script(self, script_id: str) -> Dict[str, Any]
    def execute_script(self, script_id: str) -> Dict[str, Any]
```

## 📝 Adicionando Novos Scripts

### 1. Frontend - Adicionar ao Array de Scripts

Em `frontend/src/pages/UtilityScripts.jsx`:

```javascript
const scripts = [
  {
    id: 'meu_novo_script',
    name: 'Nome do Script',
    icon: '🔧',
    description: 'Descrição do que o script faz',
    category: 'Categoria',
    action: 'fix',
    confirmMessage: 'Mensagem de confirmação',
    dangerLevel: 'low', // low, medium, high
  },
  // ... outros scripts
];
```

### 2. Backend - Implementar Lógica

Em `backend/app/services/utility_scripts.py`:

```python
class UtilityScriptsService:
    def __init__(self, db: Session):
        self.db = db
        self.scripts = {
            'meu_novo_script': self._meu_novo_script
        }
        self.preview_handlers = {
            'meu_novo_script': self._preview_meu_novo_script
        }
    
    def _preview_meu_novo_script(self) -> Dict[str, Any]:
        """Preview do novo script"""
        # Análise sem modificações
        return {
            'message': 'Preview message',
            'affected_count': 0,
            'preview_items': []
        }
    
    def _meu_novo_script(self) -> Dict[str, Any]:
        """Execução do novo script"""
        # Modificar dados
        self.db.commit()
        return {
            'message': 'Success message',
            'affected_count': 0
        }
```

## ⚠️ Melhores Práticas

### Para Administradores
1. **SEMPRE** use Preview antes de Executar
2. Faça backup do banco antes de scripts de risco alto/médio
3. Execute em horários de baixo movimento
4. Verifique logs após execução
5. Teste primeiro em ambiente de desenvolvimento

### Para Desenvolvedores
1. Implemente validação de conflitos
2. Use transações (rollback em erro)
3. Registre logs detalhados
4. Limite preview a 50 registros
5. Adicione confirmação para operações destrutivas
6. Classifique corretamente o nível de risco

## 🔐 Segurança

- ✅ Apenas usuários com `is_admin=true` podem acessar
- ✅ Autenticação JWT obrigatória
- ✅ Logs de auditoria completos
- ✅ Transações com rollback automático
- ✅ Validação de conflitos antes de modificar
- ✅ Confirmação dupla (popup + botão)

## 📊 Monitoramento

Todos os scripts executados são registrados em:
- **Tabela:** `system_logs`
- **Event Type:** `utility_script_executed`
- **Details:** Inclui script_id, resultado e user_id

### Consultar Execuções
```sql
SELECT 
    created_at,
    description,
    details->>'script_id' AS script,
    details->>'affected_count' AS registros,
    username
FROM system_logs sl
LEFT JOIN users u ON u.id = (details->>'user_id')::integer
WHERE event_type = 'utility_script_executed'
ORDER BY created_at DESC;
```

## 🐛 Troubleshooting

### Erro: "Script não encontrado"
- Verifique se o `script_id` está registrado em `UtilityScriptsService`
- Confirme que tanto preview quanto execução estão implementados

### Erro: "Apenas administradores podem executar"
- Verifique se `user.is_admin = true` no banco
- Confirme que o token JWT é válido

### Script executa mas não altera dados
- Verifique se `db.commit()` está sendo chamado
- Confirme que não há exceções silenciosas
- Verifique logs do sistema

### Conflitos detectados
- Scripts param automaticamente quando detectam conflitos
- Resolva manualmente os conflitos antes de reexecutar
- Use preview para entender o problema

## 📚 Exemplos de Uso

### Cenário 1: Correção após Importação Excel
```
1. Usuário importa 252 colaboradores via Excel
2. Excel remove zeros à esquerda de 15 matrículas
3. Admin acessa Configurações → Scripts Úteis
4. Clica "Preview" no script de correção
5. Vê lista de 15 colaboradores afetados
6. Clica "Executar"
7. Confirma no popup
8. Sistema corrige e mostra resultado: "15 colaboradores atualizados"
```

### Cenário 2: Validação de Integridade
```
1. Admin suspeita de problemas em matrículas
2. Executa Preview sem aplicar mudanças
3. Resultado: "237 corretos, 0 para corrigir"
4. Confirma que não há problemas
```

## 🚀 Futuras Melhorias

- [ ] Script para validar telefones (formato brasileiro)
- [ ] Script para remover CPFs duplicados
- [ ] Script para normalizar nomes (Title Case)
- [ ] Script para limpar emails inválidos
- [ ] Agendamento de scripts (cron-like)
- [ ] Export de preview em Excel
- [ ] Histórico de execuções na UI
- [ ] Rollback de última execução
