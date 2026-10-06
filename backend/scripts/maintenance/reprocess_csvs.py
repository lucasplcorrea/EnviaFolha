"""
Script para re-processar todos os CSVs com o processador atualizado
Isso vai preencher os campos earnings_data, benefits_data e additional_data
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from common import ensure_backend_on_path, get_analytics_dir, get_database_url, load_repo_env

ensure_backend_on_path()

from app.services.payroll_csv_processor import PayrollCSVProcessor

load_repo_env()

database_url = get_database_url()

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)

def reprocess_all_csvs():
    """Re-processa todos os CSVs encontrados"""
    
    # Encontrar todos os CSVs em Analiticos/Empreendimentos
    csv_dir = get_analytics_dir()
    csv_files = sorted(csv_dir.glob('*.CSV'))
    
    print("="*80)
    print("🔄 RE-PROCESSAMENTO DE CSVs COM CÓDIGO ATUALIZADO")
    print("="*80)
    print(f"\nEncontrados {len(csv_files)} arquivos CSV em {csv_dir}\n")
    
    session = SessionLocal()
    processor = PayrollCSVProcessor(session)
    
    results = []
    
    for csv_file in csv_files:
        print(f"\n{'─'*80}")
        print(f"📄 Processando: {csv_file.name}")
        print(f"{'─'*80}")
        
        try:
            result = processor.process_csv_file(
                file_path=str(csv_file),
                division_code='0060',  # Empreendimentos
                auto_create_employees=False
            )
            
            if result['success']:
                print(f"✅ Sucesso!")
                print(f"   - Período: {result['period_name']}")
                print(f"   - Total processado: {result['stats']['total_processed']} registros")
                print(f"   - Novos funcionários: {result['stats']['new_employees']}")
                print(f"   - Atualizados: {result['stats']['updated_records']}")
                print(f"   - Erros: {len(result['errors'])}")
                
                results.append({
                    'file': csv_file.name,
                    'status': 'success',
                    'result': result
                })
            else:
                print(f"❌ Falha no processamento")
                print(f"   - Erros: {result.get('errors', [])}")
                results.append({
                    'file': csv_file.name,
                    'status': 'error',
                    'error': str(result.get('errors', 'Unknown error'))
                })
            
        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            results.append({
                'file': csv_file.name,
                'status': 'error',
                'error': str(e)
            })
    
    session.close()
    
    # Resumo final
    print(f"\n{'='*80}")
    print("📊 RESUMO FINAL")
    print(f"{'='*80}")
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"\n✅ Processados com sucesso: {len(successful)}")
    print(f"❌ Com erros: {len(failed)}")
    
    if successful:
        total_records = sum(r['result']['stats']['total_processed'] for r in successful)
        total_new = sum(r['result']['stats']['new_employees'] for r in successful)
        total_updated = sum(r['result']['stats']['updated_records'] for r in successful)
        print(f"\n📈 Total de registros processados: {total_records}")
        print(f"👥 Total de novos funcionários: {total_new}")
        print(f"🔄 Total de registros atualizados: {total_updated}")
    
    print(f"\n{'='*80}")
    print("🔍 Verificando dados após re-processamento...")
    print(f"{'='*80}\n")
    
    # Verificar dados
    session = SessionLocal()
    result = session.execute(text("""
        SELECT 
            pp.period_name,
            COUNT(*) as total,
            COUNT(CASE WHEN pd.earnings_data::text != '{}' THEN 1 END) as with_earnings,
            COUNT(CASE WHEN pd.additional_data::text != '{}' THEN 1 END) as with_additional,
            COALESCE(SUM((pd.additional_data->>'TOTAL_PROVENTOS')::numeric), 0) as total_proventos,
            COALESCE(SUM((pd.additional_data->>'TOTAL_DESCONTOS')::numeric), 0) as total_descontos
        FROM payroll_data pd
        JOIN payroll_periods pp ON pd.period_id = pp.id
        GROUP BY pp.period_name, pp.month, pp.year
        ORDER BY pp.year, pp.month
    """))
    
    print(f"{'Período':<20} {'Registros':>10} {'c/ Earnings':>12} {'c/ Additional':>15} {'Proventos':>15} {'Descontos':>15}")
    print("─" * 100)
    
    for row in result:
        print(f"{row[0]:<20} {row[1]:>10} {row[2]:>12} {row[3]:>15} R$ {row[4]:>12,.2f} R$ {row[5]:>12,.2f}")
    
    session.close()
    print("="*80)

if __name__ == "__main__":
    try:
        reprocess_all_csvs()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
