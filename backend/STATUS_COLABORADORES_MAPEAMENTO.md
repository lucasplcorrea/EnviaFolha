# Mapeamento de Status de Colaboradores

## Análise Completa dos CSVs - Janeiro 2026

### Status Identificados

Após análise de **63 arquivos CSV** nas pastas Empreendimentos e Infraestrutura, foram identificados os seguintes status:

#### 1. Trabalhando
- **Descrição**: `Trabalhando`
- **Ocorrências**: 64
- **Categoria**: Status ativo principal

#### 2. Férias
- **Descrição**: `Férias`
- **Ocorrências**: 42
- **Categoria**: Ausência temporária programada

#### 3. Afastados (7 variações)
Todos os status de afastamento identificados:

| Status | Ocorrências | Observações |
|--------|-------------|-------------|
| **Auxílio Doença até 15 dias** | 12 | Afastamento curto por doença |
| **Auxílio Doença** | 9 | Afastamento longo por doença |
| **Licença Maternidade - Ded. GPS** | 7 | Licença maternidade com dedução GPS |
| **Licença Remunerada** | 6 | Licença remunerada genérica |
| **Auxílio Doença dentro 60 dias** | 3 | Variação de auxílio doença |
| **Paternidade** | 2 | Licença paternidade |
| **Acidente Trabalho até 15 dias** | 2 | Afastamento por acidente de trabalho |

**Total de afastados**: 41 ocorrências em 7 tipos diferentes

#### 4. Desligados
- **Descrição**: `Demitido`
- **Ocorrências**: 41
- **Categoria**: Colaboradores desligados

---

## Implementação no Backend

### Query SQL Atualizada

O sistema foi atualizado para reconhecer **todas** as variações de afastamento:

```sql
COUNT(CASE WHEN 
    additional_data->>'Status' LIKE '%Afastado%' OR
    additional_data->>'Status' LIKE '%Auxílio Doença%' OR
    additional_data->>'Status' LIKE '%Auxilio Doenca%' OR
    additional_data->>'Status' LIKE '%Licença%' OR
    additional_data->>'Status' LIKE '%Licenca%' OR
    additional_data->>'Status' LIKE '%Paternidade%' OR
    additional_data->>'Status' LIKE '%Maternidade%' OR
    additional_data->>'Status' LIKE '%Acidente Trabalho%'
THEN 1 END) as afastados
```

### Arquivos Atualizados

- **backend/main_legacy.py**: 
  - Linha ~4038: Query de estatísticas gerais
  - Linha ~4342: Query de estatísticas filtradas
  - Linha ~4418: Query RankedStatus (múltiplos períodos)

### Benefícios da Implementação

✅ **Cobertura completa**: Todos os 7 tipos de afastamento são reconhecidos
✅ **Flexibilidade**: Usa `LIKE` para capturar variações de escrita (com/sem acento)
✅ **Manutenibilidade**: Padrão único aplicado em todas as queries
✅ **Precisão**: Colaboradores em licença maternidade agora aparecem corretamente como "Afastados"

---

## Exemplo de Caso Encontrado

**Arquivo**: `06-2025.CSV` (Empreendimentos)
**Colaboradora**: ANDREZA SILVEIRA SYPRIANY RAULINO
**Status**: `13;Licença Maternidade - Ded. GPS`

Antes da atualização: **Não era contabilizado** como afastado
Após atualização: **Corretamente identificado** como afastado

---

## Recomendações

### Padronização Futura
Considerar padronizar os tipos de licença no sistema de RH:
- Unificar "Auxílio Doença" e "Auxílio Doença até 15 dias"
- Criar categorias mais específicas para relatórios (INSS, Empresa, etc.)

### Monitoramento
- Executar `analyze_employee_status.py` periodicamente para identificar novos status
- Documentar qualquer novo tipo de afastamento encontrado

### Auditoria
Para validar a categorização atual:
```bash
cd backend
python analyze_employee_status.py
```

---

## Status de Implementação

- ✅ Script de análise criado (`analyze_employee_status.py`)
- ✅ Todos os status identificados e categorizados
- ✅ Backend atualizado com queries completas
- ✅ Frontend exibindo card "Contratados" para todos os períodos
- ✅ Documentação completa criada

**Última atualização**: 28/01/2026
