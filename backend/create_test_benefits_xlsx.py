"""
Criar arquivo XLSX de teste com diferentes formatos de CPF
"""
import openpyxl
from pathlib import Path

# Criar workbook
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Layout"

# Cabeçalhos (mesmos do arquivo original)
headers = ['CPF', 'Nome', 'Data de nascimento', 'Email', 'CNPJ', 'Convencao Coletiva', 
           'Grupo de entrega', 'Refeicao', 'Alimentacao', 'Mobilidade', 'Livre']
ws.append(headers)

# Dados de teste com diferentes formatos de CPF
# Usando CPFs reais do sistema com formatos variados
test_data = [
    # Formato padrão (pontos e traço)
    ['116.329.082-39', 'ABRAHAM JOSUE BARRETO CUELLO', '2005-07-12', '', '07.847.003/0001-04', '', '', 520, 0, 0, 0],
    
    # Formato com hífen no início (problema relatado)
    ['047-750-169-97', 'ADELSO BRAZ INNOCENCIO', '1982-10-07', '', '07.847.003/0001-04', '', '', 520, 0, 0, 0],
    
    # Formato sem pontuação
    ['00427172993', 'ADEMIR SCHIMIT GARVAO', '1977-06-18', '', '07.847.003/0001-04', '', '', 520, 300, 0, 0],
    
    # Formato com espaços
    ['719 444 199 34', 'ADENIR FERNANDES SIQUEIRA', '1969-03-13', '', '07.847.003/0001-04', '', '', 520, 0, 0, 0],
    
    # Formato misto (pontos mas sem traço)
    ['890.554.629.34', 'ADILSON GIESE', '1975-12-19', '', '07.847.003/0001-04', '', '', 494, 0, 0, 0],
    
    # CPF que não existe no sistema (para testar o aviso)
    ['999.999.999-99', 'FUNCIONARIO INEXISTENTE', '1990-01-01', '', '07.847.003/0001-04', '', '', 500, 0, 0, 0],
]

for row in test_data:
    ws.append(row)

# Salvar arquivo
output_path = Path(__file__).parent.parent / "Analiticos" / "Ifood" / "TESTE_CPF_FORMATOS.xlsx"
output_path.parent.mkdir(parents=True, exist_ok=True)
wb.save(output_path)

print(f"✅ Arquivo criado com sucesso: {output_path}")
print(f"📊 Total de linhas de dados: {len(test_data)}")
print("\n📝 Formatos de CPF testados:")
for i, row in enumerate(test_data, 1):
    print(f"   {i}. {row[0]:20s} - {row[1]}")
