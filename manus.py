import PyPDF2
import re
import os
import sys

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

            # Regex para encontrar o número de cadastro
            # Busca por uma linha que começa com um número e é seguida por texto em maiúsculas
            cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
            cadastro_num = cadastro_match.group(1) if cadastro_match else 'UNKNOWN_CAD'

            # Regex para encontrar o número da empresa (campo 'Empresa')
            # Busca por 'CBO Empresa Local Departamento FL' e então captura o segundo número na linha seguinte
            empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
            empresa_num = empresa_field_match.group(3) if empresa_field_match else 'UNKNOWN_EMP'

            # Formatação do identificador único: XXXXYYYYY
            # XXXX = código da empresa (preenchido com zeros à esquerda)
            # YYYYY = código do cadastro (preenchido com zeros à esquerda)
            if empresa_num != 'UNKNOWN_EMP' and cadastro_num != 'UNKNOWN_CAD':
                empresa_formatted = str(empresa_num).zfill(4)
                cadastro_formatted = str(cadastro_num).zfill(5)
                file_identifier = f'{empresa_formatted}{cadastro_formatted}'
            else:
                file_identifier = f'UNKNOWN_{i+1}'

            # Regex para encontrar o CPF
            cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
            if cpf_match:
                employee_cpf_full = cpf_match.group(1).replace('.', '').replace('-', '')  # Remove pontos e traços
                employee_cpf = employee_cpf_full[:4]  # Apenas os 4 primeiros dígitos

            # Regex para encontrar o mês e ano de referência
            month_year_match = re.search(r"(\d{2}/\d{4})\s*Mensal", text)
            month_year = month_year_match.group(1) if month_year_match else "UNKNOWN_DATE"

            # Mapeamento de números de mês para nomes de mês em português
            month_names = {
                "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
                "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
                "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro"
            }

            # Formatar o mês e ano para o nome do arquivo
            formatted_month_year = ""
            if month_year != "UNKNOWN_DATE":
                month_num = month_year.split("/")[0]
                year = month_year.split("/")[1]
                formatted_month_year = f"{month_names.get(month_num, 'UNKNOWN')}_{year}"
            else:
                formatted_month_year = "UNKNOWN_DATE"

            output_pdf_path = os.path.join(output_dir, f'{file_identifier}_holerite_{formatted_month_year}.pdf')
            
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)

            if employee_cpf:
                try:
                    writer.encrypt(user_password=employee_cpf, owner_password=None)
                except Exception as e:
                    print(f"Erro ao proteger o PDF {file_identifier}: {e}")
                    unprotected_pdfs.append(f'{file_identifier}_error.pdf (Erro: {e})')
            else:
                unprotected_pdfs.append(f'{file_identifier}_unprotected.pdf (CPF não encontrado)')

            with open(output_pdf_path, 'wb') as outfile:
                writer.write(outfile)
            print(f'Holerite {file_identifier} salvo em {output_pdf_path} (protegido com senha: {bool(employee_cpf)})')

    if unprotected_pdfs:
        print("\n--- ATENÇÃO: PDFs NÃO PROTEGIDOS COM SENHA ---")
        for pdf in unprotected_pdfs:
            print(f"- {pdf}")
        print("---------------------------------------------")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Erro: caminho do PDF não fornecido.")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_directory = './holerites_formatados_final/'
    split_pdf_by_employee(input_pdf, output_directory)