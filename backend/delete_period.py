"""
Script para deletar períodos de folha de pagamento
Uso: python delete_period.py [period_id ou period_name]
"""
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from main_legacy import db_engine
from sqlalchemy import text

def list_periods():
    """Lista todos os períodos disponíveis"""
    print("\n" + "="*80)
    print("PERÍODOS CADASTRADOS")
    print("="*80)
    
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                pp.id,
                pp.period_name,
                pp.year,
                pp.month,
                COUNT(pd.id) as total_records,
                COUNT(DISTINCT pd.employee_id) as total_employees
            FROM payroll_periods pp
            LEFT JOIN payroll_data pd ON pd.period_id = pp.id
            GROUP BY pp.id, pp.period_name, pp.year, pp.month
            ORDER BY pp.year DESC, pp.month DESC
        """))
        
        periods = []
        for row in result:
            periods.append({
                "id": row[0],
                "period_name": row[1],
                "year": row[2],
                "month": row[3],
                "total_records": row[4],
                "total_employees": row[5]
            })
        
        if not periods:
            print("Nenhum período encontrado.")
            return []
        
        print(f"\n{'ID':<5} {'Nome do Período':<35} {'Ano':<6} {'Mês':<4} {'Registros':<12} {'Colaboradores'}")
        print("-" * 80)
        
        for p in periods:
            print(f"{p['id']:<5} {p['period_name']:<35} {p['year']:<6} {p['month']:<4} {p['total_records']:<12} {p['total_employees']}")
        
        print("\n")
        return periods

def delete_period(period_identifier):
    """
    Deleta um período pelo ID ou nome
    
    Args:
        period_identifier: ID numérico ou nome do período
    """
    with db_engine.connect() as conn:
        # Tentar encontrar o período
        if period_identifier.isdigit():
            # Buscar por ID
            result = conn.execute(
                text("SELECT id, period_name FROM payroll_periods WHERE id = :period_id"),
                {"period_id": int(period_identifier)}
            )
        else:
            # Buscar por nome (case-insensitive, parcial)
            result = conn.execute(
                text("SELECT id, period_name FROM payroll_periods WHERE LOWER(period_name) LIKE LOWER(:name)"),
                {"name": f"%{period_identifier}%"}
            )
        
        period = result.fetchone()
        
        if not period:
            print(f"❌ Período '{period_identifier}' não encontrado.")
            return False
        
        period_id = period[0]
        period_name = period[1]
        
        # Confirmar deleção
        print(f"\n⚠️  Você está prestes a deletar o período:")
        print(f"   ID: {period_id}")
        print(f"   Nome: {period_name}")
        
        # Contar registros
        count_result = conn.execute(
            text("SELECT COUNT(*) FROM payroll_data WHERE period_id = :period_id"),
            {"period_id": period_id}
        )
        total_records = count_result.fetchone()[0]
        
        print(f"   Registros: {total_records}")
        print("\n🚨 ATENÇÃO: Esta ação é IRREVERSÍVEL!")
        
        confirm = input("\nDigite 'CONFIRMAR' para prosseguir: ")
        
        if confirm != "CONFIRMAR":
            print("❌ Operação cancelada.")
            return False
        
        # Deletar
        print(f"\n🗑️  Deletando período {period_id}...")
        
        # Deletar dados de folha
        conn.execute(
            text("DELETE FROM payroll_data WHERE period_id = :period_id"),
            {"period_id": period_id}
        )
        
        # Deletar período
        conn.execute(
            text("DELETE FROM payroll_periods WHERE id = :period_id"),
            {"period_id": period_id}
        )
        
        conn.commit()
        
        print(f"✅ Período '{period_name}' deletado com sucesso!")
        print(f"   {total_records} registros removidos.")
        
        return True

def delete_multiple_periods(period_names):
    """Deleta múltiplos períodos de uma vez"""
    deleted = 0
    failed = 0
    
    print(f"\n🗑️  Deletando {len(period_names)} períodos...")
    
    for period_name in period_names:
        print(f"\n--- Processando: {period_name} ---")
        if delete_period(period_name):
            deleted += 1
        else:
            failed += 1
    
    print("\n" + "="*80)
    print(f"RESUMO: ✅ {deleted} deletados | ❌ {failed} falharam")
    print("="*80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📋 Uso:")
        print("  python delete_period.py [ID ou nome do período]")
        print("  python delete_period.py list  (para listar todos os períodos)")
        print("\nExemplos:")
        print("  python delete_period.py 15")
        print("  python delete_period.py 'Janeiro 2024'")
        print("  python delete_period.py list")
        print("\n")
        list_periods()
    elif sys.argv[1].lower() == "list":
        list_periods()
    else:
        # Se passar vários argumentos, considerar como múltiplos períodos
        if len(sys.argv) > 2:
            delete_multiple_periods(sys.argv[1:])
        else:
            list_periods()
            delete_period(sys.argv[1])
