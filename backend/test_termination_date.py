"""
Script para testar a gravação automática de termination_date
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from sqlalchemy import create_engine, text
from app.services.payroll_csv_processor import PayrollCSVProcessor
from sqlalchemy.orm import sessionmaker

def test_termination_date():
    """Testa se termination_date é gravado ao processar folha com demitidos"""
    
    # Conectar ao banco
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("\n" + "="*70)
        print("TESTE: Gravacao Automatica de termination_date")
        print("="*70)
        
        # 1. Verificar quantos employees têm termination_date ANTES
        print("\n1️⃣ Estado ANTES do reprocessamento:")
        result_before = db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(termination_date) as com_data,
                   COUNT(*) - COUNT(termination_date) as sem_data
            FROM employees
        """))
        stats_before = result_before.fetchone()
        print(f"   Total de employees: {stats_before[0]}")
        print(f"   Com termination_date: {stats_before[1]}")
        print(f"   Sem termination_date: {stats_before[2]}")
        
        # 2. Buscar employees com status "Demitido" nos períodos
        print("\n2️⃣ Verificando employees com status Demitido/Rescisão:")
        result_demitidos = db.execute(text("""
            SELECT DISTINCT 
                e.id,
                e.name,
                e.unique_id,
                e.termination_date,
                pd.additional_data->>'Status' as status,
                pp.year,
                pp.month
            FROM payroll_data pd
            INNER JOIN employees e ON e.id = pd.employee_id
            INNER JOIN payroll_periods pp ON pp.id = pd.period_id
            WHERE pd.additional_data->>'Status' LIKE '%Demitido%' 
               OR pd.additional_data->>'Status' LIKE '%Rescisão%'
            ORDER BY pp.year DESC, pp.month DESC, e.name
            LIMIT 10
        """))
        
        demitidos = result_demitidos.fetchall()
        print(f"   Encontrados {len(demitidos)} employees com status de desligamento")
        
        if demitidos:
            print("\n   📋 Primeiros 10:")
            for emp in demitidos:
                term_date = emp[3].strftime('%d/%m/%Y') if emp[3] else 'NÃO DEFINIDA'
                print(f"      • {emp[1]} ({emp[2]})")
                print(f"        Status: {emp[4]} | termination_date: {term_date}")
        
        # 3. Escolher um período para reprocessar (Maio 2025 - ID 42)
        print("\n3️⃣ Reprocessando período: Maio 2025")
        csv_path = r"C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\05-2025.CSV"
        
        import os
        if not os.path.exists(csv_path):
            print(f"   ❌ CSV não encontrado: {csv_path}")
            print("   ℹ️ Listando CSVs disponíveis:")
            csv_dir = r"C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos"
            if os.path.exists(csv_dir):
                csvs = [f for f in os.listdir(csv_dir) if f.endswith('.CSV')]
                for csv in sorted(csvs):
                    print(f"      • {csv}")
            return
        
        # 4. Deletar dados antigos do período
        print("   🗑️ Removendo dados antigos do período...")
        db.execute(text("DELETE FROM payroll_data WHERE period_id = 42"))
        db.commit()
        
        # 5. Reprocessar com a nova lógica
        print("   📊 Reprocessando CSV...")
        processor = PayrollCSVProcessor(db, user_id=None)  # Sem user_id para evitar foreign key error
        result = processor.process_csv_file(
            file_path=csv_path,
            division_code='0060',
            auto_create_employees=False
        )
        
        if result['success']:
            print(f"   ✅ Processado com sucesso!")
            print(f"      Stats: {result['stats']}")
        else:
            print(f"   ❌ Erro: {result.get('error')}")
        
        # 6. Verificar employees com termination_date DEPOIS
        print("\n4️⃣ Estado DEPOIS do reprocessamento:")
        result_after = db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(termination_date) as com_data,
                   COUNT(*) - COUNT(termination_date) as sem_data
            FROM employees
        """))
        stats_after = result_after.fetchone()
        print(f"   Total de employees: {stats_after[0]}")
        print(f"   Com termination_date: {stats_after[1]} ({stats_after[1] - stats_before[1]:+d})")
        print(f"   Sem termination_date: {stats_after[2]}")
        
        # 7. Mostrar employees que GANHARAM termination_date
        print("\n5️⃣ Employees com termination_date atualizado:")
        result_updated = db.execute(text("""
            SELECT 
                e.name,
                e.unique_id,
                e.termination_date,
                e.employment_status,
                pd.additional_data->>'Status' as payroll_status
            FROM employees e
            INNER JOIN payroll_data pd ON pd.employee_id = e.id
            WHERE e.termination_date IS NOT NULL
              AND pd.period_id = 42
            ORDER BY e.termination_date DESC, e.name
            LIMIT 20
        """))
        
        updated = result_updated.fetchall()
        if updated:
            print(f"   Encontrados {len(updated)} employees:")
            for emp in updated:
                print(f"      • {emp[0]} ({emp[1]})")
                print(f"        Data: {emp[2].strftime('%d/%m/%Y')} | Status: {emp[3]} | Folha: {emp[4]}")
        else:
            print("   ⚠️ Nenhum employee com termination_date encontrado")
        
        print("\n" + "="*70)
        print("✅ Teste concluído!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_termination_date()
