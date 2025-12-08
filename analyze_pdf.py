import PyPDF2
import re

pdf_path = 'tests/Recibos 112025 Infraestrutura.pdf'

with open(pdf_path, 'rb') as pdf_file:
    reader = PyPDF2.PdfReader(pdf_file)
    total_pages = len(reader.pages)
    print(f'Total de páginas no PDF: {total_pages}\n')
    
    for i in range(min(10, total_pages)):
        text = reader.pages[i].extract_text()
        print(f'\n{"="*60}')
        print(f'PÁGINA {i+1}')
        print("="*60)
        
        # Procurar por matrícula/ID
        lines = text.split('\n')
        matricula_found = None
        nome_found = None
        
        for idx, line in enumerate(lines[:30]):
            # Procurar padrões de matrícula
            if 'Matr' in line or 'matr' in line:
                print(f'  Linha {idx}: {line}')
                # Tentar extrair número da matrícula
                numeros = re.findall(r'\d+', line)
                if numeros:
                    matricula_found = numeros[0]
            
            # Procurar nome do colaborador
            if 'Nome' in line or 'NOME' in line:
                print(f'  Linha {idx}: {line}')
                if idx + 1 < len(lines):
                    nome_found = lines[idx + 1]
        
        if matricula_found:
            print(f'\n  ✓ MATRÍCULA IDENTIFICADA: {matricula_found}')
        if nome_found:
            print(f'  ✓ NOME: {nome_found[:50]}')
        
        print()
