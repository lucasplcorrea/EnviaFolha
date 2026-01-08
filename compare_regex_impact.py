#!/usr/bin/env python3
"""
Script para comparar o comportamento ANTES e DEPOIS da mudança no regex
e garantir que não quebramos PDFs que já funcionavam
"""
import os
import re
from PyPDF2 import PdfReader

def test_old_regex(text):
    """Regex ORIGINAL (antes da correção)"""
    cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
    cadastro_num = cadastro_match.group(1) if cadastro_match else 'UNKNOWN_CAD'
    
    empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
    empresa_num = empresa_field_match.group(3) if empresa_field_match else 'UNKNOWN_EMP'
    
    return cadastro_num, empresa_num

def test_new_regex(text):
    """Regex NOVO (com a correção)"""
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
        empresa_num = header_match.group(4)  # Quarto número é a empresa
    else:
        # Fallback: padrão mais genérico (NOVO)
        generic_match = re.search(r'^\s*(\d+)\s+[\w\sÀ-Ú]+\s+(\d{4,6})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text, re.MULTILINE)
        if generic_match:
            empresa_num = generic_match.group(3)  # Terceiro número = empresa
    
    return cadastro_num, empresa_num

def compare_pdfs(directory):
    """Compara resultados de todos os PDFs no diretório"""
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    results = {
        'total': len(pdf_files),
        'old_success': 0,
        'new_success': 0,
        'old_failed': 0,
        'new_failed': 0,
        'improved': [],  # PDFs que eram UNKNOWN e agora funcionam
        'regressed': [],  # PDFs que funcionavam e agora falharam (CRÍTICO!)
        'unchanged_ok': [],  # PDFs que continuam funcionando
        'unchanged_fail': []  # PDFs que continuam falhando
    }
    
    print(f"\n{'='*100}")
    print(f"ANÁLISE COMPARATIVA: REGEX ANTIGO vs NOVO")
    print(f"{'='*100}\n")
    print(f"Diretório: {directory}")
    print(f"Total de PDFs encontrados: {len(pdf_files)}\n")
    
    for pdf_path in sorted(pdf_files):
        filename = os.path.basename(pdf_path)
        
        try:
            reader = PdfReader(pdf_path)
            if len(reader.pages) == 0:
                continue
                
            page = reader.pages[0]
            text = page.extract_text()
            
            # Testar ambos os regex
            old_cadastro, old_empresa = test_old_regex(text)
            new_cadastro, new_empresa = test_new_regex(text)
            
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
            
            # Classificar mudanças
            if not old_success and new_success:
                # MELHORIA: Era UNKNOWN, agora funciona!
                results['improved'].append({
                    'file': filename,
                    'old_id': f"{old_empresa}{old_cadastro}",
                    'new_id': f"{str(new_empresa).zfill(4)}{str(new_cadastro).zfill(5)}"
                })
            elif old_success and not new_success:
                # REGRESSÃO: Funcionava, agora falhou! (PROBLEMA!)
                results['regressed'].append({
                    'file': filename,
                    'old_id': f"{str(old_empresa).zfill(4)}{str(old_cadastro).zfill(5)}",
                    'new_id': f"{new_empresa}{new_cadastro}"
                })
            elif old_success and new_success:
                # Ambos funcionam - verificar se dão o mesmo resultado
                old_id = f"{str(old_empresa).zfill(4)}{str(old_cadastro).zfill(5)}"
                new_id = f"{str(new_empresa).zfill(4)}{str(new_cadastro).zfill(5)}"
                
                if old_id == new_id:
                    results['unchanged_ok'].append(filename)
                else:
                    # MUDANÇA DE VALOR - pode ser problema!
                    results['regressed'].append({
                        'file': filename,
                        'old_id': old_id,
                        'new_id': new_id,
                        'note': 'IDs diferentes!'
                    })
            else:
                # Ambos falham
                results['unchanged_fail'].append(filename)
                
        except Exception as e:
            print(f"⚠️  Erro ao processar {filename}: {e}")
    
    # Relatório
    print(f"\n{'='*100}")
    print(f"RESULTADOS DA COMPARAÇÃO")
    print(f"{'='*100}\n")
    
    print(f"📊 ESTATÍSTICAS GERAIS:")
    print(f"   Total de PDFs analisados: {results['total']}")
    print(f"   Regex ANTIGO - Sucesso: {results['old_success']} | Falhas: {results['old_failed']}")
    print(f"   Regex NOVO   - Sucesso: {results['new_success']} | Falhas: {results['new_failed']}")
    
    print(f"\n✅ MELHORIAS (PDFs que eram UNKNOWN e agora funcionam): {len(results['improved'])}")
    for item in results['improved'][:10]:  # Mostrar primeiros 10
        print(f"   • {item['file']}: {item['old_id']} → {item['new_id']}")
    if len(results['improved']) > 10:
        print(f"   ... e mais {len(results['improved']) - 10} arquivos")
    
    print(f"\n🔄 SEM MUDANÇA (PDFs que continuam funcionando): {len(results['unchanged_ok'])}")
    if len(results['unchanged_ok']) > 0:
        print(f"   Primeiros exemplos: {', '.join(results['unchanged_ok'][:5])}")
    
    print(f"\n⚠️  SEM MUDANÇA (PDFs que continuam falhando): {len(results['unchanged_fail'])}")
    if len(results['unchanged_fail']) > 0:
        print(f"   Primeiros exemplos: {', '.join(results['unchanged_fail'][:5])}")
    
    print(f"\n❌ REGRESSÕES (PDFs que funcionavam e PARARAM de funcionar): {len(results['regressed'])}")
    if len(results['regressed']) > 0:
        print("\n   ⚠️⚠️⚠️  ATENÇÃO - ESTAS MUDANÇAS SÃO CRÍTICAS! ⚠️⚠️⚠️")
        for item in results['regressed']:
            note = f" ({item.get('note', '')})" if 'note' in item else ""
            print(f"   • {item['file']}: {item['old_id']} → {item['new_id']}{note}")
    
    print(f"\n{'='*100}")
    print(f"CONCLUSÃO")
    print(f"{'='*100}\n")
    
    if len(results['regressed']) > 0:
        print("❌ NÃO APLICAR A MUDANÇA!")
        print(f"   {len(results['regressed'])} PDFs que funcionavam serão quebrados!")
        print("   É necessário ajustar o regex para não quebrar PDFs existentes.")
    elif len(results['improved']) > 0:
        print("✅ MUDANÇA SEGURA PARA APLICAR!")
        print(f"   {len(results['improved'])} PDFs melhorados (UNKNOWN → funcionando)")
        print(f"   {len(results['unchanged_ok'])} PDFs continuam funcionando corretamente")
        print(f"   {len(results['unchanged_fail'])} PDFs continuam falhando (não piora)")
    else:
        print("ℹ️  Mudança não tem impacto significativo")
    
    return results

if __name__ == "__main__":
    import sys
    
    # Diretórios para testar
    test_dirs = [
        "tests",  # PDFs problemáticos
        "processed",  # PDFs já processados
        "holerites_formatados_final",  # PDFs formatados
    ]
    
    # Permitir passar diretório via argumento
    if len(sys.argv) > 1:
        test_dirs = [sys.argv[1]]
    
    all_results = {
        'total': 0,
        'old_success': 0,
        'new_success': 0,
        'improved': [],
        'regressed': [],
        'unchanged_ok': []
    }
    
    for directory in test_dirs:
        if os.path.exists(directory):
            print(f"\n{'#'*100}")
            print(f"# Analisando diretório: {directory}")
            print(f"{'#'*100}")
            results = compare_pdfs(directory)
            
            # Acumular resultados
            all_results['total'] += results['total']
            all_results['old_success'] += results['old_success']
            all_results['new_success'] += results['new_success']
            all_results['improved'].extend(results['improved'])
            all_results['regressed'].extend(results['regressed'])
            all_results['unchanged_ok'].extend(results['unchanged_ok'])
    
    print(f"\n{'#'*100}")
    print(f"# RESUMO FINAL - TODOS OS DIRETÓRIOS")
    print(f"{'#'*100}\n")
    print(f"Total de PDFs: {all_results['total']}")
    print(f"Melhorias: {len(all_results['improved'])} PDFs")
    print(f"Regressões: {len(all_results['regressed'])} PDFs")
    print(f"Sem mudança (OK): {len(all_results['unchanged_ok'])} PDFs")
    
    if len(all_results['regressed']) > 0:
        print(f"\n❌ CONCLUSÃO: NÃO APLICAR - {len(all_results['regressed'])} PDFs seriam quebrados!")
    else:
        print(f"\n✅ CONCLUSÃO: SEGURO APLICAR - {len(all_results['improved'])} PDFs melhorados, nenhuma regressão!")
