import PyPDF2
import re
import os

def split_pdf_by_employee(input_pdf_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    unprotected_pdfs = []

    with open(input_pdf_path, 'rb') as infile:
        reader = PyPDF2.PdfReader(infile)
        num_pages = len(reader.pages)

        for i in range(num_pages):
            page = reader.pages[i]
            text = page.extract_text()

            file_identifier = f'holerite_pagina_{i+1}'  # Fallback para caso o identificador não seja encontrado
            employee_cpf = ''  # Inicializa o CPF

            # Regex para encontrar o número da empresa (ex: 0059-ABECKER INFRAESTRUTURA LTDA)
            empresa_match = re.search(r'^(\d{4})-ABECKER INFRAESTRUTURA LTDA', text, re.MULTILINE)
            empresa_num = empresa_match.group(1) if empresa_match else 'UNKNOWN_EMP'

            # Regex para encontrar o número de cadastro
            cadastro_match = re.search(r'\n\s*(\d+)\s+[A-ZÀ-Ú\s]+?\s+\d{6}', text)
            cadastro_num = cadastro_match.group(1) if cadastro_match else 'UNKNOWN_CAD'

            # Formar o identificador único
            file_identifier = f'{empresa_num}_{cadastro_num}'

            # Regex para encontrar o CPF
            cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
            if cpf_match:
                employee_cpf = cpf_match.group(1).replace('.', '').replace('-', '')  # Remove pontos e traços

            output_pdf_path = os.path.join(output_dir, f'{file_identifier}_holerite_junho_2025.pdf')
            
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)

            if employee_cpf:
                try:
                    writer.encrypt(user_password=employee_cpf, owner_password=None)
                except Exception as e:
                    print(f"Erro ao proteger o PDF {file_identifier}: {e}")
                    unprotected_pdfs.append(f'{file_identifier}_holerite_junho_2025.pdf (Erro: {e})')
            else:
                unprotected_pdfs.append(f'{file_identifier}_holerite_junho_2025.pdf (CPF não encontrado)')

            with open(output_pdf_path, 'wb') as outfile:
                writer.write(outfile)
            print(f'Holerite {file_identifier} salvo em {output_pdf_path} (protegido com senha: {bool(employee_cpf)})')

    if unprotected_pdfs:
        print("\n--- ATENÇÃO: PDFs NÃO PROTEGIDOS COM SENHA ---")
        for pdf in unprotected_pdfs:
            print(f"- {pdf}")
        print("---------------------------------------------")

if __name__ == '__main__':
    input_pdf = 'Recibos.pdf'
    output_directory = './holerites_identificador_unico/'
    split_pdf_by_employee(input_pdf, output_directory)