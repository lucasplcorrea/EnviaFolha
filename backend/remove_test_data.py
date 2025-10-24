#!/usr/bin/env python3
"""
Script para remover dados de teste das tabelas de envios
"""
from app.models.base import get_db
from app.models.payroll_send import PayrollSend
from app.models.communication_send import CommunicationSend
from app.models.communication_recipient import CommunicationRecipient

def remove_test_data():
    """Remover todos os dados de teste criados"""
    db = next(get_db())
    
    try:
        print("🗑️  Removendo dados de teste...\n")
        
        # Contar antes de remover
        payroll_count_before = db.query(PayrollSend).count()
        comm_send_count_before = db.query(CommunicationSend).count()
        comm_recipient_count_before = db.query(CommunicationRecipient).count()
        
        print(f"📊 Dados atuais no banco:")
        print(f"  • PayrollSends: {payroll_count_before}")
        print(f"  • CommunicationSends: {comm_send_count_before}")
        print(f"  • CommunicationRecipients: {comm_recipient_count_before}")
        print()
        
        # Remover todos os dados
        # Recipients primeiro (por causa da chave estrangeira)
        recipients_deleted = db.query(CommunicationRecipient).delete()
        print(f"✅ Removidos {recipients_deleted} CommunicationRecipients")
        
        comm_sends_deleted = db.query(CommunicationSend).delete()
        print(f"✅ Removidos {comm_sends_deleted} CommunicationSends")
        
        payrolls_deleted = db.query(PayrollSend).delete()
        print(f"✅ Removidos {payrolls_deleted} PayrollSends")
        
        db.commit()
        
        # Verificar depois
        payroll_count_after = db.query(PayrollSend).count()
        comm_send_count_after = db.query(CommunicationSend).count()
        comm_recipient_count_after = db.query(CommunicationRecipient).count()
        
        print("\n" + "="*60)
        print("✅ Dados de teste removidos com sucesso!")
        print("="*60)
        print(f"📊 Dados restantes no banco:")
        print(f"  • PayrollSends: {payroll_count_after}")
        print(f"  • CommunicationSends: {comm_send_count_after}")
        print(f"  • CommunicationRecipients: {comm_recipient_count_after}")
        print("\n🔄 Recarregue o Dashboard e Reports para ver as mudanças!")
        print("📝 A partir de agora, apenas envios REAIS serão registrados.")
        
    except Exception as e:
        print(f"❌ Erro ao remover dados de teste: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    # Confirmação antes de deletar
    print("⚠️  ATENÇÃO: Este script irá remover TODOS os dados de envios do banco!")
    print("   Isso inclui os dados de teste e qualquer envio real já registrado.")
    print()
    
    resposta = input("Deseja continuar? (sim/não): ").strip().lower()
    
    if resposta in ['sim', 's', 'yes', 'y']:
        remove_test_data()
    else:
        print("❌ Operação cancelada pelo usuário.")
        sys.exit(0)
