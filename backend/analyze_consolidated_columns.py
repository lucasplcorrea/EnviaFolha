"""
Analisa o arquivo Consolidado_Unificado.xlsx para identificar todas as colunas
e valores relacionados a horas extras, benefícios e outros itens da folha
"""
import pandas as pd
import sys
from pathlib import Path

# Caminho do arquivo consolidado
CONSOLIDADO_PATH = r"C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Consolidado_Unificado.xlsx"

def analyze_columns():
    """Analisa colunas do arquivo consolidado"""
    print("\n" + "="*100)
    print("📊 ANÁLISE DO ARQUIVO CONSOLIDADO_UNIFICADO.XLSX")
    print("="*100)
    
    # Ler arquivo
    df = pd.read_excel(CONSOLIDADO_PATH)
    
    print(f"\n📈 Total de linhas: {len(df)}")
    print(f"📋 Total de colunas: {len(df.columns)}")
    
    # Categorizar colunas
    categories = {
        'Horas Extras': [],
        'Adicional Noturno': [],
        'Férias': [],
        'DSR': [],
        'Benefícios': [],
        'Vale': [],
        'Gratificações': [],
        'Adicionais': [],
        'Faltas/Descontos': [],
        'Empréstimos': [],
        'Pensão': [],
        'INSS': [],
        'IRRF': [],
        'FGTS': [],
        'Outras': []
    }
    
    # Classificar cada coluna
    for col in df.columns:
        col_lower = col.lower()
        
        if 'hora' in col_lower and 'extra' in col_lower:
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
        elif 'saúde' in col_lower or 'saude' in col_lower or 'plano' in col_lower:
            categories['Benefícios'].append(col)
        elif 'falta' in col_lower or 'atraso' in col_lower or 'desconto' in col_lower:
            categories['Faltas/Descontos'].append(col)
        elif 'empréstimo' in col_lower or 'emprestimo' in col_lower:
            categories['Empréstimos'].append(col)
        elif 'pensão' in col_lower or 'pensao' in col_lower:
            categories['Pensão'].append(col)
        elif 'inss' in col_lower:
            categories['INSS'].append(col)
        elif 'irrf' in col_lower or 'ir s/' in col_lower:
            categories['IRRF'].append(col)
        elif 'fgts' in col_lower:
            categories['FGTS'].append(col)
        else:
            categories['Outras'].append(col)
    
    # Exibir categorias
    for category, cols in categories.items():
        if cols:
            print(f"\n{'='*100}")
            print(f"📂 {category.upper()} ({len(cols)} colunas)")
            print(f"{'='*100}")
            
            for col in sorted(cols):
                # Calcular estatísticas básicas
                non_zero = df[col].notna() & (df[col] != 0)
                total_registros = non_zero.sum()
                
                if total_registros > 0:
                    soma = df.loc[non_zero, col].sum()
                    media = df.loc[non_zero, col].mean()
                    print(f"   ✓ {col:<60} | {total_registros:>4} registros | Total: R$ {soma:>12,.2f} | Média: R$ {media:>10,.2f}")
                else:
                    print(f"   ○ {col:<60} | SEM DADOS")
    
    # Resumo de categorias não vazias
    print(f"\n{'='*100}")
    print("📊 RESUMO POR CATEGORIA")
    print(f"{'='*100}")
    
    for category, cols in categories.items():
        cols_with_data = []
        for col in cols:
            non_zero = df[col].notna() & (df[col] != 0)
            if non_zero.sum() > 0:
                cols_with_data.append(col)
        
        if cols_with_data:
            print(f"\n{category}: {len(cols_with_data)}/{len(cols)} colunas com dados")
    
    # Identificar colunas que estamos usando atualmente
    print(f"\n{'='*100}")
    print("🔍 VERIFICAÇÃO: COLUNAS JÁ CAPTURADAS NO SISTEMA")
    print(f"{'='*100}")
    
    currently_captured = [
        'Salário Mensal',
        'Valor Salário',
        'Total de Proventos',
        'Total de Descontos',
        'Total de Vantagens',
        'Líquido de Cálculo',
        'Horas Normais Diurnas',
        'Horas Extras 50% Diurnas',
        'Horas DSR Diurnas',
        'Descrição',  # Status
        'INSS',
        'INSS S/13o Salário',
        'INSS S/Férias',
        'Devolução INSS Mês',
        'IRRF',
        'IRRF Férias na Rescisão',
        'IRRF S/13o Salário',
        'IRRF S/Férias',
        'FGTS',
        'FGTS 13o Salário GRFC',
        'FGTS GRFC',
        'FGTS Multa - Depósito Saldo',
        'FGTS S/13o Sal.Proporc.Resc.',
        'FGTS S/Aviso Prévio Indenizado',
        'FGTS S/Férias',
        'FGTS s/13o Salário Indenizado GRFC',
        'Mensalidade  Plano de Saúde',
        'Planos de Saúde - Total da Fatura',
        'Benefício Plano de Saúde - Mensalidade',
        'Saude Bradesco'
    ]
    
    available_cols = set(df.columns)
    captured = [col for col in currently_captured if col in available_cols]
    not_captured = [col for col in currently_captured if col not in available_cols]
    
    print(f"\n✅ Capturadas e disponíveis ({len(captured)}):")
    for col in sorted(captured):
        print(f"   • {col}")
    
    if not_captured:
        print(f"\n⚠️  Configuradas mas não encontradas ({len(not_captured)}):")
        for col in sorted(not_captured):
            print(f"   • {col}")
    
    # Sugestões de novas colunas
    print(f"\n{'='*100}")
    print("💡 SUGESTÕES DE NOVAS COLUNAS PARA ADICIONAR AOS INDICADORES")
    print(f"{'='*100}")
    
    suggestions = {
        'Horas Extras 100%': [col for col in categories['Horas Extras'] if '100%' in col],
        'Adicional Noturno': categories['Adicional Noturno'][:3],  # Top 3
        'Vale Transporte': [col for col in categories['Vale'] if 'transporte' in col.lower()],
        'Vale Alimentação': [col for col in categories['Vale'] if 'alimentação' in col.lower() or 'alimentacao' in col.lower()],
        'Gratificações': categories['Gratificações'][:5],
        'Adicionais Importantes': [col for col in categories['Adicionais'] if df[col].notna().sum() > 10][:5]
    }
    
    for suggestion_name, suggestion_cols in suggestions.items():
        if suggestion_cols:
            print(f"\n📌 {suggestion_name}:")
            for col in suggestion_cols:
                non_zero = df[col].notna() & (df[col] != 0)
                total = non_zero.sum()
                if total > 0:
                    soma = df.loc[non_zero, col].sum()
                    print(f"   • {col:<60} | {total} registros | R$ {soma:,.2f}")

if __name__ == "__main__":
    try:
        analyze_columns()
    except FileNotFoundError:
        print(f"\n❌ Arquivo não encontrado: {CONSOLIDADO_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
