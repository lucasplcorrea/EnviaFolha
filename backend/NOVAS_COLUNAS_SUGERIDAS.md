# 📊 Análise de Novas Colunas para Indicadores RH

## 🔍 Resumo da Análise
- **Total de colunas no consolidado**: 277
- **Colunas já capturadas**: 30
- **Colunas disponíveis não capturadas**: 247

---

## 💡 PRINCIPAIS COLUNAS SUGERIDAS PARA ADICIONAR

### 1️⃣ **Horas Extras 100%** (Alta Prioridade)
Atualmente só capturamos HE 50%, mas existem HE 100%:

| Coluna | Uso |
|--------|-----|
| `Horas Extras 100% Diurnas` | Valor pago em HE 100% diurnas |
| `Horas Extras 100% Noturnas` | Valor pago em HE 100% noturnas |
| `Horas Extras 60% Diurnas` | Valor pago em HE 60% |

**Card sugerido**: "Horas Extras 100%" mostrando R$ total

---

### 2️⃣ **Adicional Noturno** (Alta Prioridade)
Muito relevante para análise de custo:

| Coluna | Uso |
|--------|-----|
| `Adicional Noturno` | Valor total pago |
| `Horas Normais Noturnas` | Quantidade de horas noturnas |
| `Redução Hora Noturna` | Benefício hora noturna reduzida |

**Cards sugeridos**:
- "Adicional Noturno (R$)" - valor total
- "Horas Noturnas Trabalhadas" - quantidade

---

### 3️⃣ **Horas Extras Noturnas 50%** (Média Prioridade)
Complementa as HE 50%:

| Coluna | Uso |
|--------|-----|
| `Horas Extras 50% Noturnas` | Valor de HE 50% no período noturno |

**Ação**: Adicionar ao card existente de HE 50% (somar diurnas + noturnas)

---

### 4️⃣ **Vale Transporte** (Média Prioridade)
Benefício importante:

| Coluna | Uso |
|--------|-----|
| `Vale Transporte (%)` | Desconto de vale transporte |
| `Devolução de Vale Transporte` | Devoluções/ajustes |

**Card sugerido**: "Vale Transporte" mostrando total descontado

---

### 5️⃣ **Gratificações** (Média Prioridade)
Remuneração variável:

| Coluna | Uso |
|--------|-----|
| `Gratificação de Função` | Gratificação principal |
| `Gratificação de Função 20%` | Gratificação adicional |

**Card sugerido**: "Gratificações" mostrando total pago

---

### 6️⃣ **Periculosidade** (Média Prioridade)
Adicional legal importante:

| Coluna | Uso |
|--------|-----|
| `Periculosidade` | Adicional de periculosidade |

**Card sugerido**: "Adicional de Periculosidade"

---

### 7️⃣ **Insalubridade** (Média Prioridade)
Adicional legal:

| Coluna | Uso |
|--------|-----|
| `Insalubridade S/Salário Mínimo` | Insalubridade calculada s/ salário mínimo |
| `Insalubridade S/Salário Normativo` | Insalubridade s/ normativo |

**Card sugerido**: "Adicional de Insalubridade"

---

### 8️⃣ **Faltas e Descontos** (Baixa Prioridade)
Útil para análise de absenteísmo:

| Coluna | Uso |
|--------|-----|
| `Horas Faltas Diurnas` | Quantidade de horas de falta |
| `Desconto Falta Mês Anterior` | Valor descontado por faltas |

**Card sugerido**: "Faltas e Absenteísmo"

---

### 9️⃣ **Empréstimo Consignado** (Baixa Prioridade)
| Coluna | Uso |
|--------|-----|
| `Empréstimo Crédito do Trabalhador` | Desconto de empréstimo |

---

### 🔟 **Pensão Judicial** (Baixa Prioridade)
| Coluna | Uso |
|--------|-----|
| `Pensão Judicial` | Desconto de pensão |
| `Pensão Judicial S/13o Salário` | Pensão sobre 13º |

---

## 🎯 PROPOSTA DE IMPLEMENTAÇÃO

### Fase 1 - Horas Extras (Implementar AGORA)
```python
# Adicionar ao CSV Processor
earnings_fields = {
    'HORAS_EXTRAS_100_DIURNAS': 'Horas Extras 100% Diurnas',
    'HORAS_EXTRAS_100_NOTURNAS': 'Horas Extras 100% Noturnas',
    'HORAS_EXTRAS_50_NOTURNAS': 'Horas Extras 50% Noturnas',
    'HORAS_EXTRAS_60_DIURNAS': 'Horas Extras 60% Diurnas',
}
```

**Novos Cards Frontend**:
- HE 100% (R$)
- HE 60% (R$)
- HE Noturnas (R$)

---

### Fase 2 - Adicional Noturno (Implementar AGORA)
```python
earnings_fields = {
    'ADICIONAL_NOTURNO': 'Adicional Noturno',
    'HORAS_NORMAIS_NOTURNAS': 'Horas Normais Noturnas',
    'REDUCAO_HORA_NOTURNA': 'Redução Hora Noturna',
}
```

**Novos Cards**:
- Adicional Noturno (R$)
- Horas Noturnas Trabalhadas

---

### Fase 3 - Benefícios Adicionais
```python
benefits_fields = {
    'VALE_TRANSPORTE': 'Vale Transporte (%)',
    'GRATIFICACAO_FUNCAO': ['Gratificação de Função', 'Gratificação de Função 20%'],
}
```

**Novos Cards**:
- Vale Transporte
- Gratificações

---

### Fase 4 - Adicionais Legais
```python
earnings_fields = {
    'PERICULOSIDADE': 'Periculosidade',
    'INSALUBRIDADE': ['Insalubridade S/Salário Mínimo', 'Insalubridade S/Salário Normativo'],
}
```

**Novos Cards**:
- Periculosidade
- Insalubridade

---

## 📈 IMPACTO ESTIMADO

### Indicadores que melhoram:
1. **Custo Total com Horas Extras**: +40% mais preciso (incluir HE 100%, 60%, noturnas)
2. **Análise de Turnos**: Novo indicador (horas noturnas vs diurnas)
3. **Benefícios Totais**: +60% mais completo (VT, gratificações)
4. **Adicionais Legais**: Novo indicador (periculosidade + insalubridade)

### Novos Cards (Total: +8 cards)
- HE 100% (R$)
- HE 60% (R$)
- Adicional Noturno (R$)
- Horas Noturnas
- Vale Transporte
- Gratificações
- Periculosidade
- Insalubridade

---

## ✅ RECOMENDAÇÃO

**Implementar em 2 etapas**:

### Etapa 1 (PRIORITÁRIA):
1. Horas Extras 100% e 60%
2. Horas Extras Noturnas (adicionar às 50%)
3. Adicional Noturno

**Motivo**: São custos significativos que afetam diretamente a folha

### Etapa 2 (CURTO PRAZO):
1. Vale Transporte
2. Gratificações
3. Periculosidade
4. Insalubridade

**Motivo**: Completam a visão de custos e benefícios

---

## 📝 NOTAS TÉCNICAS

### Colunas NÃO encontradas no consolidado:
Estas estavam configuradas mas não existem nos CSVs:
- (Nenhuma - todas as 30 configuradas foram encontradas!)

### Encoding:
- Todos os arquivos CSV estão em `latin-1`
- Caracteres especiais (ç, ã, etc.) funcionam corretamente

### Performance:
- Arquivo consolidado tem **277 colunas** e milhares de linhas
- Leitura completa com pandas leva ~30s
- Recomendado: ler apenas headers quando possível
