#!/usr/bin/env python3
"""
Script para testar a correção do parsing de PDFs UNKNOWN
"""
import os
import re
from PyPDF2 import PdfReader

def test_improved_regex(pdf_path):
    """Testa o regex melhorado"""
    print(f"\n{'='*80}")
    print(f"Testando: {os.path.basename(pdf_path)}")
    print(f"{'='*80}\n")
    
    try:
        reader = PdfReader(pdf_path)
        page = reader.pages[0]
        text = page.extract_text()
        
        # REGEX ORIGINAL (que falha)
        print("🔴 REGEX ORIGINAL:")
        empresa_field_match_old = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
        if empresa_field_match_old:
            print(f"   Empresa: {empresa_field_match_old.group(3)}")
        else:
            print(f"   ❌ FALHOU - Não encontrou")
        
        # REGEX MELHORADO (novo)
        print("\n🟢 REGEX MELHORADO:")
        empresa_num = 'UNKNOWN_EMP'
        cadastro_num = 'UNKNOWN_CAD'
        
        # Encontrar cadastro
        cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
        if cadastro_match:
            cadastro_num = cadastro_match.group(1)
            print(f"   Cadastro: {cadastro_num}")
        
        # Tentar padrão com cabeçalho
        header_match = re.search(
            r'Cadastro\s+Nome\s+do\s+Funcionário\s+CBO\s+Empresa\s+Local\s+Departamento\s+FL\s*\n\s*'
            r'(\d+)\s+([A-ZÀ-Ú\s\d]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
            text
        )
        
        if header_match:
            empresa_num = header_match.group(4)
            print(f"   Empresa (via header_match): {empresa_num}")
            print(f"   Match groups: cadastro={header_match.group(1)}, cbo={header_match.group(3)}, empresa={header_match.group(4)}")
        else:
            print("   ⚠️  header_match falhou, tentando fallback...")
            # Fallback genérico
            generic_match = re.search(r'^\s*(\d+)\s+[\w\sÀ-Ú]+\s+(\d{4,6})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text, re.MULTILINE)
            if generic_match:
                empresa_num = generic_match.group(3)
                print(f"   Empresa (via generic_match): {empresa_num}")
                print(f"   Match groups: cadastro={generic_match.group(1)}, cbo={generic_match.group(2)}, empresa={generic_match.group(3)}")
            else:
                print(f"   ❌ FALHOU - Ambos padrões falharam")
        
        # Resultado final
        print(f"\n✅ RESULTADO FINAL:")
        if empresa_num != 'UNKNOWN_EMP' and cadastro_num != 'UNKNOWN_CAD':
            empresa_formatted = str(empresa_num).zfill(4)
            cadastro_formatted = str(cadastro_num).zfill(5)
            file_identifier = f'{empresa_formatted}{cadastro_formatted}'
            print(f"   Identificador: {file_identifier}")
            print(f"   Status: ✅ SUCESSO - PDF será associado corretamente!")
        else:
            print(f"   Cadastro: {cadastro_num}")
            print(f"   Empresa: {empresa_num}")
            print(f"   Status: ❌ FALHOU - PDF ainda será marcado como UNKNOWN")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    tests_dir = "tests"
    
    pdf_files = [f for f in os.listdir(tests_dir) if f.endswith('.pdf')]
    
    print(f"\n{'#'*80}")
    print(f"# TESTE DO REGEX MELHORADO")
    print(f"# Total de arquivos: {len(pdf_files)}")
    print(f"{'#'*80}")
    
    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(tests_dir, pdf_file)
        test_improved_regex(pdf_path)
    
    print(f"\n{'#'*80}")
    print("# TESTE CONCLUÍDO")
    print(f"{'#'*80}\n")
