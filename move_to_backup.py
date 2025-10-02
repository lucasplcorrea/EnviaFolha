import os
import shutil
from pathlib import Path

def move_to_backup():
    """Move arquivos antigos para a pasta backup"""
    
    # Criar pasta backup se não existir
    backup_dir = Path("backup")
    backup_dir.mkdir(exist_ok=True)
    
    # Arquivos e pastas para mover
    items_to_move = [
        "app.py",
        "send_holerites_evolution.py", 
        "status_manager.py",
        "manus.py",
        "requirements_evolution.txt",
        "exemplo.env",
        "env_evolution.example",
        "Dockerfile",
        "docker-compose.yml",
        "enviacomunicados"  # pasta inteira
    ]
    
    for item in items_to_move:
        item_path = Path(item)
        if item_path.exists():
            destination = backup_dir / item
            
            if item_path.is_file():
                shutil.move(str(item_path), str(destination))
                print(f"Movido arquivo: {item} -> backup/{item}")
            elif item_path.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.move(str(item_path), str(destination))
                print(f"Movida pasta: {item} -> backup/{item}")
    
    print("\n✅ Arquivos antigos movidos para backup/")
    print("Execute: git add . && git commit -m 'Move old files to backup'")

if __name__ == "__main__":
    move_to_backup()
