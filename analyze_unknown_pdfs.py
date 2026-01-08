#!/usr/bin/env python3
"""
Script para analisar PDFs marcados como UNKNOWN e identificar o problema
"""
import os
import re
from PyPDF2 import PdfReader

def analyze_pdf(pdf_path):
    """Analisa um PDF e mostra o que o código de parsing está tentando encontrar"""
    print(f"\n{'='*80}")
    print(f"Analisando: {os.path.basename(pdf_path)}")
    print(f"{'='*80}\n")
    
    try:
        reader = PdfReader(pdf_path)
        
        for i, page in enumerate(reader.pages):
            print(f"\n--- PÁGINA {i+1} ---\n")
            text = page.extract_text()
            
            # Mostrar primeiras 500 caracteres do texto
            print("TEXTO EXTRAÍDO (primeiros 500 caracteres):")
            print("-" * 80)
            print(text[:500])
            print("-" * 80)
            
            # Tentar encontrar número de cadastro (PADRÃO 1 - main_legacy.py linha 3655)
            print("\n🔍 BUSCANDO: Número de Cadastro")
            print("   Padrão: 'Cadastro\\s*Nome\\s*do\\s*Funcionário\\s*CBO\\s*Empresa\\s*Local\\s*Departamento\\s*FL\\s*\\n\\s*(\\d+)'")
            cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
            if cadastro_match:
                print(f"   ✅ ENCONTRADO: {cadastro_match.group(1)}")
            else:
                print(f"   ❌ NÃO ENCONTRADO")
                # Tentar encontrar a palavra "Cadastro" isolada
                if 'Cadastro' in text:
                    idx = text.find('Cadastro')
                    print(f"   ℹ️  Palavra 'Cadastro' encontrada no texto:")
                    print(f"      {text[idx:idx+200]}")
            
            # Tentar encontrar número da empresa (PADRÃO 2 - main_legacy.py linha 3659)
            print("\n🔍 BUSCANDO: Número da Empresa")
            print("   Padrão: '(\\d+)\\s+[A-ZÀ-Ú\\s]+\\s+(\\d+)\\s+(\\d+)\\s+\\d+\\s+\\d+\\s+\\d+'")
            empresa_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
            if empresa_match:
                print(f"   ✅ ENCONTRADO: {empresa_match.group(3)}")
            else:
                print(f"   ❌ NÃO ENCONTRADO")
            
            # Tentar encontrar CPF (main_legacy.py linha 3672)
            print("\n🔍 BUSCANDO: CPF")
            print("   Padrão: 'CPF:\\s*(\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2})'")
            cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
            if cpf_match:
                cpf_full = cpf_match.group(1).replace('.', '').replace('-', '')
                print(f"   ✅ ENCONTRADO: {cpf_match.group(1)} (4 primeiros dígitos: {cpf_full[:4]})")
            else:
                print(f"   ❌ NÃO ENCONTRADO")
                # Tentar encontrar a palavra "CPF" isolada
                if 'CPF' in text:
                    idx = text.find('CPF')
                    print(f"   ℹ️  Palavra 'CPF' encontrada no texto:")
                    print(f"      {text[idx:idx+100]}")
            
            # Tentar encontrar mês/ano (main_legacy.py linha 3677)
            print("\n🔍 BUSCANDO: Mês/Ano de Referência")
            print("   Padrão: '(\\d{2})\\s*/\\s*(\\d{4})\\s*(?:Mensal|13o?\\s+Sal[aá]rio)'")
            month_year_match = re.search(r"(\d{2})\s*/\s*(\d{4})\s*(?:Mensal|13o?\s+Sal[aá]rio)", text, re.IGNORECASE)
            if month_year_match:
                print(f"   ✅ ENCONTRADO: {month_year_match.group(1)}/{month_year_match.group(2)}")
            else:
                print(f"   ❌ NÃO ENCONTRADO")
                # Buscar padrões de data alternativos
                alt_patterns = [
                    (r"(\d{2})/(\d{4})", "DD/YYYY"),
                    (r"(\d{4})-(\d{2})", "YYYY-MM"),
                    (r"(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s*de\s*(\d{4})", "mês por extenso"),
                ]
                for pattern, desc in alt_patterns:
                    alt_match = re.search(pattern, text, re.IGNORECASE)
                    if alt_match:
                        print(f"   ℹ️  Padrão alternativo encontrado ({desc}): {alt_match.group(0)}")
                        break
            
            print("\n" + "="*80)
            
    except Exception as e:
        print(f"❌ ERRO ao analisar PDF: {e}")

if __name__ == "__main__":
    tests_dir = "tests"
    
    if not os.path.exists(tests_dir):
        print(f"❌ Diretório '{tests_dir}' não encontrado")
        exit(1)
    
    pdf_files = [f for f in os.listdir(tests_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ Nenhum PDF encontrado em '{tests_dir}'")
        exit(1)
    
    print(f"\n{'#'*80}")
    print(f"# ANÁLISE DE PDFs MARCADOS COMO UNKNOWN")
    print(f"# Total de arquivos: {len(pdf_files)}")
    print(f"{'#'*80}")
    
    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(tests_dir, pdf_file)
        analyze_pdf(pdf_path)
    
    print(f"\n{'#'*80}")
    print("# ANÁLISE CONCLUÍDA")
    print(f"{'#'*80}\n")
    
    print("\n📋 RESUMO:")
    print("Os PDFs foram marcados como 'UNKNOWN' porque o regex não conseguiu extrair:")
    print("  1. Número de Cadastro (matrícula do funcionário)")
    print("  2. Número da Empresa")
    print("\nSEM essas informações, o sistema não consegue:")
    print("  - Criar o identificador único (EEEEECCCCC - 4 dígitos empresa + 5 dígitos cadastro)")
    print("  - Associar o holerite ao colaborador correto no banco de dados")
    print("\n💡 POSSÍVEIS CAUSAS:")
    print("  - Layout do PDF diferente do esperado")
    print("  - Texto não extraível (PDF pode ser imagem/scan)")
    print("  - Campos com nomes diferentes ou formatação diferente")
    print("  - PDF corrompido ou mal formatado")
    print("\n🔧 SOLUÇÕES:")
    print("  1. Verificar se o PDF tem texto extraível (não é apenas imagem)")
    print("  2. Ajustar os padrões regex para o layout real do PDF")
    print("  3. Adicionar padrões alternativos de busca")
    print("  4. Implementar OCR se for PDF escaneado")
