#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Rápido para PDF Problemático
==================================

Script simples para analisar o PDF que está causando problemas
sem alterar o código principal do sistema.
"""

import os
import sys
import re

try:
    import PyPDF2
    print("✅ PyPDF2 disponível")
except ImportError:
    print("❌ PyPDF2 não disponível - instale com: pip install PyPDF2")
    sys.exit(1)

def debug_pdf_quick(pdf_path):
    """Análise rápida do PDF problemático"""
    print(f"\n🔍 Analisando: {os.path.basename(pdf_path)}")
    print("=" * 50)
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            print(f"📄 Total de páginas: {num_pages}")
            
            for i in range(num_pages):
                print(f"\n--- PÁGINA {i+1} ---")
                page = reader.pages[i]
                text = page.extract_text()
                
                # Salvar texto da página
                with open(f"debug_page_{i+1}.txt", 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"💾 Texto salvo em: debug_page_{i+1}.txt")
                
                # Testar os regex atuais do sistema
                print("\n🧪 Testando regex atuais:")
                
                # 1. Cadastro
                cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
                if cadastro_match:
                    print(f"✅ Cadastro: {cadastro_match.group(1)}")
                else:
                    print("❌ Cadastro: não encontrado")
                    # Mostrar onde está o problema
                    if "Cadastro" in text:
                        print("   ℹ️ Palavra 'Cadastro' encontrada, mas padrão não bate")
                        # Mostrar contexto ao redor da palavra Cadastro
                        cadastro_context = []
                        lines = text.split('\n')
                        for j, line in enumerate(lines):
                            if 'Cadastro' in line:
                                start = max(0, j-2)
                                end = min(len(lines), j+3)
                                print(f"   📝 Contexto (linhas {start+1}-{end}):")
                                for k in range(start, end):
                                    marker = ">>>" if k == j else "   "
                                    print(f"   {marker} {k+1}: {repr(lines[k])}")
                                break
                
                # 2. Empresa
                empresa_match = re.search(r'Empresa\s*Local\s*Departamento\s*FL\s*\n\s*\d+\s+[A-Z\s]+\s+\d+\s+(\d+)', text)
                if empresa_match:
                    print(f"✅ Empresa: {empresa_match.group(1)}")
                else:
                    print("❌ Empresa: não encontrado")
                    if "Empresa" in text:
                        print("   ℹ️ Palavra 'Empresa' encontrada, mas padrão não bate")
                
                # 3. CPF
                cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
                if cpf_match:
                    print(f"✅ CPF: {cpf_match.group(1)}")
                else:
                    print("❌ CPF: não encontrado")
                    # Buscar CPF em outros formatos
                    cpf_alt = re.search(r'CPF.*?(\d{3}[\.\s]*\d{3}[\.\s]*\d{3}[\-\s]*\d{2})', text)
                    if cpf_alt:
                        print(f"   ℹ️ CPF em formato alternativo: {cpf_alt.group(1)}")
                
                # 4. Data
                date_match = re.search(r"(\d{2}/\d{4})\s*Mensal", text)
                if date_match:
                    print(f"✅ Data: {date_match.group(1)}")
                else:
                    print("❌ Data: não encontrado")
                    # Buscar data em outros formatos
                    date_alt = re.search(r'\d{2}/\d{4}', text)
                    if date_alt:
                        print(f"   ℹ️ Data em formato alternativo: {date_alt.group(0)}")
                
                # Mostrar primeiras linhas do texto
                print(f"\n📝 Primeiras 10 linhas do texto:")
                lines = text.split('\n')[:10]
                for idx, line in enumerate(lines, 1):
                    print(f"{idx:2d}: {repr(line)}")
                
                # Mostrar números encontrados
                numbers = re.findall(r'\b\d{3,8}\b', text)
                unique_numbers = sorted(set(numbers))[:10]
                if unique_numbers:
                    print(f"\n🔢 Números encontrados (possíveis IDs): {unique_numbers}")
                
    except Exception as e:
        print(f"❌ Erro ao processar PDF: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔍 Debug Rápido para PDF Problemático")
    
    if len(sys.argv) < 2:
        print("\n❌ Uso: python quick_debug.py <caminho_do_pdf>")
        print("   Exemplo: python quick_debug.py holerites_problema.pdf")
        print("   Exemplo: python quick_debug.py uploads/arquivo.pdf")
        return
    
    pdf_path = sys.argv[1]
    
    # Converter para caminho absoluto se necessário
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.abspath(pdf_path)
    
    debug_pdf_quick(pdf_path)
    
    print("\n💡 Dicas:")
    print("   - Verifique os arquivos debug_page_X.txt gerados")
    print("   - Compare com PDFs que funcionam corretamente") 
    print("   - Procure por diferenças no layout ou formato do texto")

if __name__ == "__main__":
    main()