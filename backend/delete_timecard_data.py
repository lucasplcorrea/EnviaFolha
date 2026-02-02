"""
Script para deletar todos os dados de cartão ponto
Usado quando é necessário reprocessar com lógica de conversão corrigida
"""
from app.core.database import SessionLocal
from app.models.timecard import TimecardData, TimecardPeriod, TimecardProcessingLog


def delete_all_timecard_data():
    db = SessionLocal()
    try:
        # Contar registros antes
        data_count = db.query(TimecardData).count()
        period_count = db.query(TimecardPeriod).count()
        log_count = db.query(TimecardProcessingLog).count()
        
        print(f"📊 Registros encontrados:")
        print(f"   - TimecardData: {data_count}")
        print(f"   - TimecardPeriod: {period_count}")
        print(f"   - TimecardProcessingLog: {log_count}")
        
        if data_count == 0 and period_count == 0 and log_count == 0:
            print("✅ Não há dados para deletar")
            return
        
        confirm = input("\n⚠️  Deseja deletar todos esses dados? (sim/não): ")
        if confirm.lower() not in ['sim', 's', 'yes', 'y']:
            print("❌ Operação cancelada")
            return
        
        # Deletar na ordem correta (dados primeiro, depois períodos e logs)
        print("\n🗑️  Deletando dados...")
        db.query(TimecardData).delete()
        db.query(TimecardProcessingLog).delete()
        db.query(TimecardPeriod).delete()
        
        db.commit()
        
        print("✅ Dados deletados com sucesso!")
        print("   Agora você pode fazer um novo upload com a conversão corrigida")
        
    except Exception as e:
        print(f"❌ Erro ao deletar dados: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_timecard_data()
