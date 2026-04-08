"""
Utilitários para parsing de dados em formato brasileiro
Reutilizado dos scripts Analiticos (consolidar_empreendimentos.py)
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd


def parse_br_number(value) -> float:
    """
    Converte valor em formato brasileiro para float
    
    Formato BR: 1.234,56 → Float: 1234.56
    
    Args:
        value: String ou número a ser convertido
        
    Returns:
        Float convertido ou 0.0 se inválido
        
    Examples:
        >>> parse_br_number("1.234,56")
        1234.56
        >>> parse_br_number("1234,56")
        1234.56
        >>> parse_br_number("R$ 1.234,56")
        1234.56
        >>> parse_br_number("")
        0.0
    """
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    # Converter para string
    value_str = str(value).strip()
    
    # Remover prefixos comuns (R$, -, etc)
    value_str = value_str.replace('R$', '').replace('-', '').strip()
    
    # Formato brasileiro: separador de milhar (.) e decimal (,)
    # Remove pontos (milhares) e substitui vírgula por ponto (decimal)
    value_str = value_str.replace('.', '').replace(',', '.')
    
    try:
        return float(value_str)
    except ValueError:
        # Se falhar, retornar 0
        return 0.0


def parse_br_date(date_str) -> Optional[datetime]:
    """
    Converte data em formato brasileiro para datetime
    
    Formato BR: DD/MM/AAAA → datetime
    
    Args:
        date_str: String da data no formato DD/MM/AAAA
        
    Returns:
        datetime object ou None se inválido
        
    Examples:
        >>> parse_br_date("31/12/2024")
        datetime(2024, 12, 31)
        >>> parse_br_date("01/01/2025")
        datetime(2025, 1, 1)
        >>> parse_br_date("")
        None
    """
    if pd.isna(date_str) or date_str == '' or date_str is None:
        return None
    
    # Tentar diferentes formatos
    formats = [
        '%d/%m/%Y',  # 31/12/2024
        '%d/%m/%y',  # 31/12/24
        '%Y-%m-%d',  # 2024-12-31 (ISO)
    ]
    
    date_str = str(date_str).strip()
    
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    
    # Se todos falharem, retornar None
    return None


def detect_payroll_type(filename: str) -> Dict[str, Any]:
    """
    Detecta tipo de arquivo de folha via regex
    
    Baseado em: consolidar_empreendimentos.py (linhas 24-78)
    
    Args:
        filename: Nome do arquivo (ex: "01-2024.CSV")
        
    Returns:
        Dict com { 'tipo', 'mes', 'ano', 'matched' }
        
    Examples:
        >>> detect_payroll_type("01-2024.CSV")
        {'tipo': 'mensal', 'mes': '01', 'ano': '2024', 'matched': True}
        
        >>> detect_payroll_type("AdiantamentoDecimoTerceiro_11-2024.csv")
        {'tipo': '13_adiantamento', 'mes': '11', 'ano': '2024', 'matched': True}
    """
    # Padrões de detecção (ordem de prioridade)
    patterns = {
        '13_adiantamento': r'AdiantamentoDecimoTerceiro.*?(\d{2})-(\d{4})',
        '13_integral': r'IntegralDecimoTerceiro.*?(\d{2})-(\d{4})',
        'complementar': r'(?:FolhaComplementar|Complementar).*?(\d{2})-(\d{4})',
        'adiantamento_salario': r'Adiantamento.*?(\d{2})-(\d{4})',
        'mensal': r'(\d{2})-(\d{4})\.CSV',  # Padrão simples: 01-2024.CSV
    }

    month_aliases = {
        '01': 1, '1': 1, 'jan': 1, 'jane': 1, 'janeiro': 1,
        '02': 2, '2': 2, 'fev': 2, 'feve': 2, 'fevereiro': 2,
        '03': 3, '3': 3, 'mar': 3, 'marco': 3, 'março': 3,
        '04': 4, '4': 4, 'abr': 4, 'abril': 4,
        '05': 5, '5': 5, 'mai': 5, 'maio': 5,
        '06': 6, '6': 6, 'jun': 6, 'junho': 6,
        '07': 7, '7': 7, 'jul': 7, 'julho': 7,
        '08': 8, '8': 8, 'ago': 8, 'agosto': 8,
        '09': 9, '9': 9, 'set': 9, 'setembro': 9,
        '10': 10, 'out': 10, 'outubro': 10,
        '11': 11, 'nov': 11, 'novembro': 11,
        '12': 12, 'dez': 12, 'dezembro': 12,
    }
    
    for tipo, pattern in patterns.items():
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            mes = match.group(1)
            ano = match.group(2)
            return {
                'tipo': tipo,
                'mes': mes,
                'ano': ano,
                'matched': True,
                'filename': filename
            }

    # Padrões alternativos: emp-jane-2026.csv, folha_jan_2026.csv, etc.
    alt_match = re.search(r'([a-zçãé]{3,10}|\d{1,2})[-_](\d{4})(?:\.csv)?$', filename, re.IGNORECASE)
    if alt_match:
        month_token = (alt_match.group(1) or '').strip().lower()
        year_token = alt_match.group(2)
        month_number = month_aliases.get(month_token)
        if month_number:
            return {
                'tipo': 'mensal',
                'mes': str(month_number).zfill(2),
                'ano': year_token,
                'matched': True,
                'filename': filename
            }
    
    # Se não matchou nenhum padrão
    return {
        'tipo': 'desconhecido',
        'mes': None,
        'ano': None,
        'matched': False,
        'filename': filename
    }


def extract_employee_code(codigo_func: str, division_code: str = '0060') -> str:
    """
    Extrai e formata código de funcionário (matrícula)
    
    Formato: XXXX + YYYYY = 9 dígitos
    - XXXX: Código da empresa/divisão (0060 ou 0059)
    - YYYYY: Código do funcionário (5 dígitos)
    
    Args:
        codigo_func: Código do funcionário no CSV
        division_code: Código da divisão ('0060' para Empreendimentos, '0059' para Infraestrutura)
        
    Returns:
        Matrícula completa (9 dígitos)
        
    Examples:
        >>> extract_employee_code("123", "0060")
        "006000123"
        >>> extract_employee_code("00123", "0059")
        "005900123"
    """
    if not codigo_func:
        return None
    
    # Remover espaços e garantir string
    codigo_str = str(codigo_func).strip()
    
    # Preencher com zeros à esquerda (5 dígitos)
    codigo_func_padded = codigo_str.zfill(5)
    
    # Concatenar com código da divisão
    matricula_completa = f"{division_code}{codigo_func_padded}"
    
    return matricula_completa


def normalize_cpf(cpf: str) -> str:
    """
    Normaliza CPF para formato XXX.XXX.XXX-XX
    
    Args:
        cpf: CPF em qualquer formato
        
    Returns:
        CPF formatado ou string original se inválido
        
    Examples:
        >>> normalize_cpf("12345678901")
        "123.456.789-01"
        >>> normalize_cpf("123.456.789-01")
        "123.456.789-01"
    """
    if not cpf:
        return ''
    
    # Remover tudo que não for número
    cpf_digits = re.sub(r'\D', '', str(cpf))
    
    # Validar tamanho
    if len(cpf_digits) != 11:
        return str(cpf)  # Retornar original se inválido
    
    # Formatar: XXX.XXX.XXX-XX
    return f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"


def normalize_phone(phone: str) -> str:
    """
    Normaliza telefone para formato brasileiro (+55 XX XXXXX-XXXX)
    
    Args:
        phone: Telefone em qualquer formato
        
    Returns:
        Telefone formatado ou string original se inválido
        
    Examples:
        >>> normalize_phone("11987654321")
        "+55 11 98765-4321"
        >>> normalize_phone("(11) 98765-4321")
        "+55 11 98765-4321"
    """
    if not phone:
        return ''
    
    # Remover tudo que não for número
    phone_digits = re.sub(r'\D', '', str(phone))
    
    # Se já tem código do país, remover
    if phone_digits.startswith('55'):
        phone_digits = phone_digits[2:]
    
    # Validar tamanho (deve ter 10 ou 11 dígitos: DDD + número)
    if len(phone_digits) not in [10, 11]:
        return str(phone)  # Retornar original se inválido
    
    # Extrair DDD
    ddd = phone_digits[:2]
    
    # Extrair número (com ou sem 9º dígito)
    if len(phone_digits) == 11:
        numero = f"{phone_digits[2:7]}-{phone_digits[7:]}"
    else:
        numero = f"{phone_digits[2:6]}-{phone_digits[6:]}"
    
    return f"+55 {ddd} {numero}"


# Constantes de mapeamento
CSV_COLUMN_MAPPING = {
    # Identificação
    'CODIGO_FUNC': 'codigo_funcionario',
    'NOME': 'name',
    'CPF': 'cpf',
    
    # Dados pessoais
    'SEXO': 'sex',
    'ESTADO_CIVIL': 'marital_status',
    'DT_NASCIMENTO': 'birth_date',
    'DT_ADMISSAO': 'admission_date',
    'DT_DEMISSAO': 'termination_date',
    
    # Estrutura organizacional
    'DEPARTAMENTO': 'department',
    'CARGO': 'position',
    'SETOR': 'sector',
    
    # Contato
    'TELEFONE': 'phone',
    'EMAIL': 'email',
    
    # Proventos (vão para earnings_data JSON)
    'SALARIO_BASE': 'SALARIO_BASE',
    'HORAS_EXTRAS_50': 'HE_50',
    'HORAS_EXTRAS_100': 'HE_100',
    'ADICIONAL_NOTURNO': 'ADIC_NOTURNO',
    'FERIAS': 'FERIAS',
    '13_SALARIO': '13_SALARIO',
    'COMISSOES': 'COMISSOES',
    'BONUS': 'BONUS',
    
    # Descontos (vão para deductions_data JSON)
    'INSS': 'INSS',
    'IRRF': 'IRRF',
    'FGTS': 'FGTS',
    'CONTRIBUICAO_SINDICAL': 'SIND',
    'PENSAO_ALIMENTICIA': 'PENSAO',
    'ADIANTAMENTO': 'ADIANTAMENTO',
    
    # Benefícios (vão para benefits_data JSON)
    'PLANO_SAUDE': 'PLANO_SAUDE',
    'VALE_TRANSPORTE': 'VT',
    'VALE_ALIMENTACAO': 'VA',
    'VALE_REFEICAO': 'VR',
    
    # Adicionais (vão para additional_data JSON)
    'ADIC_INSALUBRIDADE': 'INSALUBRIDADE',
    'ADIC_PERICULOSIDADE': 'PERICULOSIDADE',
    
    # Totalizadores
    'TOTAL_PROVENTOS': 'total_proventos',
    'TOTAL_DESCONTOS': 'total_descontos',
    'LIQ_A_RECEBER': 'liquido_receber',
}


def map_csv_column(csv_column: str) -> str:
    """
    Mapeia nome de coluna do CSV para nome interno
    
    Args:
        csv_column: Nome da coluna no CSV (ex: "CODIGO_FUNC")
        
    Returns:
        Nome mapeado (ex: "codigo_funcionario")
    """
    return CSV_COLUMN_MAPPING.get(csv_column.upper(), csv_column)


def normalize_name_for_payroll(name: str) -> str:
    """
    Normaliza nome para matching de CSVs: UPPERCASE + sem acentos + sem pontuação
    
    Função auxiliar para geração de name_id. Remove variações de acentuação e 
    pontuação que causam false negatives em matching de nomes.
    
    Padrão: "João da Silva" → "JOAO DA SILVA"
    
    Args:
        name: Nome original (ex: "José Alberto Gómez")
        
    Returns:
        Nome normalizado (ex: "JOSE ALBERTO GOMEZ")
        
    Examples:
        >>> normalize_name_for_payroll("João da Silva")
        "JOAO DA SILVA"
        >>> normalize_name_for_payroll("MARIA DE JESUS")
        "MARIA DE JESUS"
        >>> normalize_name_for_payroll("Luís Henrique")
        "LUIS HENRIQUE"
        >>> normalize_name_for_payroll("D'Angelo")
        "DANGELO"
    """
    import unicodedata
    
    if not name:
        return ""
    
    # 1. Converter para UPPERCASE
    s = str(name).strip().upper()
    
    # 2. Normalizar acentuação (NFKD: decomposição compatível)
    s = unicodedata.normalize("NFKD", s)
    
    # 3. Remover caracteres de combinação (acentos, til, etc)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    
    # 4. Remover pontuação e símbolos especiais, mantendo apenas A-Z, 0-9 e espaços
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    
    # 5. Collapse múltiplos espaços em um
    s = re.sub(r"\s+", " ", s).strip()
    
    return s


def generate_name_id(company_code: str, registration_number: str, name: str) -> Optional[str]:
    """
    Gera chave auxiliar de matching: company_code + registration_number (5 dígitos) + nome normalizado
    
    Formato exemplo: "0060" + "00048" + "JOAO SILVA" = "006000048JOAO SILVA"
    
    Esta chave permite matching robusto de CSVs que não têm CPF, utilizando:
    - Código da empresa (imutável)
    - Número da matrícula (5 dígitos, padronizado)
    - Nome normalizado (sem acentos, maiúscula, sem pontuação)
    
    Args:
        company_code: Código da empresa (ex: "0060", "0059")
        registration_number: Número de matrícula (ex: "123" → "00123")
        name: Nome do funcionário (será normalizado)
        
    Returns:
        name_id formatado ou None se algum campo inválido
        
    Examples:
        >>> generate_name_id("0060", "123", "João Silva")
        "006000123JOAO SILVA"
        >>> generate_name_id("0059", "8", "Maria de Jesus")
        "005900008MARIA DE JESUS"
    """
    if not company_code or not registration_number or not name:
        return None
    
    # Normalizar código da empresa (remover pontos, pegar 4 primeiros dígitos)
    code = re.sub(r'\D', '', str(company_code))[-4:].zfill(4)
    
    # Normalizar matrícula (5 dígitos à esquerda)
    regnum = str(registration_number).strip()
    regnum = re.sub(r'\D', '', regnum).zfill(5)[-5:]
    
    # Normalizar nome
    normalized_name = normalize_name_for_payroll(name)
    
    if not normalized_name:
        return None
    
    return f"{code}{regnum}{normalized_name}"


if __name__ == '__main__':
    # Testes rápidos
    print("=== Testes de Parsers ===\n")
    
    print("1. parse_br_number:")
    print(f"   '1.234,56' → {parse_br_number('1.234,56')}")
    print(f"   'R$ 1.234,56' → {parse_br_number('R$ 1.234,56')}")
    print(f"   '' → {parse_br_number('')}")
    
    print("\n2. parse_br_date:")
    print(f"   '31/12/2024' → {parse_br_date('31/12/2024')}")
    print(f"   '01/01/2025' → {parse_br_date('01/01/2025')}")
    
    print("\n3. detect_payroll_type:")
    print(f"   '01-2024.CSV' → {detect_payroll_type('01-2024.CSV')}")
    print(f"   'AdiantamentoDecimoTerceiro_11-2024.csv' → {detect_payroll_type('AdiantamentoDecimoTerceiro_11-2024.csv')}")
    
    print("\n4. extract_employee_code:")
    print(f"   ('123', '0060') → {extract_employee_code('123', '0060')}")
    print(f"   ('00123', '0059') → {extract_employee_code('00123', '0059')}")
    
    print("\n5. normalize_cpf:")
    print(f"   '12345678901' → {normalize_cpf('12345678901')}")
    
    print("\n6. normalize_phone:")
    print(f"   '11987654321' → {normalize_phone('11987654321')}")
    
    print("\n✅ Testes concluídos!")
