"""
Script para reprocessar um período de folha de pagamento com as novas regras:
1. Status dos colaboradores (campo Descrição)
2. INSS com devolução subtraída
3. Total de Vantagens
"""
import sys
import os
from pathlib import Path

from common import ensure_backend_on_path

ensure_backend_on_path()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.payroll_csv_processor import PayrollCSVProcessor
import pandas as pd

def reprocess_period(csv_path: str, period_id: int):
    """Reprocessa um CSV de folha de pagamento"""
    
    # Conectar ao banco
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print(f"\n🔄 Reprocessando período {period_id}...")
        print(f"📁 CSV: {csv_path}")
        
        # Verificar se o CSV existe
        if not os.path.exists(csv_path):
            print(f"❌ Arquivo não encontrado: {csv_path}")
            return
        
        # Deletar dados existentes do período
        print(f"\n🗑️  Deletando dados existentes do período {period_id}...")
        delete_result = db.execute(
            text("DELETE FROM payroll_data WHERE period_id = :period_id"),
            {"period_id": period_id}
        )
        db.commit()
        print(f"✅ {delete_result.rowcount} registros deletados")
        
        # Reprocessar o CSV - usa o nome do arquivo para detectar divisão
        print(f"\n📊 Processando CSV...")
        processor = PayrollCSVProcessor(db)
        
        # O processor detecta automaticamente tipo e período do arquivo
        # Passa division_code='0060' para Empreendimentos
        results = processor.process_csv_file(
            file_path=csv_path,
            division_code='0060',  # Empreendimentos
            auto_create_employees=True
        )
        
        print(f"\n✅ Reprocessamento concluído!")
        if results.get('success'):
            print(f"   📈 Total processados: {results.get('stats', {}).get('processed', 0)}")
            print(f"   ❌ Erros: {results.get('stats', {}).get('errors', 0)}")
            print(f"   ⚠️  Avisos: {len(results.get('warnings', []))}")
        
        # Verificar status extraídos
        print(f"\n🔍 Verificando status dos colaboradores...")
        status_result = db.execute(text("""
            SELECT 
                additional_data->>'Status' as status,
                COUNT(*) as quantidade
            FROM payroll_data
            WHERE period_id = :period_id
              AND additional_data->>'Status' IS NOT NULL
            GROUP BY additional_data->>'Status'
            ORDER BY quantidade DESC
        """), {"period_id": period_id})
        
        status_rows = status_result.fetchall()
        if status_rows:
            print("\n📊 Status encontrados:")
            for row in status_rows:
                print(f"   {row[0]}: {row[1]} funcionários")
        else:
            print("\n⚠️  Nenhum status encontrado!")
        
        # Verificar INSS
        print(f"\n💰 Verificando INSS...")
        inss_result = db.execute(text("""
            SELECT 
                COUNT(*) as total_registros,
                COALESCE(SUM((deductions_data->>'INSS')::numeric), 0) as total_inss
            FROM payroll_data
            WHERE period_id = :period_id
        """), {"period_id": period_id})
        
        row = inss_result.fetchone()
        print(f"   Total INSS: R$ {row[1]:,.2f} ({row[0]} registros)")
        
        # Verificar Vantagens
        print(f"\n🎁 Verificando Total de Vantagens...")
        vantagens_result = db.execute(text("""
            SELECT 
                COUNT(CASE WHEN additional_data->>'Total de Vantagens' IS NOT NULL THEN 1 END) as com_vantagens,
                COALESCE(SUM((additional_data->>'Total de Vantagens')::numeric), 0) as total_vantagens
            FROM payroll_data
            WHERE period_id = :period_id
        """), {"period_id": period_id})
        
        row = vantagens_result.fetchone()
        print(f"   Registros com vantagens: {row[0]}")
        print(f"   Total de Vantagens: R$ {row[1]:,.2f}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


def list_periods():
    """Lista períodos disponíveis"""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        result = db.execute(text("""
            SELECT 
                pp.id,
                pp.period_name,
                pp.year,
                pp.month,
                COUNT(pd.id) as total_registros
            FROM payroll_periods pp
            LEFT JOIN payroll_data pd ON pd.period_id = pp.id
            GROUP BY pp.id, pp.period_name, pp.year, pp.month
            ORDER BY pp.year DESC, pp.month DESC
        """))
        
        print("\n📅 Períodos disponíveis:")
        print("=" * 80)
        for row in result:
            print(f"ID: {row[0]:3d} | {row[1]:30s} | {row[2]}/{row[3]:02d} | {row[4]:4d} registros")
        print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n📋 Uso:")
        print("  python reprocess_period.py list                           # Lista períodos")
        print("  python reprocess_period.py <period_id> <csv_path>         # Reprocessa período")
        print("\nExemplo:")
        print('  python reprocess_period.py 1 "C:\\...\\07-2025.CSV"')
        sys.exit(1)
    
    if sys.argv[1] == "list":
        list_periods()
    else:
        period_id = int(sys.argv[1])
        csv_path = sys.argv[2]
        reprocess_period(csv_path, period_id)
