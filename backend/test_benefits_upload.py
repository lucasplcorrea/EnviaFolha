"""
Script de teste para upload de XLSX de benefícios
"""
import requests
import os

# URL do servidor
BASE_URL = "http://localhost:8002/api/v1"

# Caminho do arquivo XLSX
xlsx_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "Analiticos", "Ifood", "Layout ifood Refeição 012026.xlsx"
)

print("=" * 60)
print("🧪 TESTE DE UPLOAD DE BENEFÍCIOS (XLSX)")
print("=" * 60)
print(f"📁 Arquivo: {xlsx_path}")
print(f"📅 Período: Janeiro/2026")
print(f"🏢 Empresa: 0060 (Empreendimentos)")
print()

# Verificar se arquivo existe
if not os.path.exists(xlsx_path):
    print(f"❌ Arquivo não encontrado: {xlsx_path}")
    exit(1)

print(f"✅ Arquivo encontrado ({os.path.getsize(xlsx_path)} bytes)")
print()

# Fazer upload
print("📤 Fazendo upload...")

with open(xlsx_path, 'rb') as f:
    files = {'file': ('beneficios.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    data = {
        'year': 2026,
        'month': 1,
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
            print("✅ UPLOAD CONCLUÍDO COM SUCESSO!")
            print()
            print(f"📊 Estatísticas:")
            print(f"   • Período: {result.get('period_name', 'N/A')}")
            print(f"   • Total de linhas: {result.get('total_rows', 0)}")
            print(f"   • Linhas processadas: {result.get('processed_rows', 0)}")
            print(f"   • Linhas com erro: {result.get('error_rows', 0)}")
            print(f"   • Tempo de processamento: {result.get('processing_time', 0):.2f}s")
            
            if result.get('warnings'):
                print()
                print(f"⚠️  Avisos ({len(result['warnings'])}):")
                for warn in result['warnings'][:5]:
                    print(f"   • {warn}")
                if len(result['warnings']) > 5:
                    print(f"   ... e mais {len(result['warnings']) - 5} avisos")
            
            if result.get('errors'):
                print()
                print(f"❌ Erros ({len(result['errors'])}):")
                for err in result['errors'][:5]:
                    print(f"   • {err}")
                if len(result['errors']) > 5:
                    print(f"   ... e mais {len(result['errors']) - 5} erros")
        else:
            print("❌ ERRO NO PROCESSAMENTO")
            print(f"   {result.get('error', 'Erro desconhecido')}")
            
            if result.get('errors'):
                print()
                print("Detalhes dos erros:")
                for err in result['errors'][:10]:
                    print(f"   • {err}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

print()
print("=" * 60)
print("🏁 Teste finalizado")
print("=" * 60)
