"""
FASE 3: Script de Preenchimento de name_id para todos os funcionários existentes

Objetivo:
- Calcular e preencher o campo 'name_id' em todos os registros de Employee
- Gerar relatório XLSX com status de atualização
- Identificar registros com dados incompletos (faltam company_code, registration_number, name)
- Detectar colisões de name_id (múltiplos funcionários com mesmo name_id)

Usage:
    cd backend
    python -m scripts.backfill_name_id
"""

import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# Imports locais
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Base
from app.models.employee import Employee
from app.models.company import Company
from app.core.config import settings
from app.utils.parsers import normalize_name_for_payroll, generate_name_id


class NameIdBackfiller:
    """Gerencia preenchimento de name_id e geração de relatórios"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stats = {
            'total_employees': 0,
            'updated': 0,
            'already_filled': 0,
            'missing_company_code': 0,
            'missing_registration_number': 0,
            'missing_name': 0,
            'name_id_collisions': 0,  # Múltiplos employees com mesmo name_id
            'errors': 0,
        }
        self.errors = []
        self.collisions = {}  # {name_id: [list of employee IDs]}
        self.updates = []  # Lista detalhada de atualizações
        
    def run(self) -> dict:
        """Executa o backfill completo"""
        print("\n" + "="*80)
        print("FASE 3: BACKFILL DE name_id")
        print("="*80 + "\n")
        
        print("[1/4] Carregando funcionários...")
        employees = self.db.query(Employee).all()
        self.stats['total_employees'] = len(employees)
        print(f"✓ Carregados {len(employees)} funcionários\n")
        
        print("[2/4] Processando funcionários...")
        self._process_employees(employees)
        print(f"✓ Processados {len(employees)} funcionários\n")
        
        print("[3/4] Detectando colisões...")
        self._detect_collisions()
        print(f"✓ Análise de colisões concluída\n")
        
        print("[4/4] Gerando relatório XLSX...")
        output_file = self._generate_report()
        print(f"✓ Relatório gerado: {output_file}\n")
        
        self._print_summary()
        return self.stats
    
    def _process_employees(self, employees: list):
        """Processa cada funcionário e tenta preencher name_id"""
        for emp in employees:
            # Validar se já tem name_id preenchido
            if emp.name_id:
                self.stats['already_filled'] += 1
                continue
            
            # Validar dados obrigatórios
            if not emp.company_code:
                self.stats['missing_company_code'] += 1
                self.errors.append({
                    'id': emp.id,
                    'name': emp.name,
                    'reason': 'Falta company_code'
                })
                continue
            
            if not emp.registration_number:
                self.stats['missing_registration_number'] += 1
                self.errors.append({
                    'id': emp.id,
                    'name': emp.name,
                    'reason': 'Falta registration_number'
                })
                continue
            
            if not emp.name:
                self.stats['missing_name'] += 1
                self.errors.append({
                    'id': emp.id,
                    'name': 'UNKNOWN',
                    'reason': 'Falta nome'
                })
                continue
            
            # Gerar name_id
            try:
                new_name_id = generate_name_id(
                    emp.company_code,
                    emp.registration_number,
                    emp.name
                )
                
                if new_name_id:
                    emp.name_id = new_name_id
                    self.db.add(emp)
                    self.stats['updated'] += 1
                    
                    # Rastrear para detecção de colisões
                    if new_name_id not in self.collisions:
                        self.collisions[new_name_id] = []
                    self.collisions[new_name_id].append(emp.id)
                    
                    # Registrar atualização
                    self.updates.append({
                        'id': emp.id,
                        'name': emp.name,
                        'company_code': emp.company_code,
                        'registration_number': emp.registration_number,
                        'name_id': new_name_id,
                        'status': 'UPDATED'
                    })
                else:
                    self.stats['errors'] += 1
                    self.errors.append({
                        'id': emp.id,
                        'name': emp.name,
                        'reason': 'name_id nulo após geração'
                    })
                    
            except Exception as e:
                self.stats['errors'] += 1
                self.errors.append({
                    'id': emp.id,
                    'name': emp.name,
                    'reason': str(e)
                })
        
        # Confirmar todas as mudanças
        print(f"   - Atualizando {self.stats['updated']} funcionários no banco...")
        self.db.commit()
        print(f"   ✓ Commit concluído")
    
    def _detect_collisions(self):
        """Detecta colisões (múltiplos employees com mesmo name_id)"""
        for name_id, emp_ids in self.collisions.items():
            if len(emp_ids) > 1:
                self.stats['name_id_collisions'] += 1
                
                # Buscar detalhes dos employees envolvidos
                for emp_id in emp_ids:
                    emp = self.db.query(Employee).filter(Employee.id == emp_id).first()
                    if emp:
                        self.updates.append({
                            'id': emp.id,
                            'name': emp.name,
                            'company_code': emp.company_code,
                            'registration_number': emp.registration_number,
                            'name_id': emp.name_id,
                            'status': 'COLLISION'
                        })
    
    def _generate_report(self) -> str:
        """Gera relatório XLSX com múltiplas abas"""
        output_file = Path(__file__).parent.parent / 'backfill_name_id_report.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            # ABA 1: Resumo Executivo
            summary_data = {
                'Métrica': [
                    'Total de Funcionários',
                    'Atualizados (novos name_id)',
                    'Já Preenchidos',
                    'Sem company_code',
                    'Sem registration_number',
                    'Sem nome',
                    'Erros no Processo',
                    'Colisões Detectadas',
                ],
                'Quantidade': [
                    self.stats['total_employees'],
                    self.stats['updated'],
                    self.stats['already_filled'],
                    self.stats['missing_company_code'],
                    self.stats['missing_registration_number'],
                    self.stats['missing_name'],
                    self.stats['errors'],
                    self.stats['name_id_collisions'],
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Resumo', index=False)
        
            # ABA 2: Funcionários Atualizados
            if self.updates:
                df_updated = pd.DataFrame([u for u in self.updates if u['status'] == 'UPDATED'])
                if not df_updated.empty:
                    df_updated.to_excel(writer, sheet_name='Atualizados', index=False)
        
            # ABA 3: Colisões Detectadas
            collisions_data = []
            for name_id, emp_ids in self.collisions.items():
                if len(emp_ids) > 1:
                    for emp_id in emp_ids:
                        emp = self.db.query(Employee).filter(Employee.id == emp_id).first()
                        if emp:
                            collisions_data.append({
                                'name_id': name_id,
                                'employee_id': emp.id,
                                'name': emp.name,
                                'company_code': emp.company_code,
                                'registration_number': emp.registration_number,
                                'cpf': emp.cpf,
                                'employment_status': emp.employment_status,
                                'admission_date': emp.admission_date,
                            })
            
            if collisions_data:
                df_collisions = pd.DataFrame(collisions_data)
                df_collisions.to_excel(writer, sheet_name='Colisoes', index=False)
        
            # ABA 4: Erros e Registros Incompletos
            if self.errors:
                df_errors = pd.DataFrame(self.errors)
                df_errors.to_excel(writer, sheet_name='Erros', index=False)
        
        print(f"   Arquivo: {output_file}")
        return str(output_file)
    
    def _print_summary(self):
        """Imprime resumo no console"""
        print("\n" + "="*80)
        print("RESUMO DE PREENCHIMENTO")
        print("="*80)
        
        print(f"\nTotal de Funcionários: {self.stats['total_employees']}")
        print(f"  ✓ Atualizados (novos name_id): {self.stats['updated']}")
        print(f"  ✓ Já Preenchidos: {self.stats['already_filled']}")
        print(f"  ⚠ Sem company_code: {self.stats['missing_company_code']}")
        print(f"  ⚠ Sem registration_number: {self.stats['missing_registration_number']}")
        print(f"  ⚠ Sem nome: {self.stats['missing_name']}")
        print(f"  ✗ Erros no Processo: {self.stats['errors']}")
        print(f"  ⚠ Colisões (mesma chave): {self.stats['name_id_collisions']}")
        
        print(f"\nTaxa de Sucesso: {self._success_rate():.1f}%")
        
        if self.errors:
            print(f"\nRegistros com Problema ({len(self.errors)}):")
            for err in self.errors[:10]:  # Mostrar primeiros 10
                print(f"  - ID {err['id']}: {err['name']} - {err['reason']}")
            if len(self.errors) > 10:
                print(f"  ... e mais {len(self.errors) - 10} registros")
    
    def _success_rate(self) -> float:
        """Calcula taxa de sucesso (excluindo já preenchidos)"""
        processable = self.stats['total_employees'] - self.stats['already_filled']
        if processable == 0:
            return 100.0
        successful = self.stats['updated']
        return (successful / processable) * 100


def main():
    """Função principal"""
    # Conectar ao banco
    engine = create_engine(settings.DATABASE_URL, echo=False)
    
    with Session(engine) as session:
        backfiller = NameIdBackfiller(session)
        stats = backfiller.run()
    
    print("\n✓ Backfill concluído com sucesso!\n")


if __name__ == '__main__':
    main()
