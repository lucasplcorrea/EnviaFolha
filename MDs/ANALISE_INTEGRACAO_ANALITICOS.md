# Análise de Integração: Scripts Analiticos vs Sistema Atual

**Data:** 16/01/2026  
**Objetivo:** Mapear integração dos scripts de análise CSV com o sistema web atual

---

## 1. COMPARAÇÃO: Indicadores Existentes vs Analiticos

### ✅ Indicadores JÁ IMPLEMENTADOS no Sistema

#### **1.1 Headcount (Efetivo)**
- **Sistema Atual:** 
  - Endpoint: `GET /api/v1/indicators/headcount`
  - Service: `HRIndicatorsService.get_headcount_metrics()`
  - Fonte de dados: Tabela `employees` (apenas ativos)
  - Métricas: Total, por departamento, setor, empresa, tipo contrato
  - Cache: 1 hora (TTL)

- **Scripts Analiticos:**
  - Arquivo: `calcular_indicadores_consolidados.py` (Indicador 1)
  - Fonte: Tabela consolidada `dados_unificados`
  - Métricas: Evolução temporal, crescimento %, ticket médio
  - Diferencial: **Histórico mensal + tendências**

**CONFLITO:** ❌ NÃO  
**INTEGRAÇÃO:** ✅ COMPLEMENTAR - Sistema atual mostra snapshot, Analiticos adiciona série histórica

---

#### **1.2 Turnover (Rotatividade)**
- **Sistema Atual:**
  - Endpoint: `GET /api/v1/indicators/turnover`
  - Fonte: Tabelas `employees` + `movement_records`
  - Métricas: Admissões, desligamentos, taxa de rotatividade
  - Período: Parametrizável via query params

- **Scripts Analiticos:**
  - Indicador 2 em `calcular_indicadores_consolidados.py`
  - Usa colunas: `data_admissao`, `data_demissao`
  - Calcula: Taxa mensal, comparativo entre períodos

**CONFLITO:** ❌ NÃO  
**INTEGRAÇÃO:** ✅ COMPATÍVEL - Mesma lógica, fontes de dados alinhadas

---

#### **1.3 Demographics (Perfil Demográfico)**
- **Sistema Atual:**
  - Endpoint: `GET /api/v1/indicators/demographics`
  - Campos: `sex`, `marital_status`, `birth_date` (calcula idade)
  - Distribuição por gênero, estado civil, faixa etária

- **Scripts Analiticos:**
  - Não há indicador específico de demografia
  - CSVs contêm: `sexo`, `estado_civil`, `dt_nascimento`

**CONFLITO:** ❌ NÃO  
**INTEGRAÇÃO:** ✅ Sistema atual já cobre, pode enriquecer com dados históricos

---

#### **1.4 Tenure (Tempo de Casa)**
- **Sistema Atual:**
  - Endpoint: `GET /api/v1/indicators/tenure`
  - Calcula: Tempo médio, distribuição por faixas (0-1, 1-3, 3-5, 5-10, 10+)
  - Usa: `admission_date` dos employees ativos

- **Scripts Analiticos:**
  - Indicador 10: Distribuição tempo de casa
  - Identifica: Risco de retenção (< 6 meses)

**CONFLITO:** ❌ NÃO  
**INTEGRAÇÃO:** ✅ Sistema atual básico, Analiticos adiciona análise de risco

---

#### **1.5 Leaves (Afastamentos)**
- **Sistema Atual:**
  - Endpoint: `GET /api/v1/indicators/leaves`
  - Tabela: `leave_records`
  - Métricas: Total afastados, por tipo, duração média

- **Scripts Analiticos:**
  - Não há análise específica de afastamentos
  - CSVs podem conter eventos pontuais

**CONFLITO:** ❌ NÃO  
**INTEGRAÇÃO:** ✅ Sistema atual suficiente

---

### ⚠️ Indicadores AUSENTES no Sistema (Presentes em Analiticos)

#### **2.1 Análise Salarial Detalhada** 📊
- **Analiticos Indicador 3:**
  - Salário médio, mediano, mínimo, máximo
  - Desvio padrão, coeficiente de variação
  - Crescimento % mês a mês
  - Distribuição por quartis

- **Sistema Atual:**
  - ❌ NÃO POSSUI análise salarial
  - Tabela `payroll_data` existe mas sem agregações

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR novo endpoint `/api/v1/indicators/salary`

---

#### **2.2 Custo de Folha e Encargos** 💰
- **Analiticos Indicador 4:**
  - Total de proventos, descontos
  - Taxas: INSS, IRRF, FGTS
  - Custo total da folha
  - % de encargos sobre bruto

- **Sistema Atual:**
  - ❌ NÃO CALCULADO
  - Dados existem em `payroll_data.earnings_data` e `deductions_data` (JSON)

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR `/api/v1/indicators/payroll-cost`

---

#### **2.3 Horas Extras** ⏰
- **Analiticos Indicador 5:**
  - Custo HE 50%, HE 100%, adicional noturno
  - % de HE sobre folha total
  - Colaboradores com HE recorrente

- **Sistema Atual:**
  - ❌ NÃO ANALISADO
  - Campo `hours_extra` existe em `payroll_records` (modelo antigo)

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR `/api/v1/indicators/overtime`

---

#### **2.4 Benefícios** 🏥
- **Analiticos Indicador 6:**
  - Plano de saúde (valor + % adoção)
  - Vale transporte (valor + % adoção)
  - Total de benefícios
  - Custo per capita

- **Sistema Atual:**
  - Tabela `benefit_records` existe
  - ❌ NÃO HÁ agregação/análise

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR `/api/v1/indicators/benefits`

---

#### **2.5 13º Salário e Férias** 🎁
- **Analiticos Indicador 7:**
  - Total 13º adiantamento vs integral
  - Total férias pagas
  - Provisão estimada

- **Sistema Atual:**
  - ❌ NÃO POSSUI
  - Precisa parsing de arquivos específicos (AdiantamentoDecimoTerceiro, IntegralDecimoTerceiro)

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR `/api/v1/indicators/thirteenth-salary`

---

#### **2.6 Comparativo entre Divisões** 🏢
- **Analiticos Indicador 8:**
  - Empreendimentos (0060) vs Infraestrutura (0059)
  - Participação % de cada divisão
  - Custos comparativos

- **Sistema Atual:**
  - Campo `company_code` existe
  - ❌ SEM análise comparativa

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR `/api/v1/indicators/division-comparison`

---

#### **2.7 Insalubridade e Periculosidade** ⚠️
- **Analiticos Indicador 9:**
  - Total de adicional de insalubridade
  - Total de adicional de periculosidade
  - % de colaboradores com adicionais

- **Sistema Atual:**
  - ❌ NÃO RASTREADO
  - Precisa extração de campos JSON em `payroll_data.additional_data`

**AÇÃO NECESSÁRIA:** 🔧 IMPLEMENTAR `/api/v1/indicators/health-safety`

---

## 2. ESTRUTURA DO BANCO DE DADOS

### 2.1 Tabelas Existentes Relevantes

```
✅ employees (55 colunas)
   - Campos básicos: id, unique_id, name, cpf, phone, email
   - Campos RH: department, position, sector, admission_date, birth_date
   - Status: is_active, employment_status, termination_date
   - Relacionamentos: payrolls, benefits, movements, leaves

✅ payroll_data (modelo novo - JSONB)
   - employee_id, period_id
   - gross_salary, net_salary
   - earnings_data (JSON) → proventos dinâmicos
   - deductions_data (JSON) → descontos (INSS, IR, etc)
   - benefits_data (JSON) → benefícios
   - additional_data (JSON) → campos extras

⚠️ payroll_records (modelo antigo - campos fixos)
   - employee_id, competence
   - salary_base, additions, deductions
   - hours_extra, hours_absence, net_salary
   - STATUS: Legacy, sendo substituído por payroll_data

✅ payroll_periods
   - year, month, period_name
   - is_active, is_closed
   - Relaciona com payroll_data

✅ benefit_records
   - employee_id, benefit_type, value
   - STATUS: Existe mas pouco usado

✅ movement_records
   - employee_id, movement_type, movement_date
   - old_value, new_value
   - Para turnover

✅ leave_records
   - employee_id, leave_type, start_date, end_date, days
   - STATUS: Recém implementado (working)

✅ hr_indicator_snapshots (cache)
   - indicator_type, calculation_date
   - metrics (JSON)
   - period_start, period_end
   - STATUS: Sistema de cache funcionando
```

### 2.2 Lacunas no Banco vs CSVs Analiticos

| Dado CSV | Tabela Atual | Status | Solução |
|----------|--------------|--------|---------|
| `total_proventos` | `payroll_data.earnings_data` | ✅ Existe (JSON) | Extrair e somar |
| `total_descontos` | `payroll_data.deductions_data` | ✅ Existe (JSON) | Extrair e somar |
| `custo_he_50` | `payroll_data.earnings_data['HE50%']` | ⚠️ Depende do CSV | Mapear chave JSON |
| `custo_he_100` | `payroll_data.earnings_data['HE100%']` | ⚠️ Depende do CSV | Mapear chave JSON |
| `plano_saude` | `benefit_records` OU `payroll_data.benefits_data` | ⚠️ Duplicado | Definir fonte única |
| `vale_transporte` | `benefit_records` OU `payroll_data.benefits_data` | ⚠️ Duplicado | Definir fonte única |
| `adicional_insalubridade` | `payroll_data.additional_data` | ⚠️ Sem campo específico | Adicionar coluna |
| `adicional_periculosidade` | `payroll_data.additional_data` | ⚠️ Sem campo específico | Adicionar coluna |
| `13_salario_adiantamento` | ❌ Não rastreado | ❌ Falta | Nova tabela ou JSON |
| `13_salario_integral` | ❌ Não rastreado | ❌ Falta | Nova tabela ou JSON |

---

## 3. ONDE ENCAIXAR AS NOVAS ESTATÍSTICAS

### 3.1 Frontend - Página RHIndicators.jsx

**Estrutura Atual:**
```javascript
// Categorias existentes:
- overview (visão geral)
- headcount (efetivo)
- turnover (rotatividade)
- demographics (perfil)
- tenure (tempo de casa)
- leaves (afastamentos)
```

**Proposta de Expansão:**
```javascript
// ADICIONAR 7 novas categorias:
- salary (análise salarial) ← Analiticos Indicador 3
- payroll-cost (custo folha) ← Analiticos Indicador 4
- overtime (horas extras) ← Analiticos Indicador 5
- benefits (benefícios) ← Analiticos Indicador 6
- thirteenth-salary (13º) ← Analiticos Indicador 7
- division-comparison (divisões) ← Analiticos Indicador 8
- health-safety (insalubridade) ← Analiticos Indicador 9
```

**Visual Sugerido:**
```jsx
// Menu lateral com ícones:
<button onClick={() => setActiveCategory('salary')}>
  <CurrencyDollarIcon /> Análise Salarial
</button>

<button onClick={() => setActiveCategory('overtime')}>
  <ClockIcon /> Horas Extras
</button>

<button onClick={() => setActiveCategory('benefits')}>
  <GiftIcon /> Benefícios
</button>
```

---

### 3.2 Backend - Novos Endpoints

**Padrão Existente:**
```python
# main_legacy.py (linhas 1415-1427)
elif path == '/api/v1/indicators/headcount':
    self.handle_indicators_headcount()
```

**Endpoints a Adicionar:**
```python
# ===== INDICADORES FINANCEIROS =====
elif path == '/api/v1/indicators/salary':
    self.handle_indicators_salary()  # Novo

elif path == '/api/v1/indicators/payroll-cost':
    self.handle_indicators_payroll_cost()  # Novo

elif path == '/api/v1/indicators/overtime':
    self.handle_indicators_overtime()  # Novo

elif path == '/api/v1/indicators/benefits':
    self.handle_indicators_benefits()  # Novo

elif path == '/api/v1/indicators/thirteenth-salary':
    self.handle_indicators_thirteenth()  # Novo

# ===== INDICADORES COMPARATIVOS =====
elif path == '/api/v1/indicators/division-comparison':
    self.handle_indicators_divisions()  # Novo

# ===== INDICADORES DE SAÚDE/SEGURANÇA =====
elif path == '/api/v1/indicators/health-safety':
    self.handle_indicators_health_safety()  # Novo
```

---

### 3.3 Service Layer - Extensão de HRIndicatorsService

**Arquivo:** `backend/app/services/hr_indicators.py`

**Novos Métodos:**
```python
class HRIndicatorsService:
    
    # EXISTENTES (já implementados):
    def get_headcount_metrics(self, use_cache=True)
    def get_turnover_metrics(self, period_start=None, period_end=None, use_cache=True)
    def get_demographic_metrics(self, use_cache=True)
    def get_tenure_metrics(self, use_cache=True)
    def get_leave_metrics(self, use_cache=True)
    
    # NOVOS (a implementar):
    def get_salary_metrics(self, period_id=None, use_cache=True):
        """
        Análise salarial detalhada
        - Médio, mediano, min, max, desvio padrão
        - Distribuição por quartis
        - Crescimento temporal
        """
        
    def get_payroll_cost_metrics(self, period_id=None, use_cache=True):
        """
        Custo total da folha
        - Total proventos, descontos
        - Taxas INSS, IRRF, FGTS
        - % encargos
        """
        
    def get_overtime_metrics(self, period_id=None, use_cache=True):
        """
        Análise de horas extras
        - Custo HE50%, HE100%, adicional noturno
        - % sobre folha
        - Colaboradores com HE recorrente
        """
        
    def get_benefits_metrics(self, period_id=None, use_cache=True):
        """
        Benefícios
        - Plano saúde, vale transporte
        - Taxa de adoção %
        - Custo per capita
        """
        
    def get_thirteenth_salary_metrics(self, year=None, use_cache=True):
        """
        13º Salário
        - Total adiantamento vs integral
        - Provisão vs realizado
        """
        
    def get_division_comparison_metrics(self, period_id=None, use_cache=True):
        """
        Comparativo Divisões
        - Empreendimentos vs Infraestrutura
        - Participação % custos
        """
        
    def get_health_safety_metrics(self, period_id=None, use_cache=True):
        """
        Insalubridade e Periculosidade
        - Total adicional insalubridade
        - Total adicional periculosidade
        - % colaboradores com adicionais
        """
```

---

## 4. MESCLAR CÓDIGOS: Estratégia de Integração

### 4.1 Funções Reutilizáveis dos Scripts Analiticos

#### **converter_valor_para_numero()**
```python
# De: consolidar_empreendimentos.py (linhas 90-105)
# Para: backend/app/utils/parsers.py (novo arquivo)

def parse_br_number(value: str) -> float:
    """
    Converte número formato BR (1.234,56) para float
    Reutilizar em upload de CSVs
    """
    if pd.isna(value) or value == '':
        return 0.0
    value_str = str(value).strip()
    value_str = value_str.replace('.', '').replace(',', '.')
    try:
        return float(value_str)
    except:
        return 0.0
```

#### **converter_data()**
```python
# De: consolidar_empreendimentos.py (linhas 107-115)
# Para: backend/app/utils/parsers.py

def parse_br_date(date_str: str) -> Optional[datetime]:
    """
    Converte data DD/MM/AAAA para datetime
    """
    if pd.isna(date_str) or date_str == '':
        return None
    try:
        return pd.to_datetime(date_str, format='%d/%m/%Y')
    except:
        return None
```

#### **extrair_informacoes_arquivo()**
```python
# De: consolidar_empreendimentos.py (linhas 24-78)
# Para: backend/app/services/payroll_processor.py

def detect_payroll_type(filename: str) -> Dict[str, Any]:
    """
    Detecta tipo de arquivo via regex
    Retorna: { tipo, mes, ano }
    """
    patterns = {
        'mensal': r'(\d{2})-(\d{4})\.CSV',
        '13_adiantamento': r'AdiantamentoDecimoTerceiro.*(\d{2})-(\d{4})',
        '13_integral': r'IntegralDecimoTerceiro.*(\d{2})-(\d{4})',
        'complementar': r'FolhaComplementar.*(\d{2})-(\d{4})',
        'adiantamento': r'Adiantamento.*(\d{2})-(\d{4})'
    }
    # ... lógica de matching
```

---

### 4.2 Arquitetura de Processamento CSV

**Fluxo Atual (Payroll Upload):**
```
1. Frontend: PayrollDataProcessor.jsx
   ↓ POST /api/v1/payroll/upload
2. Backend: handle_payroll_upload() (main_legacy.py)
   ↓ Salva em uploads/
3. ??? (processamento não implementado)
```

**Fluxo Proposto (Inspirado em Analiticos):**
```
1. Upload CSV
   ↓
2. Detectar tipo (detect_payroll_type)
   ↓
3. Parse colunas (parse_br_number, parse_br_date)
   ↓
4. Criar PayrollPeriod (se não existe)
   ↓
5. Inserir em payroll_data (JSONB)
   ↓
6. Invalidar cache de indicadores
   ↓
7. Retornar resumo (sucesso, erros, linhas processadas)
```

**Serviço Novo:**
```python
# backend/app/services/payroll_csv_processor.py

class PayrollCSVProcessor:
    def __init__(self, db: Session):
        self.db = db
    
    def process_csv_file(self, file_path: str, division_code: str) -> Dict:
        """
        Processa CSV de folha e salva no banco
        
        Args:
            file_path: Caminho do arquivo CSV
            division_code: '0060' (Empreendimentos) ou '0059' (Infraestrutura)
        
        Returns:
            {
                'success': True/False,
                'period_id': int,
                'records_processed': int,
                'errors': []
            }
        """
        # 1. Detectar tipo de arquivo
        file_info = detect_payroll_type(os.path.basename(file_path))
        
        # 2. Ler CSV com encoding correto
        df = pd.read_csv(
            file_path,
            delimiter=';',
            encoding='latin-1',
            on_bad_lines='skip'
        )
        
        # 3. Criar/buscar PayrollPeriod
        period = self._get_or_create_period(
            year=file_info['ano'],
            month=file_info['mes'],
            period_type=file_info['tipo']
        )
        
        # 4. Processar cada linha
        for idx, row in df.iterrows():
            self._process_employee_payroll(row, period.id, division_code)
        
        # 5. Invalidar cache
        from app.services.hr_indicators import HRIndicatorsService
        indicators_service = HRIndicatorsService(self.db)
        indicators_service.invalidate_cache()
        
        return {
            'success': True,
            'period_id': period.id,
            'records_processed': len(df)
        }
    
    def _process_employee_payroll(self, row: pd.Series, period_id: int, division_code: str):
        """Processa linha individual do CSV"""
        
        # Buscar employee por matricula
        matricula_completa = f"{division_code}{row.get('CODIGO_FUNC', '').zfill(5)}"
        employee = self.db.query(Employee).filter(
            Employee.unique_id == matricula_completa
        ).first()
        
        if not employee:
            # Log erro ou criar employee temporário
            return
        
        # Construir JSONs dinâmicos
        earnings_data = {}
        deductions_data = {}
        benefits_data = {}
        additional_data = {}
        
        # Mapear colunas CSV → JSON
        for col in row.index:
            value = parse_br_number(row[col])
            
            if col.startswith('PROV_'):  # Proventos
                earnings_data[col] = value
            elif col.startswith('DESC_'):  # Descontos
                deductions_data[col] = value
            elif col in ['VALE_TRANSPORTE', 'PLANO_SAUDE']:
                benefits_data[col] = value
            elif col in ['ADIC_INSALUBRIDADE', 'ADIC_PERICULOSIDADE']:
                additional_data[col] = value
        
        # Criar/atualizar PayrollData
        payroll = PayrollData(
            employee_id=employee.id,
            period_id=period_id,
            gross_salary=parse_br_number(row.get('SALARIO_BASE', 0)),
            net_salary=parse_br_number(row.get('LIQ_A_RECEBER', 0)),
            earnings_data=earnings_data,
            deductions_data=deductions_data,
            benefits_data=benefits_data,
            additional_data=additional_data,
            upload_filename=os.path.basename(file_path)
        )
        
        self.db.add(payroll)
        self.db.commit()
```

---

### 4.3 Mapeamento de Colunas CSV → Banco

**Colunas Essenciais dos CSVs:**
```python
CSV_COLUMN_MAPPING = {
    # Identificação
    'CODIGO_FUNC': 'unique_id',  # + prefixo 0060/0059
    'NOME': 'name',
    'CPF': 'cpf',
    
    # Proventos (vai para earnings_data JSON)
    'SALARIO_BASE': 'earnings_data["SALARIO_BASE"]',
    'HORAS_EXTRAS_50': 'earnings_data["HE_50"]',
    'HORAS_EXTRAS_100': 'earnings_data["HE_100"]',
    'ADICIONAL_NOTURNO': 'earnings_data["ADIC_NOTURNO"]',
    'FERIAS': 'earnings_data["FERIAS"]',
    '13_SALARIO': 'earnings_data["13_SALARIO"]',
    
    # Descontos (vai para deductions_data JSON)
    'INSS': 'deductions_data["INSS"]',
    'IRRF': 'deductions_data["IRRF"]',
    'FGTS': 'deductions_data["FGTS"]',
    'CONTRIBUICAO_SINDICAL': 'deductions_data["SIND"]',
    
    # Benefícios (vai para benefits_data JSON)
    'PLANO_SAUDE': 'benefits_data["PLANO_SAUDE"]',
    'VALE_TRANSPORTE': 'benefits_data["VT"]',
    'VALE_ALIMENTACAO': 'benefits_data["VA"]',
    
    # Adicionais (vai para additional_data JSON)
    'ADIC_INSALUBRIDADE': 'additional_data["INSALUBRIDADE"]',
    'ADIC_PERICULOSIDADE': 'additional_data["PERICULOSIDADE"]',
    
    # Totalizadores
    'TOTAL_PROVENTOS': 'gross_salary',
    'LIQ_A_RECEBER': 'net_salary'
}
```

---

## 5. MELHORIAS NECESSÁRIAS

### 5.1 Banco de Dados

#### **A) Criar Índices para Performance**
```sql
-- Acelerar queries de indicadores
CREATE INDEX idx_payroll_data_period ON payroll_data(period_id);
CREATE INDEX idx_payroll_data_employee_period ON payroll_data(employee_id, period_id);

-- Para queries de benefícios
CREATE INDEX idx_benefit_records_type ON benefit_records(benefit_type);

-- Para análise temporal
CREATE INDEX idx_employees_admission ON employees(admission_date);
CREATE INDEX idx_employees_termination ON employees(termination_date);
```

#### **B) Adicionar Campos Calculados (Performance)**
```sql
-- Em payroll_data, adicionar colunas denormalizadas para queries rápidas
ALTER TABLE payroll_data ADD COLUMN total_earnings DECIMAL(10,2);
ALTER TABLE payroll_data ADD COLUMN total_deductions DECIMAL(10,2);
ALTER TABLE payroll_data ADD COLUMN total_benefits DECIMAL(10,2);
ALTER TABLE payroll_data ADD COLUMN overtime_cost DECIMAL(10,2);

-- Trigger para calcular automaticamente ao inserir
CREATE TRIGGER calculate_payroll_totals
BEFORE INSERT OR UPDATE ON payroll_data
FOR EACH ROW
EXECUTE FUNCTION calculate_totals_from_json();
```

#### **C) Tabela de Mapeamento de Divisões**
```sql
CREATE TABLE divisions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,  -- '0060', '0059'
    name VARCHAR(100),  -- 'Empreendimentos', 'Infraestrutura'
    cnpj VARCHAR(18),
    is_active BOOLEAN DEFAULT TRUE
);

-- Adicionar FK em employees
ALTER TABLE employees ADD COLUMN division_id INTEGER REFERENCES divisions(id);
```

---

### 5.2 Backend - Refatoração

#### **A) Separar Lógica de Negócio**
```
Atual: Tudo em main_legacy.py (5667 linhas)
        ↓
Proposto:
backend/app/
  ├── services/
  │   ├── hr_indicators.py (✅ existe, expandir)
  │   ├── payroll_csv_processor.py (🔧 criar)
  │   ├── payroll_calculator.py (🔧 criar)
  │   └── export_service.py (🔧 criar)
  ├── utils/
  │   ├── parsers.py (🔧 criar - parse_br_number, parse_br_date)
  │   └── validators.py (🔧 criar)
  └── routes/ (modular)
      ├── indicators_router.py (🔧 criar)
      └── payroll_router.py (🔧 criar)
```

#### **B) Criar Service de Cálculo de Folha**
```python
# backend/app/services/payroll_calculator.py

class PayrollCalculator:
    """Lógica de cálculo de folha (reutilizar dos scripts)"""
    
    @staticmethod
    def calculate_payroll_cost(payroll_data: PayrollData) -> Dict:
        """Calcula custo total com encargos"""
        gross = payroll_data.gross_salary or 0
        
        # Taxas médias (configuráveis)
        inss_rate = 0.14  # 14%
        fgts_rate = 0.08  # 8%
        
        return {
            'gross_salary': gross,
            'inss': gross * inss_rate,
            'fgts': gross * fgts_rate,
            'total_cost': gross * (1 + inss_rate + fgts_rate)
        }
    
    @staticmethod
    def calculate_overtime_cost(earnings_data: Dict) -> Dict:
        """Calcula custo de horas extras"""
        he_50 = earnings_data.get('HE_50', 0)
        he_100 = earnings_data.get('HE_100', 0)
        noturno = earnings_data.get('ADIC_NOTURNO', 0)
        
        total_overtime = he_50 + he_100 + noturno
        
        return {
            'he_50_cost': he_50,
            'he_100_cost': he_100,
            'night_shift_cost': noturno,
            'total_overtime': total_overtime
        }
```

---

### 5.3 Frontend - Dashboard Aprimorado

#### **A) Componentes de Visualização**
```jsx
// frontend/src/components/indicators/

SalaryDistributionChart.jsx
  → Gráfico de distribuição salarial (histograma)
  → Usa recharts ou echarts

OvertimeTrendChart.jsx
  → Linha temporal de custo HE
  → Identifica picos (alertas)

BenefitsAdoptionCards.jsx
  → Cards com % de adoção de benefícios
  → Progress bars

DivisionComparisonChart.jsx
  → Gráfico de barras comparativo
  → Empreendimentos vs Infraestrutura

PayrollCostBreakdown.jsx
  → Pie chart de composição de custos
  → Salário base vs encargos vs benefícios
```

#### **B) Filtros Avançados**
```jsx
// Adicionar ao RHIndicators.jsx

<div className="filters-panel">
  {/* Filtro de período */}
  <select value={selectedPeriod} onChange={handlePeriodChange}>
    <option>Último mês</option>
    <option>Últimos 3 meses</option>
    <option>Últimos 6 meses</option>
    <option>Ano atual</option>
    <option>Personalizado</option>
  </select>
  
  {/* Filtro de divisão */}
  <select value={selectedDivision}>
    <option value="all">Todas as Divisões</option>
    <option value="0060">Empreendimentos</option>
    <option value="0059">Infraestrutura</option>
  </select>
  
  {/* Filtro de departamento */}
  <MultiSelect 
    options={departments}
    value={selectedDepartments}
    onChange={setSelectedDepartments}
  />
</div>
```

---

### 5.4 Automação e Agendamento

#### **A) Processamento Assíncrono de CSVs**
```python
# Usar Celery ou RQ para processar CSVs em background

from celery import Celery
app = Celery('payroll_tasks', broker='redis://localhost:6379')

@app.task
def process_payroll_csv_async(file_path: str, division_code: str):
    """
    Task assíncrona para processar CSV grande
    Evita timeout em uploads de 10k+ linhas
    """
    db = SessionLocal()
    try:
        processor = PayrollCSVProcessor(db)
        result = processor.process_csv_file(file_path, division_code)
        
        # Notificar usuário via WebSocket
        send_notification(result)
        
    finally:
        db.close()
```

#### **B) Recálculo Agendado de Indicadores**
```python
# Cron job para recalcular indicadores daily às 2am

@app.task
def recalculate_all_indicators():
    """Recalcula todos os indicadores e atualiza cache"""
    db = SessionLocal()
    try:
        service = HRIndicatorsService(db)
        
        # Invalidar cache antigo
        service.invalidate_cache()
        
        # Recalcular todos (forçar use_cache=False)
        service.get_headcount_metrics(use_cache=False)
        service.get_turnover_metrics(use_cache=False)
        service.get_salary_metrics(use_cache=False)
        # ... todos os demais
        
        print("✅ Indicadores recalculados com sucesso")
    finally:
        db.close()
```

---

### 5.5 Exportação de Relatórios

#### **A) Endpoint de Exportação (Excel/PDF)**
```python
# backend/app/services/export_service.py

class ExportService:
    
    def export_indicators_to_excel(
        self, 
        indicator_types: List[str],
        period_start: date,
        period_end: date
    ) -> BytesIO:
        """
        Exporta múltiplos indicadores para Excel
        Similar aos scripts Analiticos
        """
        writer = pd.ExcelWriter('output.xlsx', engine='openpyxl')
        
        for indicator_type in indicator_types:
            df = self._get_indicator_dataframe(indicator_type, period_start, period_end)
            df.to_excel(writer, sheet_name=indicator_type[:31])  # Max 31 chars
        
        # Aplicar formatação (cores, bordas)
        self._apply_excel_formatting(writer)
        
        writer.save()
        return writer
```

#### **B) Rota de Download**
```python
# main_legacy.py

elif path == '/api/v1/reports/export':
    self.handle_export_indicators()

def handle_export_indicators(self):
    """Gera arquivo Excel com indicadores selecionados"""
    body = self.get_request_body()
    
    export_service = ExportService(self.db)
    excel_file = export_service.export_indicators_to_excel(
        indicator_types=body['indicators'],
        period_start=body['period_start'],
        period_end=body['period_end']
    )
    
    # Enviar arquivo
    self.send_response(200)
    self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    self.send_header('Content-Disposition', f'attachment; filename="indicadores_{datetime.now():%Y%m%d}.xlsx"')
    self.end_headers()
    self.wfile.write(excel_file.getvalue())
```

---

## 6. PLANO DE IMPLEMENTAÇÃO FASEADO

### **FASE 1: Fundação (2 semanas)** 🏗️

**Objetivos:**
- Preparar banco de dados
- Criar serviços básicos de parsing
- Implementar upload de CSV funcional

**Tarefas:**
1. ✅ Criar `backend/app/utils/parsers.py` (parse_br_number, parse_br_date)
2. ✅ Criar `backend/app/services/payroll_csv_processor.py`
3. ✅ Implementar `PayrollCSVProcessor.process_csv_file()`
4. ✅ Criar índices no banco (performance)
5. ✅ Testar upload de 1 CSV mensal (validação end-to-end)

**Entregáveis:**
- CSV de folha sobe e salva em `payroll_data`
- Indicadores básicos (headcount, turnover) funcionam com dados reais

---

### **FASE 2: Indicadores Financeiros (3 semanas)** 💰

**Objetivos:**
- Implementar análise salarial
- Implementar custo de folha
- Implementar horas extras

**Tarefas:**
1. ✅ Adicionar métodos em `HRIndicatorsService`:
   - `get_salary_metrics()`
   - `get_payroll_cost_metrics()`
   - `get_overtime_metrics()`
2. ✅ Criar endpoints em `main_legacy.py`
3. ✅ Criar componentes React:
   - `SalaryDistributionChart.jsx`
   - `PayrollCostBreakdown.jsx`
   - `OvertimeTrendChart.jsx`
4. ✅ Integrar no `RHIndicators.jsx`

**Entregáveis:**
- Dashboard mostra análise salarial completa
- Custo de folha com breakdown detalhado
- Alertas de horas extras excessivas

---

### **FASE 3: Benefícios e 13º Salário (2 semanas)** 🎁

**Objetivos:**
- Análise de benefícios
- Rastreamento de 13º salário

**Tarefas:**
1. ✅ `get_benefits_metrics()` - Implementar
2. ✅ `get_thirteenth_salary_metrics()` - Implementar
3. ✅ Criar lógica de detecção de arquivos 13º (adiantamento vs integral)
4. ✅ Componentes React para exibição

**Entregáveis:**
- Dashboard de benefícios com taxa de adoção
- Tracking de 13º (provisão vs pago)

---

### **FASE 4: Comparativos e Saúde/Segurança (2 semanas)** 📊

**Objetivos:**
- Comparativo entre divisões
- Adicionais de insalubridade/periculosidade

**Tarefas:**
1. ✅ Criar tabela `divisions` no banco
2. ✅ Migrar `company_code` → `division_id`
3. ✅ `get_division_comparison_metrics()`
4. ✅ `get_health_safety_metrics()`
5. ✅ Componentes de visualização comparativa

**Entregáveis:**
- Gráfico comparativo Empreendimentos vs Infraestrutura
- Dashboard de adicionais de saúde/segurança

---

### **FASE 5: Exportação e Automação (2 semanas)** 🤖

**Objetivos:**
- Exportar relatórios Excel/PDF
- Processar CSVs em background
- Recálculo automático de indicadores

**Tarefas:**
1. ✅ Implementar `ExportService`
2. ✅ Endpoint `/api/v1/reports/export`
3. ✅ Configurar Celery/RQ para tasks assíncronas
4. ✅ Cron job para recálculo noturno
5. ✅ Progress bar para uploads grandes

**Entregáveis:**
- Botão "Exportar para Excel" funcional
- Upload de CSV não bloqueia interface
- Indicadores atualizados automaticamente toda noite

---

## 7. RESUMO DE CONFLITOS E COMPATIBILIDADE

### ✅ COMPATÍVEL (Sem Conflitos)

| Indicador | Sistema Atual | Analiticos | Integração |
|-----------|---------------|------------|------------|
| Headcount | ✅ Snapshot atual | ✅ Série histórica | Complementar |
| Turnover | ✅ Básico | ✅ Detalhado | Expandir |
| Demographics | ✅ Completo | ❌ Não possui | Manter atual |
| Tenure | ✅ Básico | ✅ Com análise risco | Expandir |
| Leaves | ✅ Completo | ❌ Não possui | Manter atual |

### 🔧 REQUER IMPLEMENTAÇÃO

| Indicador | Analiticos | Sistema Atual | Prioridade |
|-----------|------------|---------------|------------|
| Análise Salarial | ✅ Completo | ❌ Falta | 🔴 ALTA |
| Custo de Folha | ✅ Completo | ❌ Falta | 🔴 ALTA |
| Horas Extras | ✅ Completo | ❌ Falta | 🟡 MÉDIA |
| Benefícios | ✅ Completo | ❌ Falta | 🟡 MÉDIA |
| 13º Salário | ✅ Completo | ❌ Falta | 🟡 MÉDIA |
| Comparativo Divisões | ✅ Completo | ❌ Falta | 🟢 BAIXA |
| Insalubridade | ✅ Completo | ❌ Falta | 🟢 BAIXA |

### ⚠️ ATENÇÃO: Duplicação de Dados

**Problema:** Benefícios podem estar em 2 lugares:
- `benefit_records` (tabela dedicada)
- `payroll_data.benefits_data` (JSON)

**Solução Recomendada:**
1. Usar `payroll_data.benefits_data` como fonte única (mais flexível)
2. Depreciar `benefit_records` ou usar apenas para histórico
3. Criar view SQL unificada:
```sql
CREATE VIEW unified_benefits AS
SELECT 
    employee_id,
    period_id,
    benefits_data->>'PLANO_SAUDE' AS health_plan,
    benefits_data->>'VT' AS transport
FROM payroll_data
WHERE benefits_data IS NOT NULL;
```

---

## 8. CHECKLIST DE VALIDAÇÃO

Antes de considerar a integração completa:

- [ ] Upload de CSV salva corretamente em `payroll_data`
- [ ] Parsing de números BR (1.234,56) funciona sem erros
- [ ] Parsing de datas DD/MM/AAAA funciona sem erros
- [ ] Todos os 7 novos indicadores retornam dados válidos
- [ ] Cache de indicadores invalida após upload
- [ ] Frontend exibe gráficos sem erros
- [ ] Exportação para Excel funciona
- [ ] Performance: queries < 2 segundos (com cache)
- [ ] Performance: queries < 5 segundos (sem cache)
- [ ] Documentação de API atualizada
- [ ] Testes unitários criados para parsers
- [ ] Testes de integração para indicadores

---

## 9. PRÓXIMOS PASSOS RECOMENDADOS

### Imediato (Esta Semana):
1. **Decisão de Arquitetura:** 
   - Validar escolha de `payroll_data` (JSONB) vs expansão de colunas fixas
   - Definir fonte única de benefícios

2. **Criar Estrutura Base:**
   ```bash
   mkdir -p backend/app/utils
   touch backend/app/utils/parsers.py
   touch backend/app/services/payroll_csv_processor.py
   touch backend/app/services/payroll_calculator.py
   ```

3. **Implementar Primeiro Indicador Novo:**
   - Começar com análise salarial (mais simples)
   - Validar padrão para os demais

### Curto Prazo (Próximas 2 Semanas):
4. **Upload CSV End-to-End:**
   - Testar com 1 CSV real de Empreendimentos
   - Validar salvamento em `payroll_data`
   - Verificar indicadores atualizados

5. **Dashboard Protótipo:**
   - Adicionar 1-2 novos indicadores no frontend
   - Validar usabilidade com usuários

### Médio Prazo (Próximo Mês):
6. **Completar Todos os 7 Indicadores Novos**
7. **Implementar Exportação Excel**
8. **Configurar Processamento Assíncrono**

---

## 10. CONCLUSÃO

**Principais Descobertas:**
- ✅ Sistema atual tem **base sólida** (6 indicadores funcionando)
- ✅ Scripts Analiticos trazem **7 indicadores novos** (todos viáveis)
- ✅ **Não há conflitos** diretos, apenas lacunas a preencher
- ⚠️ Maior desafio: **processar CSVs grandes** (5k+ linhas) de forma eficiente
- ⚠️ Decisão crítica: **JSONB vs colunas fixas** para dados dinâmicos

**Recomendação Final:**
Seguir implementação **faseada de 11 semanas** conforme descrito acima, priorizando:
1. **FASE 1 (fundação)** - Essencial para tudo mais
2. **FASE 2 (indicadores financeiros)** - Maior valor de negócio
3. **FASE 5 (automação)** - Escalabilidade

Com esta abordagem, teremos um sistema completo de **análise de RH** integrando o melhor dos scripts Analiticos com a interface web moderna já construída.

---

**Documento gerado em:** 16/01/2026  
**Próxima revisão:** Após FASE 1 completa
