#!/usr/bin/env python3
"""
Script para analisar todos os status únicos de colaboradores nos CSVs e no consolidado
"""
import os
import pandas as pd
from collections import Counter
import glob

def analyze_csv_files():
    """Analisa todos os CSVs nas pastas de uploads, processed e Analiticos"""
    
    all_status = []
    files_analyzed = 0
    
    # Caminhos para buscar CSVs
    search_paths = [
        r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\uploads\*.CSV',
        r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\processed\*.CSV',
        r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\*.CSV',
        r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Infraestrutura\*.CSV',
    ]
    
    print("=" * 80)
    print("ANÁLISE DE STATUS DE COLABORADORES - CSVs")
    print("=" * 80)
    print()
    
    for pattern in search_paths:
        csv_files = glob.glob(pattern)
        
        for csv_file in csv_files:
            try:
                # Tentar diferentes encodings e delimitadores
                df = None
                for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                    for delimiter in [';', ',']:
                        try:
                            df = pd.read_csv(csv_file, encoding=encoding, delimiter=delimiter)
                            # Verificar se tem colunas esperadas
                            if any(col in df.columns for col in ['Descrição', 'Descricao', 'Situação', 'Situacao', 'Status']):
                                break
                        except:
                            continue
                    if df is not None and any(col in df.columns for col in ['Descrição', 'Descricao', 'Situação', 'Situacao', 'Status']):
                        break
                
                if df is None:
                    continue
                
                # Identificar coluna de status
                status_col = None
                for col in ['Descrição', 'Descricao', 'Status', 'Situação', 'Situacao', 'DESCRIÇÃO', 'DESCRICAO', 'STATUS', 'SITUAÇÃO', 'SITUACAO']:
                    if col in df.columns:
                        status_col = col
                        break
                
                if status_col:
                    # Extrair status não-nulos
                    status_values = df[status_col].dropna().unique()
                    all_status.extend(status_values)
                    files_analyzed += 1
                    print(f"✅ {os.path.basename(csv_file)}: {len(status_values)} status únicos")
                    
            except Exception as e:
                print(f"⚠️  Erro ao processar {os.path.basename(csv_file)}: {e}")
    
    print()
    print(f"📊 Total de arquivos analisados: {files_analyzed}")
    print()
    
    return all_status


def analyze_consolidated_xlsx():
    """Analisa o arquivo consolidado XLSX"""
    
    consolidated_path = r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\consolidado_unificado.xlsx'
    
    print("=" * 80)
    print("ANÁLISE DE STATUS - CONSOLIDADO UNIFICADO")
    print("=" * 80)
    print()
    
    if not os.path.exists(consolidated_path):
        print("❌ Arquivo consolidado não encontrado")
        return []
    
    try:
        # Ler XLSX
        df = pd.read_excel(consolidated_path)
        
        # Identificar coluna de status
        status_col = None
        for col in ['Descrição', 'Descricao', 'Status', 'Situação', 'Situacao', 'DESCRIÇÃO', 'DESCRICAO', 'STATUS', 'SITUAÇÃO', 'SITUACAO']:
            if col in df.columns:
                status_col = col
                break
        
        if status_col:
            status_values = df[status_col].dropna().unique()
            print(f"✅ Consolidado: {len(status_values)} status únicos encontrados")
            print(f"📋 Colunas disponíveis: {', '.join(df.columns.tolist()[:10])}...")
            print()
            return status_values.tolist()
        else:
            print(f"❌ Coluna de status não encontrada")
            print(f"📋 Colunas disponíveis: {', '.join(df.columns.tolist())}")
            return []
            
    except Exception as e:
        print(f"❌ Erro ao processar consolidado: {e}")
        return []


def categorize_status(all_status):
    """Categoriza os status encontrados"""
    
    print("=" * 80)
    print("CATEGORIZAÇÃO DE STATUS")
    print("=" * 80)
    print()
    
    # Contar ocorrências
    counter = Counter(all_status)
    
    # Categorizar
    categories = {
        'Trabalhando': [],
        'Férias': [],
        'Afastados': [],
        'Desligados': [],
        'Outros': []
    }
    
    for status, count in counter.most_common():
        status_lower = str(status).lower()
        
        if 'trabalhando' in status_lower or 'ativo' in status_lower:
            categories['Trabalhando'].append((status, count))
        elif 'férias' in status_lower or 'ferias' in status_lower:
            categories['Férias'].append((status, count))
        elif any(word in status_lower for word in ['afastado', 'licença', 'licenca', 'auxílio', 'auxilio', 'atestado', 'maternidade', 'paternidade']):
            categories['Afastados'].append((status, count))
        elif any(word in status_lower for word in ['demitido', 'rescisão', 'rescisao', 'desligado']):
            categories['Desligados'].append((status, count))
        else:
            categories['Outros'].append((status, count))
    
    # Exibir resultados
    for category, items in categories.items():
        if items:
            print(f"\n🏷️  {category.upper()}")
            print("-" * 80)
            for status, count in sorted(items, key=lambda x: x[1], reverse=True):
                print(f"   • {status} ({count} ocorrências)")
    
    return categories


def suggest_backend_mapping(categories):
    """Sugere mapeamento para o backend"""
    
    print()
    print("=" * 80)
    print("SUGESTÃO DE MAPEAMENTO PARA O BACKEND")
    print("=" * 80)
    print()
    
    print("📝 Adicionar no arquivo backend/main_legacy.py (função handle_payroll_statistics_filtered):")
    print()
    print("```python")
    print("# Categorização de status")
    print("status_categories = {")
    
    # Gerar mapeamento para cada categoria
    for category in ['Trabalhando', 'Férias', 'Afastados', 'Desligados']:
        if categories[category]:
            print(f"    '{category.lower()}': [")
            for status, _ in categories[category]:
                print(f"        '{status}',")
            print("    ],")
    
    print("}")
    print("```")
    print()
    
    # Sugestão de SQL
    print("📝 Query SQL sugerida para contar Afastados:")
    print()
    print("```sql")
    afastados_patterns = [status for status, _ in categories['Afastados']]
    if afastados_patterns:
        conditions = " OR ".join([f"additional_data->>'Status' LIKE '%{status}%'" for status in afastados_patterns[:5]])
        print(f"""
SELECT COUNT(DISTINCT e.id)
FROM employees e
INNER JOIN payroll_data pd ON pd.employee_id = e.id
WHERE pd.period_id = :period_id
AND ({conditions})
""")
    print("```")


def main():
    """Função principal"""
    
    print()
    print("🔍 INICIANDO ANÁLISE DE STATUS DE COLABORADORES")
    print()
    
    # Analisar CSVs
    csv_status = analyze_csv_files()
    
    # Analisar consolidado
    consolidated_status = analyze_consolidated_xlsx()
    
    # Combinar todos
    all_status = csv_status + consolidated_status
    
    if not all_status:
        print("❌ Nenhum status encontrado!")
        return
    
    # Categorizar
    categories = categorize_status(all_status)
    
    # Sugerir mapeamento
    suggest_backend_mapping(categories)
    
    # Estatísticas finais
    print()
    print("=" * 80)
    print("RESUMO GERAL")
    print("=" * 80)
    print()
    print(f"📊 Total de status únicos encontrados: {len(set(all_status))}")
    print(f"📊 Total de ocorrências analisadas: {len(all_status)}")
    print()
    print("✅ Análise concluída!")
    print()


if __name__ == "__main__":
    main()
