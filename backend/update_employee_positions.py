"""
Script para atualizar a coluna position dos colaboradores com dados do CSV
"""
import os
import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import text

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from main_legacy import db_engine

def update_employee_positions():
    """Atualiza position dos colaboradores baseado nos CSVs"""
    
    csv_dir = Path(__file__).parent.parent / 'Analiticos' / 'Empreendimentos'
    
    print("="*80)
    print("ATUALIZANDO POSITIONS DOS COLABORADORES")
    print("="*80)
    
    # Coletar dados de todos os CSVs
    position_data = {}  # unique_id -> position
    
    for csv_file in csv_dir.glob('*.CSV'):
        try:
            df = pd.read_csv(csv_file, sep=';', encoding='latin-1', dtype=str)
            
            if 'Código Funcionário' in df.columns and 'Descrição Cargo' in df.columns:
                for _, row in df.iterrows():
                    code = str(row['Código Funcionário']).strip()
                    cargo = str(row.get('Descrição Cargo', '')).strip()
                    
                    if code and cargo and cargo != 'nan':
                        # Criar unique_id no formato 006000XXX
                        unique_id = f"006{code.zfill(6)}"
                        
                        # Guardar position (pode sobrescrever se CSV mais recente tiver info diferente)
                        if unique_id not in position_data or position_data[unique_id] == '':
                            position_data[unique_id] = cargo
                            
        except Exception as e:
            print(f"Erro ao processar {csv_file.name}: {e}")
    
    print(f"\nEncontrados {len(position_data)} cargos únicos nos CSVs")
    
    # Atualizar no banco
    with db_engine.connect() as conn:
        # Verificar quantos precisam atualização
        result = conn.execute(text("""
            SELECT COUNT(*) FROM employees 
            WHERE position IS NULL OR position = ''
        """))
        need_update = result.fetchone()[0]
        print(f"Colaboradores sem position no banco: {need_update}")
        
        # Atualizar cada um
        updated = 0
        for unique_id, position in position_data.items():
            try:
                result = conn.execute(
                    text("UPDATE employees SET position = :position WHERE unique_id = :unique_id AND (position IS NULL OR position = '')"),
                    {"position": position, "unique_id": unique_id}
                )
                if result.rowcount > 0:
                    updated += 1
            except Exception as e:
                print(f"Erro ao atualizar {unique_id}: {e}")
        
        conn.commit()
        print(f"\nAtualizados: {updated} colaboradores")
        
        # Verificar resultado
        print("\n" + "="*80)
        print("RESULTADO APÓS ATUALIZAÇÃO")
        print("="*80)
        
        result = conn.execute(text("""
            SELECT 
                COALESCE(e.department, e.position, 'Não especificado') as dept,
                COUNT(DISTINCT e.id) as total
            FROM employees e
            INNER JOIN payroll_data pd ON pd.employee_id = e.id
            GROUP BY COALESCE(e.department, e.position, 'Não especificado')
            ORDER BY total DESC
            LIMIT 15
        """))
        
        print("\nDepartamentos/Cargos com dados de folha:")
        for row in result:
            print(f"  {row[0]}: {row[1]} colaboradores")

if __name__ == "__main__":
    update_employee_positions()
