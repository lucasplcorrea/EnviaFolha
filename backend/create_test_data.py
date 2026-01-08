#!/usr/bin/env python3
"""
Script para criar dados de teste nas tabelas de envios
"""
from datetime import datetime, timedelta
import random
from app.models.base import get_db
from app.models.payroll_send import PayrollSend
from app.models.communication_send import CommunicationSend
from app.models.communication_recipient import CommunicationRecipient
from app.models.employee import Employee
from app.models.user import User

def create_test_data():
    """Criar dados de teste para popular o dashboard"""
    db = next(get_db())
    
    try:
        # Buscar colaboradores e usuários existentes
        employees = db.query(Employee).limit(5).all()
        users = db.query(User).first()
        
        if not employees:
            print("❌ Nenhum colaborador encontrado no banco")
            return
        
        print(f"📊 Criando dados de teste para {len(employees)} colaboradores...")
        
        # Criar alguns envios de holerites (últimos 30 dias)
        print("\n📄 Criando envios de holerites...")
        payroll_months = ['2025-09', '2025-10']
        for month in payroll_months:
            for emp in employees:
                # 80% de sucesso, 20% de falha
                is_success = random.random() < 0.8
                days_ago = random.randint(1, 30)
                
                payroll = PayrollSend(
                    employee_id=emp.id,
                    month=month,
                    file_path=f"{emp.unique_id}_holerite_{month}.pdf",
                    status='sent' if is_success else 'failed',
                    error_message=None if is_success else 'Erro de teste',
                    sent_at=datetime.now() - timedelta(days=days_ago),
                    user_id=users.id if users else None
                )
                db.add(payroll)
                print(f"  ✅ Holerite {month} para {emp.name} - {'sucesso' if is_success else 'falha'}")
        
        # Criar alguns comunicados (últimos 15 dias)
        print("\n📨 Criando envios de comunicados...")
        comm_titles = [
            "Aviso: Reunião de equipe",
            "Comunicado: Férias coletivas",
            "Lembrete: Atualizar cadastro",
            "Informativo: Novos benefícios"
        ]
        
        for i, title in enumerate(comm_titles):
            days_ago = random.randint(1, 15)
            send_time = datetime.now() - timedelta(days=days_ago)
            
            # Criar o CommunicationSend
            comm_send = CommunicationSend(
                title=title,
                message=f"Mensagem de teste para {title}",
                file_path=None,
                total_recipients=random.randint(2, 3),
                successful_sends=0,  # Será atualizado depois
                failed_sends=0,
                status='completed',
                started_at=send_time,
                completed_at=send_time + timedelta(minutes=2),
                user_id=users.id if users else None
            )
            db.add(comm_send)
            db.flush()  # Para obter o ID
            
            # Criar recipients para 2-3 colaboradores
            num_recipients = random.randint(2, 3)
            success_count = 0
            failed_count = 0
            
            for emp in random.sample(employees, num_recipients):
                is_success = random.random() < 0.9  # 90% de sucesso
                
                recipient = CommunicationRecipient(
                    communication_send_id=comm_send.id,
                    employee_id=emp.id,
                    status='sent' if is_success else 'failed',
                    error_message=None if is_success else 'Erro de teste',
                    sent_at=send_time
                )
                db.add(recipient)
                
                if is_success:
                    success_count += 1
                else:
                    failed_count += 1
                    
                print(f"  ✅ {title} para {emp.name} - {'sucesso' if is_success else 'falha'}")
            
            # Atualizar contadores
            comm_send.total_recipients = num_recipients
            comm_send.successful_sends = success_count
            comm_send.failed_sends = failed_count
        
        db.commit()
        
        # Verificar resultados
        total_payrolls = db.query(PayrollSend).count()
        total_comms = db.query(CommunicationRecipient).count()
        
        print("\n" + "="*60)
        print("✅ Dados de teste criados com sucesso!")
        print("="*60)
        print(f"📊 Total de envios de holerites: {total_payrolls}")
        print(f"📨 Total de envios de comunicados: {total_comms}")
        print("\n🔄 Recarregue o Dashboard para ver os dados!")
        
    except Exception as e:
        print(f"❌ Erro ao criar dados de teste: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()
