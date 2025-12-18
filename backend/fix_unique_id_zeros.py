"""
Script para corrigir unique_id de colaboradores que perderam zeros à esquerda.

Lógica:
- Se unique_id começa com '59' ou '60' → adiciona '00' à esquerda
- Exemplo: '5900123' → '005900123'
- Exemplo: '6012345' → '006012345'

Uso:
    python fix_unique_id_zeros.py

"""

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos do app
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.employee import Employee

def fix_unique_ids_with_missing_zeros():
    """
    Corrige unique_ids que perderam zeros à esquerda durante importação Excel.
    """
    print("=" * 80)
    print("CORREÇÃO DE UNIQUE_IDS - Adicionando zeros à esquerda")
    print("=" * 80)
    print()
    
    # Configurar conexão com banco de dados
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Buscar colaboradores cujo unique_id começa com 59 ou 60
        print("🔍 Buscando colaboradores com unique_id começando com 59 ou 60...")
        
        employees_to_fix = db.query(Employee).filter(
            (Employee.unique_id.like('59%')) | (Employee.unique_id.like('60%'))
        ).all()
        
        if not employees_to_fix:
            print("✅ Nenhum colaborador encontrado para correção.")
            print()
            return
        
        print(f"📋 Encontrados {len(employees_to_fix)} colaboradores para análise:")
        print()
        
        # Analisar e preparar correções
        corrections = []
        for employee in employees_to_fix:
            old_id = employee.unique_id
            
            # Verificar se já tem o formato correto (9 caracteres começando com 00)
            if len(old_id) == 9 and old_id.startswith('00'):
                print(f"   ⏭️  {employee.full_name:<30} | ID: {old_id} (já correto)")
                continue
            
            # Se tem 7 caracteres e começa com 59/60, adiciona 00 à esquerda
            if len(old_id) == 7 and (old_id.startswith('59') or old_id.startswith('60')):
                new_id = f"00{old_id}"
                corrections.append({
                    'employee': employee,
                    'old_id': old_id,
                    'new_id': new_id
                })
                print(f"   🔧 {employee.full_name:<30} | {old_id} → {new_id}")
            else:
                print(f"   ⚠️  {employee.full_name:<30} | ID: {old_id} (formato inesperado)")
        
        print()
        print("=" * 80)
        
        if not corrections:
            print("✅ Nenhuma correção necessária. Todos os IDs já estão corretos.")
            print()
            return
        
        # Confirmar correções
        print(f"📊 RESUMO: {len(corrections)} colaboradores serão corrigidos")
        print()
        print("⚠️  Esta operação irá:")
        print(f"   • Atualizar {len(corrections)} registros na tabela 'employees'")
        print("   • Adicionar '00' à esquerda dos unique_ids")
        print()
        
        response = input("Deseja continuar com a correção? (sim/não): ").strip().lower()
        
        if response not in ['sim', 's', 'yes', 'y']:
            print("❌ Operação cancelada pelo usuário.")
            print()
            return
        
        print()
        print("🔄 Aplicando correções...")
        print()
        
        # Aplicar correções
        updated_count = 0
        for correction in corrections:
            try:
                employee = correction['employee']
                old_id = correction['old_id']
                new_id = correction['new_id']
                
                # Verificar se o novo ID já existe
                existing = db.query(Employee).filter(
                    Employee.unique_id == new_id,
                    Employee.id != employee.id
                ).first()
                
                if existing:
                    print(f"   ⚠️  CONFLITO: {employee.full_name} - {new_id} já existe (pertence a {existing.full_name})")
                    continue
                
                # Atualizar unique_id
                employee.unique_id = new_id
                updated_count += 1
                print(f"   ✅ {employee.full_name:<30} | {old_id} → {new_id}")
                
            except Exception as e:
                print(f"   ❌ ERRO ao corrigir {correction['old_id']}: {str(e)}")
        
        # Commit das alterações
        if updated_count > 0:
            db.commit()
            print()
            print("=" * 80)
            print(f"✅ SUCESSO: {updated_count} colaboradores corrigidos!")
            print("=" * 80)
        else:
            print()
            print("⚠️  Nenhuma correção foi aplicada devido a conflitos.")
        
        print()
        
    except Exception as e:
        print(f"❌ ERRO durante a execução: {str(e)}")
        db.rollback()
        raise
    
    finally:
        db.close()


def preview_corrections():
    """
    Modo de preview - apenas mostra o que seria corrigido sem fazer alterações.
    """
    print("=" * 80)
    print("PREVIEW - Correções que seriam aplicadas (SEM MODIFICAR DADOS)")
    print("=" * 80)
    print()
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        employees_to_fix = db.query(Employee).filter(
            (Employee.unique_id.like('59%')) | (Employee.unique_id.like('60%'))
        ).all()
        
        if not employees_to_fix:
            print("✅ Nenhum colaborador encontrado para correção.")
            print()
            return
        
        print(f"📋 {len(employees_to_fix)} colaboradores encontrados:")
        print()
        
        corrections_needed = 0
        for employee in employees_to_fix:
            old_id = employee.unique_id
            
            if len(old_id) == 9 and old_id.startswith('00'):
                print(f"   ⏭️  {employee.full_name:<30} | ID: {old_id} (já correto)")
            elif len(old_id) == 7 and (old_id.startswith('59') or old_id.startswith('60')):
                new_id = f"00{old_id}"
                corrections_needed += 1
                print(f"   🔧 {employee.full_name:<30} | {old_id} → {new_id}")
            else:
                print(f"   ⚠️  {employee.full_name:<30} | ID: {old_id} (formato inesperado)")
        
        print()
        print("=" * 80)
        print(f"📊 {corrections_needed} correções seriam aplicadas")
        print("=" * 80)
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    print()
    
    # Verificar se deve rodar em modo preview
    if len(sys.argv) > 1 and sys.argv[1] == '--preview':
        preview_corrections()
    else:
        fix_unique_ids_with_missing_zeros()
