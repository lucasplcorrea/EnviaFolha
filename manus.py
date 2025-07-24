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
            employee_cpf = '' # Inicializa o CPF

            # Regex para encontrar o nome do funcionário
            name_match = re.search(r'\n\s*\d+\s+([A-ZÀ-Ú\s]+?)\s+\d{6}', text)
            if name_match:
                employee_name = name_match.group(1).strip()
                employee_name = re.sub(r'[^a-zA-Z0-9_]', '', employee_name.replace(' ', '_'))
                if not employee_name:
                    employee_name = f'holerite_pagina_{i+1}'

            # Regex para encontrar o CPF
            cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
            if cpf_match:
                employee_cpf = cpf_match.group(1).replace('.', '').replace('-', '') # Remove pontos e traços

            output_pdf_path = os.path.join(output_dir, f'{employee_name}_holerite_junho_2025.pdf')
            
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)

            if employee_cpf: # Se o CPF foi encontrado, adiciona a senha
                writer.encrypt(user_pwd=employee_cpf, owner_pwd=None)

            with open(output_pdf_path, 'wb') as outfile:
                writer.write(outfile)
            print(f'Holerite de {employee_name} salvo em {output_pdf_path} (protegido com senha: {bool(employee_cpf)})')

if __name__ == '__main__':
    input_pdf = './Recibos.pdf'
    output_directory = './holerites_protegidos/'
    split_pdf_by_employee(input_pdf, output_directory)