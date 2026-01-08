#!/usr/bin/env python3
"""
Script para simular o processamento completo de segmentação de PDFs
Testa TODAS as páginas de cada PDF, como o código real faz
"""
import os
import re
from PyPDF2 import PdfReader
from datetime import datetime

def test_old_regex_page(text):
    """Regex ORIGINAL (antes da correção) - por página"""
    cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
    cadastro_num = cadastro_match.group(1) if cadastro_match else 'UNKNOWN_CAD'
    
    empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
    empresa_num = empresa_field_match.group(3) if empresa_field_match else 'UNKNOWN_EMP'
    
    return cadastro_num, empresa_num

def test_new_regex_page(text):
    """Regex NOVO (com a correção) - por página"""
    cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
    cadastro_num = cadastro_match.group(1) if cadastro_match else 'UNKNOWN_CAD'
    
    empresa_num = 'UNKNOWN_EMP'
    
    # Tentar padrão com cabeçalho (NOVO)
    header_match = re.search(
        r'Cadastro\s+Nome\s+do\s+Funcionário\s+CBO\s+Empresa\s+Local\s+Departamento\s+FL\s*\n\s*'
        r'(\d+)\s+([A-ZÀ-Ú\s\d]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
        text
    )
    
    if header_match:
        empresa_num = header_match.group(4)
    else:
        # Fallback: padrão mais genérico (NOVO)
        generic_match = re.search(r'^\s*(\d+)\s+[\w\sÀ-Ú]+\s+(\d{4,6})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text, re.MULTILINE)
        if generic_match:
            empresa_num = generic_match.group(3)
    
    return cadastro_num, empresa_num

def process_all_pages(pdf_path):
    """Processa TODAS as páginas do PDF, simulando o código de segmentação real"""
    results = {
        'filename': os.path.basename(pdf_path),
        'total_pages': 0,
        'pages': [],
        'old_success': 0,
        'new_success': 0,
        'old_failed': 0,
        'new_failed': 0,
        'improved_pages': [],
        'regressed_pages': [],
        'changed_pages': []
    }
    
    try:
        reader = PdfReader(pdf_path)
        results['total_pages'] = len(reader.pages)
        
        print(f"\n{'='*100}")
        print(f"Processando: {results['filename']}")
        print(f"Total de páginas: {results['total_pages']}")
        print(f"{'='*100}\n")
        
        for i, page in enumerate(reader.pages):
            page_num = i + 1
            text = page.extract_text()
            
            # Testar ambos os regex
            old_cadastro, old_empresa = test_old_regex_page(text)
            new_cadastro, new_empresa = test_new_regex_page(text)
            
            old_success = (old_cadastro != 'UNKNOWN_CAD' and old_empresa != 'UNKNOWN_EMP')
            new_success = (new_cadastro != 'UNKNOWN_CAD' and new_empresa != 'UNKNOWN_EMP')
            
            if old_success:
                results['old_success'] += 1
            else:
                results['old_failed'] += 1
            
            if new_success:
                results['new_success'] += 1
            else:
                results['new_failed'] += 1
            
            old_id = f"{str(old_empresa).zfill(4)}{str(old_cadastro).zfill(5)}" if old_success else 'UNKNOWN'
            new_id = f"{str(new_empresa).zfill(4)}{str(new_cadastro).zfill(5)}" if new_success else 'UNKNOWN'
            
            page_info = {
                'page_num': page_num,
                'old_cadastro': old_cadastro,
                'old_empresa': old_empresa,
                'new_cadastro': new_cadastro,
                'new_empresa': new_empresa,
                'old_id': old_id,
                'new_id': new_id,
                'old_success': old_success,
                'new_success': new_success
            }
            
            results['pages'].append(page_info)
            
            # Classificar mudanças
            if not old_success and new_success:
                results['improved_pages'].append(page_num)
                print(f"  ✅ Página {page_num}: MELHORADO - {old_id} → {new_id}")
            elif old_success and not new_success:
                results['regressed_pages'].append(page_num)
                print(f"  ❌ Página {page_num}: REGRESSÃO! - {old_id} → {new_id}")
            elif old_success and new_success and old_id != new_id:
                results['changed_pages'].append(page_num)
                print(f"  ⚠️  Página {page_num}: MUDOU ID - {old_id} → {new_id}")
            elif not old_success and not new_success:
                if page_num % 50 == 0:  # Mostrar progresso a cada 50 páginas
                    print(f"  ⚠️  Página {page_num}: Ambos falharam")
            else:
                if page_num % 100 == 0:  # Mostrar progresso a cada 100 páginas
                    print(f"  ✓  Página {page_num}: OK (sem mudança)")
        
    except Exception as e:
        print(f"❌ ERRO ao processar {pdf_path}: {e}")
        results['error'] = str(e)
    
    return results

def generate_full_report(directory):
    """Gera relatório completo processando TODAS as páginas de TODOS os PDFs"""
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    print(f"\n{'#'*100}")
    print(f"# TESTE COMPLETO DE SEGMENTAÇÃO - TODAS AS PÁGINAS")
    print(f"# Diretório: {directory}")
    print(f"# Total de PDFs: {len(pdf_files)}")
    print(f"{'#'*100}")
    
    all_results = []
    total_pages = 0
    total_old_success = 0
    total_new_success = 0
    total_improved = 0
    total_regressed = 0
    total_changed = 0
    
    for pdf_path in sorted(pdf_files):
        result = process_all_pages(pdf_path)
        all_results.append(result)
        
        total_pages += result['total_pages']
        total_old_success += result['old_success']
        total_new_success += result['new_success']
        total_improved += len(result['improved_pages'])
        total_regressed += len(result['regressed_pages'])
        total_changed += len(result['changed_pages'])
    
    # Relatório final
    print(f"\n{'#'*100}")
    print(f"# RELATÓRIO FINAL - PROCESSAMENTO COMPLETO")
    print(f"{'#'*100}\n")
    
    print(f"📊 ESTATÍSTICAS GERAIS:")
    print(f"   Total de PDFs processados: {len(pdf_files)}")
    print(f"   Total de páginas analisadas: {total_pages}")
    print(f"   Regex ANTIGO - Sucesso: {total_old_success}/{total_pages} ({total_old_success/total_pages*100:.1f}%)")
    print(f"   Regex NOVO   - Sucesso: {total_new_success}/{total_pages} ({total_new_success/total_pages*100:.1f}%)")
    print(f"   Melhoria:     +{total_new_success - total_old_success} páginas")
    print()
    
    print(f"📈 DETALHAMENTO:")
    print(f"   ✅ Páginas melhoradas (UNKNOWN → OK): {total_improved}")
    print(f"   ⚠️  Páginas com ID alterado: {total_changed}")
    print(f"   ❌ Páginas com regressão (OK → UNKNOWN): {total_regressed}")
    print()
    
    print(f"📄 DETALHES POR PDF:")
    for result in all_results:
        print(f"\n   {result['filename']}:")
        print(f"      Total de páginas: {result['total_pages']}")
        print(f"      Antigo: {result['old_success']}/{result['total_pages']} OK ({result['old_success']/result['total_pages']*100:.1f}%)")
        print(f"      Novo:   {result['new_success']}/{result['total_pages']} OK ({result['new_success']/result['total_pages']*100:.1f}%)")
        
        if len(result['improved_pages']) > 0:
            print(f"      ✅ {len(result['improved_pages'])} páginas melhoradas")
            if len(result['improved_pages']) <= 10:
                print(f"         Páginas: {', '.join(map(str, result['improved_pages']))}")
        
        if len(result['regressed_pages']) > 0:
            print(f"      ❌ {len(result['regressed_pages'])} REGRESSÕES nas páginas: {', '.join(map(str, result['regressed_pages']))}")
        
        if len(result['changed_pages']) > 0:
            print(f"      ⚠️  {len(result['changed_pages'])} mudanças de ID nas páginas: {', '.join(map(str, result['changed_pages'][:10]))}")
    
    print(f"\n{'#'*100}")
    print(f"# CONCLUSÃO")
    print(f"{'#'*100}\n")
    
    if total_regressed > 0:
        print(f"❌ NÃO APLICAR A MUDANÇA!")
        print(f"   {total_regressed} páginas que funcionavam serão quebradas!")
        print(f"   É necessário revisar o regex antes de aplicar em produção.")
    elif total_changed > 0:
        print(f"⚠️  ATENÇÃO - {total_changed} páginas terão IDs alterados!")
        print(f"   Verifique se isso é esperado antes de aplicar.")
        print(f"   Melhoria: +{total_improved} páginas")
    elif total_improved > 0:
        print(f"✅ MUDANÇA 100% SEGURA PARA APLICAR!")
        print(f"   {total_improved} páginas melhoradas (UNKNOWN → identificadas corretamente)")
        print(f"   {total_old_success} páginas continuam funcionando perfeitamente")
        print(f"   0 regressões detectadas")
    else:
        print(f"ℹ️  Mudança neutra - sem impacto significativo")
    
    # Salvar relatório
    report_file = f"FULL_VALIDATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"Relatório de Validação Completa - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Total de PDFs: {len(pdf_files)}\n")
        f.write(f"Total de páginas: {total_pages}\n")
        f.write(f"Regex antigo: {total_old_success}/{total_pages} OK\n")
        f.write(f"Regex novo: {total_new_success}/{total_pages} OK\n")
        f.write(f"Melhorias: {total_improved}\n")
        f.write(f"Regressões: {total_regressed}\n")
        f.write(f"Mudanças de ID: {total_changed}\n")
    
    print(f"\n✅ Relatório salvo em: {report_file}\n")

if __name__ == "__main__":
    import sys
    
    directory = sys.argv[1] if len(sys.argv) > 1 else "tests"
    generate_full_report(directory)
