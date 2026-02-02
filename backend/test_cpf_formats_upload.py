"""
Teste de upload com diferentes formatos de CPF
"""
import requests
import os

BASE_URL = "http://localhost:8002/api/v1"

xlsx_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "Analiticos", "Ifood", "teste_formatos_cpf.xlsx"
)

print("=" * 60)
print("🧪 TESTE DE UPLOAD COM DIFERENTES FORMATOS DE CPF")
print("=" * 60)
print(f"📁 Arquivo: {xlsx_path}")
print(f"📅 Período: Fevereiro/2026")
print(f"🏢 Empresa: 0060")
print()

if not os.path.exists(xlsx_path):
    print(f"❌ Arquivo não encontrado: {xlsx_path}")
    exit(1)

print(f"✅ Arquivo encontrado ({os.path.getsize(xlsx_path)} bytes)")
print()
print("📤 Fazendo upload...")

with open(xlsx_path, 'rb') as f:
    files = {'file': ('teste_formatos_cpf.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    data = {
        'year': 2026,
        'month': 2,
        'company': '0060'
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/benefits/upload-xlsx",
            files=files,
            data=data,
            timeout=60
        )
        
        print(f"🔍 Status Code: {response.status_code}")
        print()
        
        result = response.json()
        
        if result.get('success'):
            print("✅ TESTE PASSOU - UPLOAD BEM-SUCEDIDO!")
            print()
            print(f"📊 Resultados:")
            print(f"   • Total de linhas: {result.get('total_rows', 0)}")
            print(f"   • Processadas: {result.get('processed_rows', 0)}")
            print(f"   • Erros: {result.get('error_rows', 0)}")
            
            # Verificar se todas as 4 linhas foram processadas
            if result.get('processed_rows', 0) == 4:
                print()
                print("🎉 SUCESSO COMPLETO!")
                print("   Todos os 4 formatos de CPF foram reconhecidos!")
            else:
                print()
                print("⚠️  ATENÇÃO!")
                print(f"   Esperado: 4 linhas processadas")
                print(f"   Obtido: {result.get('processed_rows', 0)} linhas processadas")
            
            if result.get('warnings'):
                print()
                print(f"⚠️  Avisos:")
                for warn in result['warnings']:
                    print(f"   • {warn}")
        else:
            print("❌ TESTE FALHOU")
            print(f"   Erro: {result.get('error', 'Erro desconhecido')}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

print()
print("=" * 60)
