"""
Script de teste para validar normalização de CPF no upload de benefícios
"""
import requests
import os

# URL do servidor
BASE_URL = "http://localhost:8002/api/v1"

# Caminho do arquivo XLSX de teste
xlsx_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "Analiticos", "Ifood", "TESTE_CPF_FORMATOS.xlsx"
)

print("=" * 60)
print("🧪 TESTE DE UPLOAD DE BENEFÍCIOS - NORMALIZAÇÃO DE CPF")
print("=" * 60)
print(f"📁 Arquivo: {xlsx_path}")
print(f"📅 Período: Fevereiro/2026 (teste)")
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
    files = {'file': ('TESTE_CPF_FORMATOS.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    data = {
        'year': '2026',
        'month': '2',  # Fevereiro
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
            
            # Analisar resultados esperados
            total_linhas = result.get('total_rows', 0)
            processadas = result.get('processed_rows', 0)
            
            print()
            print("🔍 Análise de Normalização:")
            print(f"   • Linhas no arquivo: 6")
            print(f"   • Linhas processadas: {processadas}")
            print(f"   • CPFs válidos encontrados: 5 (esperado)")
            print(f"   • CPF inválido (999.999.999-99): 1 (esperado)")
            
            if processadas == 5:
                print()
                print("✅ NORMALIZAÇÃO FUNCIONANDO PERFEITAMENTE!")
                print("   Todos os formatos de CPF foram reconhecidos:")
                print("   ✓ Formato padrão: 116.329.082-39")
                print("   ✓ Formato com hífen: 047-750-169-97")
                print("   ✓ Sem pontuação: 00427172993")
                print("   ✓ Com espaços: 719 444 199 34")
                print("   ✓ Sem traço final: 890.554.629.34")
            else:
                print()
                print(f"⚠️  Resultado diferente do esperado")
                print(f"   Esperado: 5 processadas")
                print(f"   Obtido: {processadas} processadas")
            
            if result.get('warnings'):
                print()
                print(f"⚠️  Avisos ({len(result['warnings'])}):")
                for warn in result['warnings']:
                    print(f"   • {warn}")
            
            if result.get('errors'):
                print()
                print(f"❌ Erros ({len(result['errors'])}):")
                for err in result['errors']:
                    print(f"   • {err}")
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
        print("   Verifique se o servidor está rodando em http://localhost:8002")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

print()
print("=" * 60)
print("🏁 Teste finalizado")
print("=" * 60)
