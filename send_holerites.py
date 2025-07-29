import pandas as pd
import os
import logging

# Configuração de logging para um output mais limpo
logging.basicConfig(level=logging.INFO, format="%(message)s")

def send_holerites_to_api(excel_path, pdf_dir, api_url, month_year_str):
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        logging.error(f"Erro: Planilha de colaboradores não encontrada em {excel_path}")
        return

    logging.info(f"\n--- INICIANDO TESTE DE MESA DE ASSOCIAÇÃO DE HOLERITES ---")
    logging.info(f"Verificando {len(df)} colaboradores na planilha.\n")

    found_associations = 0
    for index, row in df.iterrows():
        unique_id = str(row["ID_Unico"]).zfill(9)
        employee_name = row["Nome_Colaborador"]
        phone_number = str(row["Telefone"])

        pdf_filename = f"{unique_id}_holerite_{month_year_str}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        if os.path.exists(pdf_path):
            found_associations += 1
            logging.info(f"[ENCONTRADO] Holerite: {pdf_filename} -> Colaborador: {employee_name} -> Telefone: {phone_number}")
        else:
            logging.warning(f"[NÃO ENCONTRADO] Holerite: {pdf_filename} para {employee_name}. Arquivo não existe.")

    logging.info(f"\n--- TESTE DE MESA CONCLUÍDO ---")
    logging.info(f"Total de holerites encontrados e associados: {found_associations} de {len(df)}")

if __name__ == "__main__":
    excel_file = "./Colaboradores.xlsx"
    holerites_directory = "./holerites_formatados_final/"
    target_api_url = "https://sua-api-aqui.com/upload-holerite" # URL da API (apenas para referência no log)
    current_month_year = "junho_2025" # Mês e ano de referência dos holerites

    send_holerites_to_api(excel_file, holerites_directory, target_api_url, current_month_year)
