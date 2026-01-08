"""
Script para corrigir unique_ids que perderam zeros à esquerda
"""
import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from app.core.config import Settings

def fix_unique_ids():
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    
    print("🔧 Analisando unique_ids que podem ter perdido zeros à esquerda...\n")
    
    try:
        with engine.connect() as conn:
            # Buscar todos os employees
            result = conn.execute(text("""
                SELECT id, unique_id, name 
                FROM employees 
                ORDER BY id
            """))
            
            employees = result.fetchall()
            
            print(f"📊 Total de colaboradores: {len(employees)}\n")
            print(f"{'ID':<5} {'Unique ID Atual':<20} {'Nome':<40}")
            print("=" * 70)
            
            needs_fix = []
            for emp in employees:
                emp_id, unique_id, name = emp
                
                # Verificar se unique_id tem menos de 9 dígitos (padrão esperado)
                if unique_id.isdigit() and len(unique_id) < 9:
                    needs_fix.append((emp_id, unique_id, name))
                    print(f"{emp_id:<5} {unique_id:<20} {name:<40} ⚠️ PRECISA AJUSTE")
                else:
                    print(f"{emp_id:<5} {unique_id:<20} {name:<40}")
            
            if needs_fix:
                print(f"\n⚠️ Encontrados {len(needs_fix)} unique_ids que podem precisar de zeros à esquerda")
                print("\nPara corrigir, você pode:")
                print("1. Editar manualmente pela interface")
                print("2. Reimportar o Excel com a coluna unique_id formatada como TEXTO no Excel")
                print("3. Executar UPDATE manual no banco (requer conhecimento do formato correto)")
                
                print("\n💡 DICA: No Excel, antes de salvar:")
                print("   - Selecione a coluna unique_id")
                print("   - Clique com botão direito → Formatar Células")
                print("   - Escolha 'Texto' como categoria")
                print("   - Digite os valores novamente ou use uma fórmula: =TEXT(A1,\"000000000\")")
            else:
                print("\n✅ Todos os unique_ids parecem estar corretos!")
                
    except Exception as e:
        print(f"❌ Erro ao verificar: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_unique_ids()
