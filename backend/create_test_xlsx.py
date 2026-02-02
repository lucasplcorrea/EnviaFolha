"""
Criar arquivo XLSX de teste com CPFs em diferentes formatos
"""
import openpyxl
from pathlib import Path

# Criar workbook
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Layout"

# Cabeçalhos
headers = ['CPF', 'Nome', 'Data de nascimento', 'Email', 'CNPJ', 'Convencao Coletiva', 'Grupo de entrega', 'Refeicao', 'Alimentacao', 'Mobilidade', 'Livre']
ws.append(headers)

# Dados de teste com diferentes formatos de CPF
# Usando CPFs de colaboradores que sabemos que existem no sistema
test_data = [
    ['116.329.082-39', 'TESTE FORMATO NORMAL', '2000-01-01', 'teste1@email.com', '07.847.003/0001-04', '', '', 520, 0, 0, 0],
    ['116-329.082-39', 'TESTE FORMATO HIFEN INICIO', '2000-01-01', 'teste2@email.com', '07.847.003/0001-04', '', '', 520, 100, 0, 0],
    ['11632908239', 'TESTE SEM FORMATACAO', '2000-01-01', 'teste3@email.com', '07.847.003/0001-04', '', '', 520, 0, 50, 0],
    ['116 329 082 39', 'TESTE COM ESPACOS', '2000-01-01', 'teste4@email.com', '07.847.003/0001-04', '', '', 520, 0, 0, 100],
]

for row in test_data:
    ws.append(row)

# Salvar arquivo
output_path = Path(__file__).parent.parent / "Analiticos" / "Ifood" / "teste_formatos_cpf.xlsx"
wb.save(output_path)

print("=" * 60)
print("✅ Arquivo de teste criado com sucesso!")
print(f"📁 Local: {output_path}")
print()
print("📊 Dados incluídos:")
print("   • 4 linhas com o mesmo CPF em formatos diferentes")
print("   • Formato padrão: 116.329.082-39")
print("   • Formato com hífen no início: 116-329.082-39")
print("   • Sem formatação: 11632908239")
print("   • Com espaços: 116 329 082 39")
print("=" * 60)
