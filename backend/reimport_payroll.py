"""
Script para reimportar CSVs com o novo processador simplificado
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.payroll_csv_processor import PayrollCSVProcessor
from app.models.employee import Employee
from app.models.payroll_period import PayrollPeriod

def main():
    print("=" * 80)
    print("🔄 REIMPORTANDO CSVs COM NOVO PROCESSADOR")
    print("=" * 80)
    
    db = SessionLocal()
    processor = PayrollCSVProcessor()
    
    try:
        # Arquivos para importar
        csv_files = [
            ("uploads/IntegralDecimoTerceiro-12-2024.CSV", "13º Integral - Dez/2024"),
            ("uploads/12-2024.CSV", "Dezembro 2024"),
        ]
        
        for csv_path, expected_period in csv_files:
            full_path = Path(csv_path)
            
            if not full_path.exists():
                print(f"\n❌ Arquivo não encontrado: {csv_path}")
                print(f"   Por favor, coloque o arquivo em: {full_path.absolute()}")
                continue
            
            print(f"\n{'=' * 80}")
            print(f"📄 Processando: {csv_path}")
            print(f"   Período esperado: {expected_period}")
            print(f"{'=' * 80}\n")
            
            # Processar o CSV
            result = processor.process_csv(str(full_path), db)
            
            if result["success"]:
                print(f"\n✅ Importação concluída com sucesso!")
                print(f"   • Período: {result['period_name']}")
                print(f"   • Funcionários processados: {result['processed']}")
                print(f"   • Erros: {result['errors']}")
                
                # Buscar estatísticas do período
                period = db.query(PayrollPeriod).filter(
                    PayrollPeriod.period_name == result['period_name']
                ).first()
                
                if period:
                    from sqlalchemy import text
                    stats = db.execute(text("""
                        SELECT 
                            COUNT(*) as total,
                            COALESCE(SUM((additional_data->>'Total de Proventos')::numeric), 0) as proventos,
                            COALESCE(SUM((additional_data->>'Total de Descontos')::numeric), 0) as descontos,
                            COALESCE(SUM((additional_data->>'Líquido de Cálculo')::numeric), 0) as liquido
                        FROM payroll_data
                        WHERE period_id = :period_id
                    """), {"period_id": period.id}).fetchone()
                    
                    if stats:
                        print(f"\n📊 Estatísticas do período:")
                        print(f"   • Total de registros: {stats[0]}")
                        print(f"   • Total de Proventos: R$ {stats[1]:,.2f}")
                        print(f"   • Total de Descontos: R$ {stats[2]:,.2f}")
                        print(f"   • Total Líquido: R$ {stats[3]:,.2f}")
            else:
                print(f"\n❌ Erro na importação: {result.get('error', 'Erro desconhecido')}")
        
        print(f"\n{'=' * 80}")
        print("✅ Processo de reimportação concluído!")
        print("=" * 80)
        
        # Listar todos os períodos
        print("\n📋 Períodos disponíveis no banco:")
        periods = db.query(PayrollPeriod).order_by(PayrollPeriod.created_at.desc()).all()
        for p in periods:
            print(f"   • ID {p.id}: {p.period_name} ({p.year}/{p.month})")
        
    except Exception as e:
        print(f"\n❌ Erro durante o processo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
