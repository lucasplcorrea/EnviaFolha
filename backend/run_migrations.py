#!/usr/bin/env python3
"""
Executa todas as migrations pendentes na ordem correta
"""
import os
import sys
import importlib.util
from pathlib import Path

def run_all_migrations():
    """Executa todas as migrations na pasta migrations/"""
    
    migrations_dir = Path(__file__).parent / 'migrations'
    
    if not migrations_dir.exists():
        print("ℹ️  Pasta migrations não encontrada")
        return
    
    # Listar todos os arquivos Python de migration
    migration_files = sorted([
        f for f in migrations_dir.glob('*.py')
        if f.name != '__init__.py' and not f.name.startswith('_')
    ])
    
    if not migration_files:
        print("ℹ️  Nenhuma migration encontrada")
        return
    
    print("🔄 Executando migrations...")
    print()
    
    for migration_file in migration_files:
        try:
            # Importar o módulo dinamicamente
            spec = importlib.util.spec_from_file_location(
                migration_file.stem, 
                migration_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Executar a função run_migration()
            if hasattr(module, 'run_migration'):
                module.run_migration()
            
        except Exception as e:
            print(f"⚠️  Erro ao executar {migration_file.name}: {e}")
            # Continuar com as outras migrations
            continue
    
    print()
    print("✅ Migrations concluídas")

if __name__ == "__main__":
    run_all_migrations()
