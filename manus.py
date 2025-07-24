import PyPDF2
import re
import os

def split_pdf_by_employee(input_pdf_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_pdf_path, 'rb') as infile:
        reader = PyPDF2.PdfReader(infile)
        num_pages = len(reader.pages)

        for i in range(num_pages):
            page = reader.pages[i]
            text = page.extract_text()

            employee_name = f'holerite_pagina_{i+1}' # Fallback para caso o nome não seja encontrado

            # Regex para encontrar a linha que contém o nome do funcionário
            # Procura por 'Cadastro' seguido por 'Nome do Funcionário' e então o número de cadastro
            # e captura a linha inteira que contém o nome do funcionário e o CBO.
            match_line = re.search(r'Cadastro\s+Nome do Funcionário.*?\n\s*\d+\s+([^\n]+?)\s+\d+', text, re.DOTALL)
            
            if match_line:
                line_with_name_and_cbo = match_line.group(1).strip()
                
                # Agora, extrair apenas o nome da linha capturada
                # O nome é uma sequência de letras maiúsculas e espaços, antes do CBO (número de 6 dígitos)
                name_match = re.match(r'([A-ZÀ-Ú\s]+?)\s+\d{6}', line_with_name_and_cbo)
                if name_match:
                    employee_name = name_match.group(1).strip()
                else:
                    # Se não encontrou o padrão com CBO, tenta pegar tudo antes do primeiro número
                    name_match_fallback = re.match(r'([A-ZÀ-Ú\s]+?)\s+\d+', line_with_name_and_cbo)
                    if name_match_fallback:
                        employee_name = name_match_fallback.group(1).strip()
                    else:
                        employee_name = line_with_name_and_cbo # Usa a linha inteira como último recurso

                # Limpar o nome para usar como nome de arquivo
                employee_name = re.sub(r'[^a-zA-Z0-9_]', '', employee_name.replace(' ', '_'))
                if not employee_name: # Se o nome ficou vazio após a limpeza, usa o fallback
                    employee_name = f'holerite_pagina_{i+1}'

            output_pdf_path = os.path.join(output_dir, f'{employee_name}_holerite_junho_2025.pdf')
            
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)

            with open(output_pdf_path, 'wb') as outfile:
                writer.write(outfile)
            print(f'Holerite de {employee_name} salvo em {output_pdf_path}')

if __name__ == '__main__':
    input_pdf = './Recibos.pdf'
    output_directory = './holerites_separados_final'
    split_pdf_by_employee(input_pdf, output_directory)


