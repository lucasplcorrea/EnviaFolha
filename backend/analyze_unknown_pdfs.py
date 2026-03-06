"""
Script para analisar PDFs marcados como UNKNOWN
"""
import PyPDF2
import re
import os

def analyze_pdf(pdf_path):
    """Analisa o conteúdo de um PDF e tenta extrair matrícula"""
    print(f"\n{'='*80}")
    print(f"📄 Analisando: {os.path.basename(pdf_path)}")
    print(f"{'='*80}\n")
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            print(f"Total de páginas: {total_pages}\n")
            
            for page_num in range(min(2, total_pages)):  # Analisar primeiras 2 páginas
                print(f"\n--- PÁGINA {page_num + 1} ---\n")
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Mostrar primeiras 1000 caracteres
                print("Texto extraído (primeiros 1000 chars):")
                print("-" * 80)
                print(text[:1000])
                print("-" * 80)
                
                # Tentar regex para cadastro
                print("\n🔍 Buscando padrão de Cadastro:")
                cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
                if cadastro_match:
                    print(f"✅ ENCONTRADO: {cadastro_match.group(1)}")
                else:
                    print("❌ NÃO ENCONTRADO")
                    # Tentar padrões alternativos
                    print("\n🔍 Tentando padrão alternativo 1: apenas 'Cadastro' seguido de número")
                    alt1 = re.search(r'Cadastro[:\s]+(\d+)', text, re.IGNORECASE)
                    if alt1:
                        print(f"✅ ALTERNATIVO 1: {alt1.group(1)}")
                    
                    print("\n🔍 Tentando padrão alternativo 2: 'Cadastro' em qualquer posição")
                    alt2 = re.search(r'Cadastro.*?(\d{3,})', text, re.IGNORECASE | re.DOTALL)
                    if alt2:
                        print(f"✅ ALTERNATIVO 2: {alt2.group(1)}")
                
                # Tentar regex para empresa
                print("\n🔍 Buscando padrão de Empresa (ORIGINAL):")
                empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
                if empresa_field_match:
                    print(f"✅ ENCONTRADO: Grupo 1={empresa_field_match.group(1)}, Grupo 2={empresa_field_match.group(2)}, Grupo 3={empresa_field_match.group(3)}")
                else:
                    print("❌ NÃO ENCONTRADO")
                
                # Testar nova regex
                print("\n🔍 Buscando padrão de Empresa (NOVA REGEX):")
                new_empresa_match = re.search(
                    r'(\d{3,4})\s+[A-ZÀ-Úa-zà-ú\s]+\s+(\d{6})\s+(\d{1,3})\s+\d+\s+\d+',
                    text
                )
                if new_empresa_match:
                    print(f"✅ ENCONTRADO: Cadastro={new_empresa_match.group(1)}, CBO={new_empresa_match.group(2)}, Empresa={new_empresa_match.group(3)}")
                else:
                    print("❌ NÃO ENCONTRADO")
                
                # Fallback
                if cadastro_match:
                    cadastro_num = cadastro_match.group(1)
                    print(f"\n🔍 Buscando padrão FALLBACK (usando cadastro {cadastro_num}):")
                    line_pattern = rf'{cadastro_num}\s+[A-ZÀ-Úa-zà-ú\s]+\s+\d{{6}}\s+(\d{{1,3}})'
                    fallback_match = re.search(line_pattern, text)
                    if fallback_match:
                        print(f"✅ ENCONTRADO (FALLBACK): Empresa={fallback_match.group(1)}")
                        
                        # Montar matrícula completa
                        empresa_formatted = str(fallback_match.group(1)).zfill(4)
                        cadastro_formatted = str(cadastro_num).zfill(5)
                        full_matricula = f'{empresa_formatted}{cadastro_formatted}'
                        print(f"✅ MATRÍCULA COMPLETA: {full_matricula}")
                    else:
                        print("❌ NÃO ENCONTRADO (FALLBACK)")
                
                print("\n🔍 Buscando 'Empresa' no texto:")
                empresa_occurrences = re.finditer(r'Empresa[:\s]+(\d+)', text, re.IGNORECASE)
                for idx, match in enumerate(empresa_occurrences):
                    print(f"  Ocorrência {idx+1}: {match.group(1)}")
                
                # Buscar CPF
                print("\n🔍 Buscando CPF:")
                cpf_pattern = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
                cpf_matches = re.finditer(cpf_pattern, text)
                for idx, match in enumerate(cpf_matches):
                    cpf = re.sub(r'[^\d]', '', match.group())
                    if len(cpf) == 11:
                        print(f"  CPF {idx+1}: {cpf}")
                
                # Buscar nome do funcionário
                print("\n🔍 Buscando Nome do Funcionário:")
                name_patterns = [
                    r'Nome\s*do\s*Funcionário[:\s]+([A-ZÀ-Ú\s]+)',
                    r'Cadastro\s+Nome\s+do\s+Funcionário.*?\n\s*\d+\s+([A-ZÀ-Ú\s]+)',
                ]
                for pattern in name_patterns:
                    name_match = re.search(pattern, text, re.IGNORECASE)
                    if name_match:
                        print(f"✅ ENCONTRADO: {name_match.group(1).strip()}")
                        break
                else:
                    print("❌ NÃO ENCONTRADO")
                    
    except Exception as e:
        print(f"❌ ERRO ao processar PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Analisar os dois PDFs problemáticos
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'tests', 'Erros 02-2026')
    
    pdf_files = [
        'EN_UNKNOWN_134_11_02_2026_unlocked - Vitoria de Oliveira.pdf',
        'EN_UNKNOWN_257_11_02_2026_unlocked - Vitoria de Oliveira.pdf'
    ]
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(test_dir, pdf_file)
        if os.path.exists(pdf_path):
            analyze_pdf(pdf_path)
        else:
            print(f"⚠️  Arquivo não encontrado: {pdf_path}")
