"""
Análise rápida apenas dos headers do Consolidado_Unificado.xlsx
"""
import openpyxl
import sys

CONSOLIDADO_PATH = r"C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Consolidado_Unificado.xlsx"

print("\n📊 Carregando headers do arquivo...")
wb = openpyxl.load_workbook(CONSOLIDADO_PATH, read_only=True, data_only=True)
sheet = wb.active

# Ler apenas primeira linha (headers)
headers = []
for cell in next(sheet.iter_rows(min_row=1, max_row=1)):
    if cell.value:
        headers.append(str(cell.value))

print(f"✅ Total de colunas: {len(headers)}\n")

# Categorizar
categories = {
    'Horas Extras': [],
    'Adicional Noturno': [],
    'Férias': [],
    'DSR': [],
    'Benefícios/Saúde': [],
    'Vale': [],
    'Gratificações': [],
    'Adicionais': [],
    'Faltas/Descontos': [],
    'Empréstimos': [],
    'Pensão': [],
    'INSS': [],
    'IRRF': [],
    'FGTS': [],
    'Identificação': [],
    'Totalizadores': [],
    'Outras': []
}

# Classificar
for col in headers:
    col_lower = col.lower()
    
    if any(x in col_lower for x in ['código', 'cnpj', 'nome', 'cargo', 'admissão', 'salário mensal', 'valor salário']):
        categories['Identificação'].append(col)
    elif 'total' in col_lower or 'líquido' in col_lower or 'base' in col_lower:
        categories['Totalizadores'].append(col)
    elif 'hora' in col_lower and 'extra' in col_lower:
        categories['Horas Extras'].append(col)
    elif 'noturno' in col_lower or 'noturna' in col_lower:
        categories['Adicional Noturno'].append(col)
    elif 'dsr' in col_lower:
        categories['DSR'].append(col)
    elif 'férias' in col_lower or 'ferias' in col_lower:
        categories['Férias'].append(col)
    elif 'vale' in col_lower:
        categories['Vale'].append(col)
    elif 'gratificação' in col_lower or 'gratificacao' in col_lower:
        categories['Gratificações'].append(col)
    elif 'adicional' in col_lower and 'noturno' not in col_lower:
        categories['Adicionais'].append(col)
    elif 'saúde' in col_lower or 'saude' in col_lower or ('plano' in col_lower and 'saúde' not in col_lower):
        categories['Benefícios/Saúde'].append(col)
    elif 'falta' in col_lower or 'atraso' in col_lower or 'desconto' in col_lower:
        categories['Faltas/Descontos'].append(col)
    elif 'empréstimo' in col_lower or 'emprestimo' in col_lower:
        categories['Empréstimos'].append(col)
    elif 'pensão' in col_lower or 'pensao' in col_lower:
        categories['Pensão'].append(col)
    elif 'inss' in col_lower:
        categories['INSS'].append(col)
    elif 'irrf' in col_lower or 'ir s/' in col_lower or 'imposto de renda' in col_lower:
        categories['IRRF'].append(col)
    elif 'fgts' in col_lower:
        categories['FGTS'].append(col)
    else:
        categories['Outras'].append(col)

# Exibir resultados
print("="*100)
print("COLUNAS POR CATEGORIA")
print("="*100)

for category, cols in categories.items():
    if cols:
        print(f"\n📂 {category.upper()} ({len(cols)} colunas)")
        print("-"*100)
        for col in sorted(cols):
            print(f"   • {col}")

# Colunas atualmente capturadas
print("\n" + "="*100)
print("🔍 VERIFICAÇÃO: COLUNAS JÁ CAPTURADAS")
print("="*100)

currently_captured = {
    'Salário Mensal', 'Valor Salário', 'Total de Proventos', 'Total de Descontos',
    'Total de Vantagens', 'Líquido de Cálculo', 'Horas Normais Diurnas',
    'Horas Extras 50% Diurnas', 'Horas DSR Diurnas', 'Descrição',
    'INSS', 'INSS S/13o Salário', 'INSS S/Férias', 'Devolução INSS Mês',
    'IRRF', 'IRRF Férias na Rescisão', 'IRRF S/13o Salário', 'IRRF S/Férias',
    'FGTS', 'FGTS 13o Salário GRFC', 'FGTS GRFC', 'FGTS Multa - Depósito Saldo',
    'FGTS S/13o Sal.Proporc.Resc.', 'FGTS S/Aviso Prévio Indenizado',
    'FGTS S/Férias', 'FGTS s/13o Salário Indenizado GRFC',
    'Mensalidade  Plano de Saúde', 'Planos de Saúde - Total da Fatura',
    'Benefício Plano de Saúde - Mensalidade', 'Saude Bradesco'
}

headers_set = set(headers)
captured = currently_captured & headers_set
not_found = currently_captured - headers_set

print(f"\n✅ Capturadas ({len(captured)}):")
for col in sorted(captured):
    print(f"   • {col}")

if not_found:
    print(f"\n⚠️  Não encontradas ({len(not_found)}):")
    for col in sorted(not_found):
        print(f"   • {col}")

# Sugestões
print("\n" + "="*100)
print("💡 SUGESTÕES DE NOVAS COLUNAS")
print("="*100)

suggestions = {
    '💰 Horas Extras 100%': [col for col in categories['Horas Extras'] if '100' in col],
    '🌙 Adicional Noturno': categories['Adicional Noturno'],
    '🍽️ Vales (Transporte/Alimentação)': categories['Vale'][:10],
    '🎁 Gratificações': categories['Gratificações'][:10],
    '➕ Outros Adicionais': categories['Adicionais'][:10],
}

for title, suggestion_cols in suggestions.items():
    if suggestion_cols:
        print(f"\n{title}:")
        for col in suggestion_cols[:15]:  # Limitar a 15 por categoria
            print(f"   • {col}")

wb.close()
