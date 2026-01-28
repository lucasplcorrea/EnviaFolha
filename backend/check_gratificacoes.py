import csv

csv_path = r'C:\Users\LucasPedroLopesCorrê\Documents\GitHub\EnviaFolha\Analiticos\Empreendimentos\07-2025.CSV'

with open(csv_path, 'r', encoding='latin-1') as f:
    reader = csv.reader(f, delimiter=';')
    headers = next(reader)
    
    # Encontrar índices das colunas de gratificação
    gratif_indices = {}
    for i, h in enumerate(headers):
        if 'gratif' in h.lower():
            gratif_indices[h] = i
            print(f"Coluna {i}: {h}")
    
    print("\n" + "="*80)
    print("Verificando dados nas colunas de gratificação:")
    print("="*80 + "\n")
    
    # Verificar valores
    rows = list(reader)
    for col_name, col_idx in gratif_indices.items():
        total = 0
        count = 0
        for row in rows:
            if col_idx < len(row):
                val_str = row[col_idx].strip()
                if val_str and val_str != '0' and val_str != '0,00':
                    # Converter formato BR para float
                    val_str = val_str.replace('.', '').replace(',', '.')
                    try:
                        val = float(val_str)
                        if val > 0:
                            count += 1
                            total += val
                    except:
                        pass
        
        print(f"{col_name}:")
        print(f"  Registros: {count}")
        print(f"  Total: R$ {total:,.2f}")
        print()
