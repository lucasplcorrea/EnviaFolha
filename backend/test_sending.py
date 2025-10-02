#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de envio simples baseado nos scripts de backup
Para testar funcionalidades básicas sem dependências complexas
"""

import json
import os
import time
import random
from datetime import datetime

class MockEvolutionAPI:
    """Mock da Evolution API para testes"""
    
    def __init__(self):
        print("🔧 Inicializando Mock Evolution API...")
        
    def check_connection(self):
        """Simula verificação de conexão"""
        print("📡 Verificando conexão...")
        time.sleep(1)
        return True
    
    def send_message(self, phone, message, file_path=None):
        """Simula envio de mensagem"""
        print(f"📱 Enviando para {phone}...")
        print(f"💬 Mensagem: {message[:50]}...")
        
        if file_path:
            print(f"📎 Arquivo: {file_path}")
        
        # Simular delay realista
        delay = random.uniform(2, 5)
        time.sleep(delay)
        
        # Simular sucesso (90% das vezes)
        success = random.random() > 0.1
        
        if success:
            print("✅ Enviado com sucesso!")
        else:
            print("❌ Falha no envio")
        
        return success

class SimpleEmployeeManager:
    """Gerenciador simples de colaboradores"""
    
    def __init__(self, data_file="employees.json"):
        self.data_file = data_file
        self.employees = self.load_employees()
    
    def load_employees(self):
        """Carrega colaboradores do arquivo JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("employees", [])
            except:
                pass
        
        # Dados de teste se não existir arquivo
        return [
            {
                "id": 1,
                "unique_id": "001",
                "full_name": "João Silva",
                "phone_number": "11999999999",
                "department": "TI",
                "is_active": True
            },
            {
                "id": 2,
                "unique_id": "002", 
                "full_name": "Maria Santos",
                "phone_number": "11888888888",
                "department": "RH",
                "is_active": True
            }
        ]
    
    def get_active_employees(self):
        """Retorna colaboradores ativos"""
        return [emp for emp in self.employees if emp.get("is_active", True)]

def test_communication_sending():
    """Testa envio de comunicados"""
    print("=" * 60)
    print("🚀 TESTE DE ENVIO DE COMUNICADOS")
    print("=" * 60)
    
    # Inicializar componentes
    employee_manager = SimpleEmployeeManager()
    evolution_api = MockEvolutionAPI()
    
    # Verificar conexão
    if not evolution_api.check_connection():
        print("❌ Falha na conexão com Evolution API")
        return
    
    # Obter colaboradores
    employees = employee_manager.get_active_employees()
    print(f"👥 Encontrados {len(employees)} colaboradores ativos")
    
    # Simular envio
    message = "📢 Comunicado importante: Reunião geral amanhã às 14h no auditório."
    
    success_count = 0
    failed_employees = []
    
    print("\n🔄 Iniciando envios...")
    print("-" * 40)
    
    for employee in employees:
        print(f"\n👤 Processando: {employee['full_name']}")
        
        success = evolution_api.send_message(
            phone=employee['phone_number'],
            message=message
        )
        
        if success:
            success_count += 1
        else:
            failed_employees.append(employee['full_name'])
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL")
    print("=" * 60)
    print(f"✅ Sucessos: {success_count}/{len(employees)}")
    print(f"❌ Falhas: {len(failed_employees)}")
    
    if failed_employees:
        print(f"👥 Falhas: {', '.join(failed_employees)}")
    
    print("🏁 Teste concluído!")

def test_payroll_sending():
    """Testa envio de holerites"""
    print("=" * 60)
    print("📄 TESTE DE ENVIO DE HOLERITES")
    print("=" * 60)
    
    # Inicializar componentes
    employee_manager = SimpleEmployeeManager()
    evolution_api = MockEvolutionAPI()
    
    # Verificar conexão
    if not evolution_api.check_connection():
        print("❌ Falha na conexão com Evolution API")
        return
    
    # Simular arquivos de holerites
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    
    employees = employee_manager.get_active_employees()
    print(f"👥 Encontrados {len(employees)} colaboradores ativos")
    
    success_count = 0
    failed_employees = []
    
    print("\n🔄 Iniciando envios de holerites...")
    print("-" * 40)
    
    for employee in employees:
        print(f"\n👤 Processando: {employee['full_name']}")
        
        # Simular arquivo de holerite
        file_path = f"uploads/holerite_{employee['unique_id']}.pdf"
        
        message = f"📄 Olá {employee['full_name']}, seu holerite está anexo. Senha: 1234"
        
        success = evolution_api.send_message(
            phone=employee['phone_number'],
            message=message,
            file_path=file_path
        )
        
        if success:
            success_count += 1
        else:
            failed_employees.append(employee['full_name'])
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL - HOLERITES")
    print("=" * 60)
    print(f"✅ Sucessos: {success_count}/{len(employees)}")
    print(f"❌ Falhas: {len(failed_employees)}")
    
    if failed_employees:
        print(f"👥 Falhas: {', '.join(failed_employees)}")
    
    print("🏁 Teste concluído!")

def main():
    """Função principal"""
    print("🎯 Sistema de Teste de Envios")
    print("Baseado nos scripts de backup em produção")
    print("=" * 60)
    
    while True:
        print("\nOpções:")
        print("1. Testar envio de comunicados")
        print("2. Testar envio de holerites")
        print("3. Sair")
        
        choice = input("\nEscolha uma opção (1-3): ").strip()
        
        if choice == "1":
            test_communication_sending()
        elif choice == "2":
            test_payroll_sending()
        elif choice == "3":
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    main()