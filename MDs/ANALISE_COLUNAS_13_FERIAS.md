# Análise de Colunas: 13º Salário e Férias

## 📊 Resumo da Análise

Análise realizada em **30/01/2026** dos CSVs de folha de pagamento para identificar campos relacionados a 13º salário e férias.

**Arquivos analisados:**
- `AdiantamentoDecimoTerceiro-11-2024.CSV` (22 colunas)
- `IntegralDecimoTerceiro-12-2024.CSV` (31 colunas)
- `11-2024.CSV` - Folha mensal (81 colunas)

---

## 🎄 13º SALÁRIO

### **Arquivos Identificados:**
- **AdiantamentoDecimoTerceiro-MM-AAAA.CSV** - 22 colunas
- **IntegralDecimoTerceiro-MM-AAAA.CSV** - 31 colunas

### **Adiantamento de 13º** (Novembro - 22 colunas)

| Campo CSV | Descrição | Status Atual |
|-----------|-----------|--------------|
| `13o Salário Adiantamento` | 💰 **VALOR BASE** - Adiantamento do 13º (50% do salário) | ❌ **NÃO CAPTURADO** |
| `FGTS S/13o Salário` | FGTS sobre o adiantamento (8%) | ⚠️ Capturado consolidado com outros FGTS |
| `Gratificacao Função 13o Sal.Adiantamento` | Gratificação de função proporcional ao adiantamento | ❌ **NÃO CAPTURADO** |
| `Total de Proventos` | Soma total de proventos do adiantamento | ❌ **NÃO CAPTURADO** |
| `Total de Vantagens` | Vantagens adicionais | ❌ **NÃO CAPTURADO** |
| `Líquido de Cálculo` | Valor líquido após descontos | ❌ **NÃO CAPTURADO** |

**🔍 Exemplo real do arquivo:**
```
Funcionário: JULIANA DA SILVA
13o Salário Adiantamento: 2.612,50
FGTS S/13o Salário: 209,00
Total de Proventos: 2.612,50
Líquido de Cálculo: 2.613,00
```

### **13º Integral** (Dezembro - 31 colunas)

| Campo CSV | Descrição | Status Atual |
|-----------|-----------|--------------|
| `13o Salário Integral` | 💰 **VALOR BASE** - 13º integral (segunda parcela) | ❌ **NÃO CAPTURADO** |
| `13o Salário Maternidade (GPS)` | 💰 13º pago pelo INSS em licença maternidade | ❌ **NÃO CAPTURADO** |
| `Desconto 13o Salário Adiantamento` | 💸 Desconto do adiantamento já recebido | ❌ **NÃO CAPTURADO** |
| `Med.Eve.Var.13o Sal.Integral` | 💰 Média de eventos variáveis (comissões, prêmios) no 13º | ❌ **NÃO CAPTURADO** |
| `Med.Hrs.Ext.13o Sal.Integral Diurno` | 💰 Média de horas extras diurnas no 13º | ❌ **NÃO CAPTURADO** |
| `Gratificacao Função 13o Sal.Integral` | Gratificação de função sobre 13º integral | ⚠️ Capturado como `GRATIFICACAO_FUNCAO_13_SAL_PROP` |
| `INSS S/13o Salário` | 💸 INSS sobre 13º integral | ⚠️ Capturado consolidado com outros INSS |
| `IRRF S/13o Salário` | 💸 IRRF sobre 13º integral | ⚠️ Capturado consolidado com outros IRRF |
| `FGTS S/13o Salário` | 💸 FGTS sobre 13º integral (8%) | ⚠️ Capturado consolidado com outros FGTS |
| `Total de Proventos` | Soma total de proventos (antes descontos) | ❌ **NÃO CAPTURADO** |
| `Total de Descontos` | Soma total de descontos | ❌ **NÃO CAPTURADO** |
| `Líquido de Cálculo` | Valor líquido a receber | ❌ **NÃO CAPTURADO** |
| `Base INSS 13o Salário - Empresa` | Base de cálculo INSS patronal | ❌ **NÃO CAPTURADO** |
| `Base IRRF 13o Salário - Outra Empresa` | Base IRRF para cálculo com outras empresas | ❌ **NÃO CAPTURADO** |
| `Dedução IRRF Dependentes - IRRF s/13o. Salário` | Dedução por dependentes no IR | ❌ **NÃO CAPTURADO** |
| `Dedução Simplificada - IRRF s/13o. Salário` | Dedução simplificada do IR | ❌ **NÃO CAPTURADO** |

**🔍 Exemplo real do arquivo (Funcionária JULIANA com maternidade):**
```
Funcionário: JULIANA DA SILVA
13o Salário Integral: 3.483,33
13o Salário Maternidade (GPS): 1.741,67  ← Pago pelo governo!
Desconto 13o Salário Adiantamento: 2.612,50
Med.Eve.Var.13o Sal.Integral: 1,97
Med.Hrs.Ext.13o Sal.Integral Diurno: 16,43
INSS S/13o Salário: 550,31
IRRF S/13o Salário: 346,38
FGTS S/13o Salário: 209,00
Total de Proventos: 5.225,00
Total de Descontos: 3.509,19
Líquido de Cálculo: 1.715,81
```

**💡 Observação Crítica:**
O valor da maternidade (GPS) é pago pelo governo, não pela empresa. Precisa ser identificado separadamente para cálculos corretos de custo com folha.

---

## 🏖️ FÉRIAS

### **Colunas Identificadas nas Folhas Mensais**

| Campo CSV | Descrição | Status Atual |
|-----------|-----------|--------------|
| `Horas Férias Diurnas` | Valor base das férias (horas diurnas) | ❌ **NÃO CAPTURADO** |
| `1/3 Sobre Férias` | Abono constitucional de férias (1/3) | ❌ **NÃO CAPTURADO** |
| `Desconto Adiantamento Férias` | Desconto de adiantamento de férias | ❌ **NÃO CAPTURADO** |
| `INSS S/Férias` | INSS sobre férias | ✅ Capturado (consolidado) |
| `IRRF S/Férias` | IRRF sobre férias | ✅ Capturado (consolidado) |
| `FGTS S/Férias` | FGTS sobre férias | ✅ Capturado (consolidado) |
| `Gratificacao Função Férias` | Gratificação de função sobre férias | ✅ Capturado como `GRATIFICACAO_FUNCAO_FERIAS` |
| `Gratificacao Função Férias Proporc.` | Gratificação proporcional | ✅ Capturado como `GRATIFICACAO_FUNCAO_FERIAS_PROP` |
| `Med.Hrs.Ext.S/Férias Diurnas` | Média horas extras em férias | ❌ **NÃO CAPTURADO** |
| `Base INSS Férias - Empresa` | Base de cálculo INSS férias | ❌ **NÃO CAPTURADO** |
| `Dedução IRRF Dependentes - IRRF s/Férias` | Dedução por dependentes | ❌ **NÃO CAPTURADO** |
| `Dedução Simplificada - IRRF s/Férias` | Dedução simplificada IRRF | ❌ **NÃO CAPTURADO** |
| `Compl. Desconto Adiantamento S/Férias IRRF/Pensão` | Complemento de descontos | ❌ **NÃO CAPTURADO** |

---

## 🔍 Observações Importantes

### **Estrutura Atual do Sistema:**

O sistema atualmente **não diferencia** entre:
- Folha mensal regular
- Folha de 13º salário (adiantamento ou integral)
- Folha de férias

**Todos são tratados como períodos genéricos**, o que causa problemas:

1. **13º Salário:**
   - ❌ Valor principal do 13º não é capturado
   - ✅ Apenas gratificações e encargos são consolidados
   - ⚠️ Não há distinção entre adiantamento e integral

2. **Férias:**
   - ❌ Valor principal das férias não é capturado
   - ❌ Abono de 1/3 não é capturado
   - ✅ Apenas gratificações e encargos são consolidados

### **Problema de Duplicação:**

Quando os CSVs de 13º forem processados, haverá **duplicação de encargos**:
- FGTS, INSS e IRRF já são capturados na folha mensal
- Se processar os CSVs de 13º, somará novamente os mesmos encargos
- **Total consolidado ficará incorreto** (dobrado)

---

## 💡 Solução Proposta

### **1. Adicionar Detecção de Tipo de Período**

Já existe no código (`payroll_csv_processor.py`):

```python
'13_adiantamento': r'AdiantamentoDecimoTerceiro.*?(\d{2})-(\d{4})',
'13_integral': r'IntegralDecimoTerceiro.*?(\d{2})-(\d{4})',
```

### **2. Criar Campos Específicos para 13º e Férias**

**Adicionar no `earnings_data` JSON:**

```python
# 13º Salário - ADIANTAMENTO (Novembro)
'13_SALARIO_ADIANTAMENTO': '13o Salário Adiantamento',                    # VALOR BASE DO ADIANTAMENTO
'13_GRATIFICACAO_FUNCAO_ADIANTAMENTO': 'Gratificacao Função 13o Sal.Adiantamento',

# 13º Salário - INTEGRAL (Dezembro)
'13_SALARIO_INTEGRAL': '13o Salário Integral',                           # VALOR BASE DA 2ª PARCELA
'13_SALARIO_MATERNIDADE_GPS': '13o Salário Maternidade (GPS)',          # PAGO PELO GOVERNO (separar!)
'13_MEDIA_EVENTOS_VARIAVEIS': 'Med.Eve.Var.13o Sal.Integral',           # Comissões, prêmios, etc
'13_MEDIA_HORAS_EXTRAS_DIURNO': 'Med.Hrs.Ext.13o Sal.Integral Diurno',  # Média de HE no 13º
'13_GRATIFICACAO_FUNCAO_INTEGRAL': 'Gratificacao Função 13o Sal.Integral',

# Férias
'FERIAS_VALOR_BASE': 'Horas Férias Diurnas',                             # VALOR BASE DAS FÉRIAS
'FERIAS_ABONO_1_3': '1/3 Sobre Férias',                                  # ABONO CONSTITUCIONAL
'FERIAS_MEDIA_HORAS_EXTRAS': 'Med.Hrs.Ext.S/Férias Diurnas',            # Média de HE nas férias
```

**Adicionar no `deductions_data` JSON:**

```python
# Descontos de 13º e Férias
'DESCONTO_13_ADIANTAMENTO': 'Desconto 13o Salário Adiantamento',        # Desconto da 1ª parcela
'DESCONTO_FERIAS_ADIANTAMENTO': 'Desconto Adiantamento Férias',         # Desconto de adiantamento de férias
```

**⚠️ IMPORTANTE - Campos já existentes (não duplicar):**
```python
# Estes JÁ EXISTEM no sistema atual:
'GRATIFICACAO_FUNCAO_13_SAL_PROP': 'Gratificacao Função 13o Sal.Integral'  # ✅ JÁ CAPTURADO
'GRATIFICACAO_FUNCAO_FERIAS': 'Gratificacao Função Férias'                 # ✅ JÁ CAPTURADO
'GRATIFICACAO_FUNCAO_FERIAS_PROP': 'Gratificacao Função Férias Proporc.'  # ✅ JÁ CAPTURADO
'FGTS_13_SALARIO': 'FGTS S/13o Salário'                                    # ✅ JÁ CAPTURADO (consolidado)
'INSS_13_SALARIO': 'INSS S/13o Salário'                                    # ✅ JÁ CAPTURADO (consolidado)
'IRRF_13_SALARIO': 'IRRF S/13o Salário'                                    # ✅ JÁ CAPTURADO (consolidado)
```

### **3. Atualizar Queries do Backend**

Criar totalizadores separados em [main_legacy.py](../backend/main_legacy.py):

```sql
-- 13º Salário - VALORES BASE
COALESCE(SUM((earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric), 0) as total_13_adiantamento,
COALESCE(SUM((earnings_data->>'13_SALARIO_INTEGRAL')::numeric), 0) as total_13_integral,
COALESCE(SUM((earnings_data->>'13_SALARIO_MATERNIDADE_GPS')::numeric), 0) as total_13_maternidade_gps,

-- 13º Salário - COMPONENTES ADICIONAIS
COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_VARIAVEIS')::numeric), 0) as total_13_med_eventos,
COALESCE(SUM((earnings_data->>'13_MEDIA_HORAS_EXTRAS_DIURNO')::numeric), 0) as total_13_med_horas_extras,
COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_FUNCAO_ADIANTAMENTO')::numeric), 0) as total_13_gratif_adiantamento,
COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_FUNCAO_INTEGRAL')::numeric), 0) as total_13_gratif_integral,

-- Férias - VALORES BASE
COALESCE(SUM((earnings_data->>'FERIAS_VALOR_BASE')::numeric), 0) as total_ferias_base,
COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) as total_ferias_abono_1_3,
COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HORAS_EXTRAS')::numeric), 0) as total_ferias_med_horas_extras,

-- Descontos
COALESCE(SUM((deductions_data->>'DESCONTO_13_ADIANTAMENTO')::numeric), 0) as total_desconto_13_adiantamento,
COALESCE(SUM((deductions_data->>'DESCONTO_FERIAS_ADIANTAMENTO')::numeric), 0) as total_desconto_ferias_adiantamento,
```

**💡 Cálculo Total de 13º:**
```python
# No backend, retornar:
total_13_salario_completo = (
    total_13_adiantamento +           # Adiantamento (novembro)
    total_13_integral +                # Integral (dezembro)
    total_13_maternidade_gps +         # Pago pelo governo
    total_13_med_eventos +             # Comissões/bônus
    total_13_med_horas_extras +        # Horas extras
    total_13_gratif_adiantamento +     # Gratificação do adiantamento
    total_13_gratif_integral           # Gratificação do integral
)

# ATENÇÃO: Já existe no sistema atual:
total_13_salario_antigo = (
    total_13_salario_proporcional +    # ✅ Já capturado (só gratificações)
    total_abono_natalino               # ✅ Já capturado
)
# Esse cálculo ANTIGO é INCOMPLETO - falta o valor base!
```

**💡 Cálculo Total de Férias:**
```python
# No backend, retornar:
total_ferias_completo = (
    total_ferias_base +                # Valor base das férias
    total_ferias_abono_1_3 +          # 1/3 constitucional
    total_ferias_med_horas_extras +    # Horas extras em férias
    total_ferias_proporcionais +       # ✅ Já existe (gratificações)
    total_ferias_pagas                 # ✅ Já existe (gratificações)
)

# ATENÇÃO: Já existe no sistema atual:
total_ferias_antigo = (
    total_ferias_pagas +               # ✅ Já capturado (só gratificações)
    total_ferias_proporcionais         # ✅ Já capturado (só gratificações)
)
# Esse cálculo ANTIGO é INCOMPLETO - falta o valor base + abono!
```

### **4. Atualizar Frontend**

Atualizar cards de 13º e Férias em [Payroll.jsx](../frontend/src/pages/indicators/Payroll.jsx) para mostrar valores reais:

```jsx
// ============================================
// 🎄 CARD 13º SALÁRIO - DETALHADO
// ============================================
<div className="card">
  <div className="card-header">
    <h3>🎄 13º Salário</h3>
    <span className="badge">
      {displayStats.total_13_salario_completo ? 
        `R$ ${formatCurrency(displayStats.total_13_salario_completo)}` : 
        'Sem dados'
      }
    </span>
  </div>
  
  <div className="card-body">
    {/* BREAKDOWN DETALHADO */}
    <div className="breakdown">
      <p className="breakdown-label">💰 Valores Base:</p>
      <ul className="breakdown-list">
        <li>
          Adiantamento (Nov): 
          <strong>R$ {formatCurrency(displayStats.total_13_adiantamento || 0)}</strong>
        </li>
        <li>
          Integral (Dez): 
          <strong>R$ {formatCurrency(displayStats.total_13_integral || 0)}</strong>
        </li>
        <li>
          Maternidade (GPS): 
          <strong>R$ {formatCurrency(displayStats.total_13_maternidade_gps || 0)}</strong>
          <span className="badge-info">Pago pelo governo</span>
        </li>
      </ul>

      <p className="breakdown-label">✨ Componentes Adicionais:</p>
      <ul className="breakdown-list">
        <li>
          Média Eventos Variáveis: 
          <strong>R$ {formatCurrency(displayStats.total_13_med_eventos || 0)}</strong>
        </li>
        <li>
          Média Horas Extras: 
          <strong>R$ {formatCurrency(displayStats.total_13_med_horas_extras || 0)}</strong>
        </li>
        <li>
          Gratificações: 
          <strong>R$ {formatCurrency(
            (displayStats.total_13_gratif_adiantamento || 0) + 
            (displayStats.total_13_gratif_integral || 0)
          )}</strong>
        </li>
      </ul>

      {/* TOTAL CALCULADO */}
      <div className="breakdown-total">
        <p>Total 13º Salário:</p>
        <strong className="total-value">
          R$ {formatCurrency(
            (displayStats.total_13_adiantamento || 0) +
            (displayStats.total_13_integral || 0) +
            (displayStats.total_13_maternidade_gps || 0) +
            (displayStats.total_13_med_eventos || 0) +
            (displayStats.total_13_med_horas_extras || 0) +
            (displayStats.total_13_gratif_adiantamento || 0) +
            (displayStats.total_13_gratif_integral || 0)
          )}
        </strong>
      </div>
    </div>

    {/* ALERTA SE TIVER MATERNIDADE */}
    {displayStats.total_13_maternidade_gps > 0 && (
      <div className="alert alert-info">
        ℹ️ <strong>R$ {formatCurrency(displayStats.total_13_maternidade_gps)}</strong> foram 
        pagos pelo INSS (licença maternidade) e não impactam o custo da folha da empresa.
      </div>
    )}
  </div>
</div>

// ============================================
// 🏖️ CARD FÉRIAS - DETALHADO
// ============================================
<div className="card">
  <div className="card-header">
    <h3>🏖️ Férias</h3>
    <span className="badge">
      {displayStats.total_ferias_completo ? 
        `R$ ${formatCurrency(displayStats.total_ferias_completo)}` : 
        'Sem dados'
      }
    </span>
  </div>
  
  <div className="card-body">
    {/* BREAKDOWN DETALHADO */}
    <div className="breakdown">
      <p className="breakdown-label">💰 Valores Base:</p>
      <ul className="breakdown-list">
        <li>
          Valor Base (Horas Férias): 
          <strong>R$ {formatCurrency(displayStats.total_ferias_base || 0)}</strong>
        </li>
        <li>
          Abono Constitucional (1/3): 
          <strong>R$ {formatCurrency(displayStats.total_ferias_abono_1_3 || 0)}</strong>
          <span className="badge-info">Obrigatório por lei</span>
        </li>
      </ul>

      <p className="breakdown-label">✨ Componentes Adicionais:</p>
      <ul className="breakdown-list">
        <li>
          Média Horas Extras: 
          <strong>R$ {formatCurrency(displayStats.total_ferias_med_horas_extras || 0)}</strong>
        </li>
        <li>
          Gratificações: 
          <strong>R$ {formatCurrency(
            (displayStats.total_ferias_pagas || 0) + 
            (displayStats.total_ferias_proporcionais || 0)
          )}</strong>
        </li>
      </ul>

      {/* DESCONTOS */}
      {displayStats.total_desconto_ferias_adiantamento > 0 && (
        <>
          <p className="breakdown-label">💸 Descontos:</p>
          <ul className="breakdown-list">
            <li>
              Adiantamento de Férias: 
              <strong className="text-danger">
                -R$ {formatCurrency(displayStats.total_desconto_ferias_adiantamento || 0)}
              </strong>
            </li>
          </ul>
        </>
      )}

      {/* TOTAL CALCULADO */}
      <div className="breakdown-total">
        <p>Total Férias:</p>
        <strong className="total-value">
          R$ {formatCurrency(
            (displayStats.total_ferias_base || 0) +
            (displayStats.total_ferias_abono_1_3 || 0) +
            (displayStats.total_ferias_med_horas_extras || 0) +
            (displayStats.total_ferias_pagas || 0) +
            (displayStats.total_ferias_proporcionais || 0)
          )}
        </strong>
      </div>
    </div>

    {/* INFO SOBRE ABONO CONSTITUCIONAL */}
    <div className="alert alert-info">
      ℹ️ O abono de 1/3 sobre férias é <strong>garantia constitucional</strong> 
      (Art. 7º, XVII da CF/88) e representa {
        displayStats.total_ferias_base > 0 
          ? ((displayStats.total_ferias_abono_1_3 / displayStats.total_ferias_base * 100).toFixed(1))
          : '33.33'
      }% do valor das férias.
    </div>
  </div>
</div>
```

**🎨 CSS Adicional necessário:**
```css
.breakdown {
  margin-top: 1rem;
}

.breakdown-label {
  font-weight: 600;
  margin-top: 0.75rem;
  margin-bottom: 0.5rem;
  color: #374151;
}

.breakdown-list {
  list-style: none;
  padding-left: 0;
  margin-bottom: 1rem;
}

.breakdown-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.breakdown-list li strong {
  color: #059669;
  font-weight: 600;
}

.breakdown-list li .text-danger {
  color: #dc2626;
}

.breakdown-total {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 2px solid #d1d5db;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.total-value {
  font-size: 1.25rem;
  color: #059669;
  font-weight: 700;
}

.badge-info {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background-color: #dbeafe;
  color: #1e40af;
  border-radius: 0.25rem;
  margin-left: 0.5rem;
}

.alert {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.alert-info {
  background-color: #dbeafe;
  border: 1px solid #93c5fd;
  color: #1e40af;
}
```

---

## 📝 Próximos Passos

1. ✅ **Análise completa** - Identificadas todas as colunas
2. ⏳ **Implementar mapeamento** - Adicionar campos no processador CSV
3. ⏳ **Atualizar backend** - Criar queries para novos totalizadores
4. ⏳ **Atualizar frontend** - Exibir valores nos cards
5. ⏳ **Testar upload** - Processar CSVs de 13º e férias
6. ⏳ **Validar consolidação** - Garantir que não há duplicação

---

## 🎯 Benefícios da Implementação

- ✅ **Valores reais** de 13º e férias nos relatórios
- ✅ **Separação clara** entre adiantamento e integral
- ✅ **Rastreamento** de férias pagas por período
- ✅ **Cálculos corretos** sem duplicação de encargos
- ✅ **Análise histórica** de 13º e férias por ano
