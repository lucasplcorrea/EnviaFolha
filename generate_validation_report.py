#!/usr/bin/env python3
"""
Script para criar um relatório detalhado de validação dos PDFs
"""
import os
import re
from PyPDF2 import PdfReader
from datetime import datetime

def analyze_pdf_detailed(pdf_path):
    """Analisa um PDF e retorna informações detalhadas"""
    try:
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            return None
            
        page = reader.pages[0]
        text = page.extract_text()
        
        # REGEX ANTIGO
        cadastro_match_old = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
        cadastro_old = cadastro_match_old.group(1) if cadastro_match_old else 'UNKNOWN_CAD'
        
        empresa_match_old = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
        empresa_old = empresa_match_old.group(3) if empresa_match_old else 'UNKNOWN_EMP'
        
        # REGEX NOVO
        cadastro_match_new = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
        cadastro_new = cadastro_match_new.group(1) if cadastro_match_new else 'UNKNOWN_CAD'
        
        empresa_new = 'UNKNOWN_EMP'
        header_match = re.search(
            r'Cadastro\s+Nome\s+do\s+Funcionário\s+CBO\s+Empresa\s+Local\s+Departamento\s+FL\s*\n\s*'
            r'(\d+)\s+([A-ZÀ-Ú\s\d]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
            text
        )
        
        method_used = None
        if header_match:
            empresa_new = header_match.group(4)
            method_used = "header_match"
        else:
            generic_match = re.search(r'^\s*(\d+)\s+[\w\sÀ-Ú]+\s+(\d{4,6})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text, re.MULTILINE)
            if generic_match:
                empresa_new = generic_match.group(3)
                method_used = "generic_match"
        
        # Extrair CPF e nome
        cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
        cpf = cpf_match.group(1) if cpf_match else 'Não encontrado'
        
        # Tentar extrair nome
        name_match = re.search(r'Cadastro\s+Nome\s+do\s+Funcionário\s+CBO\s+Empresa\s+Local\s+Departamento\s+FL\s*\n\s*\d+\s+([A-ZÀ-Ú\s\d]+?)\s+\d+', text)
        name = name_match.group(1).strip() if name_match else 'Não encontrado'
        
        # Mês/Ano
        month_match = re.search(r"(\d{2})\s*/\s*(\d{4})\s*(?:Mensal|13o?\s+Sal[aá]rio)", text, re.IGNORECASE)
        month_year = f"{month_match.group(1)}/{month_match.group(2)}" if month_match else 'Não encontrado'
        
        return {
            'filename': os.path.basename(pdf_path),
            'cadastro_old': cadastro_old,
            'empresa_old': empresa_old,
            'cadastro_new': cadastro_new,
            'empresa_new': empresa_new,
            'method_used': method_used,
            'cpf': cpf,
            'name': name,
            'month_year': month_year,
            'pages': len(reader.pages)
        }
    except Exception as e:
        return {
            'filename': os.path.basename(pdf_path),
            'error': str(e)
        }

def generate_report(directory):
    """Gera relatório completo de validação"""
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    results = []
    for pdf_path in sorted(pdf_files):
        info = analyze_pdf_detailed(pdf_path)
        if info:
            results.append(info)
    
    # Criar relatório
    report_lines = []
    report_lines.append("="*120)
    report_lines.append("RELATÓRIO DE VALIDAÇÃO DE PDFs - REGEX ANTIGO vs NOVO")
    report_lines.append("="*120)
    report_lines.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    report_lines.append(f"Diretório analisado: {directory}")
    report_lines.append(f"Total de PDFs: {len(results)}")
    report_lines.append("="*120)
    report_lines.append("")
    
    success_old = sum(1 for r in results if 'error' not in r and r['cadastro_old'] != 'UNKNOWN_CAD' and r['empresa_old'] != 'UNKNOWN_EMP')
    success_new = sum(1 for r in results if 'error' not in r and r['cadastro_new'] != 'UNKNOWN_CAD' and r['empresa_new'] != 'UNKNOWN_EMP')
    
    report_lines.append("📊 RESUMO EXECUTIVO:")
    report_lines.append(f"   Regex ANTIGO: {success_old}/{len(results)} PDFs identificados com sucesso ({success_old/len(results)*100:.1f}%)")
    report_lines.append(f"   Regex NOVO:   {success_new}/{len(results)} PDFs identificados com sucesso ({success_new/len(results)*100:.1f}%)")
    report_lines.append(f"   Melhoria:     +{success_new - success_old} PDFs")
    report_lines.append("")
    report_lines.append("="*120)
    report_lines.append("")
    
    # Agrupar resultados por categoria
    melhorados = []
    ok_sem_mudanca = []
    regressoes = []
    mudancas = []
    
    for info in results:
        if 'error' in info:
            continue
        
        old_id = f"{str(info['empresa_old']).zfill(4)}{str(info['cadastro_old']).zfill(5)}" if info['empresa_old'] != 'UNKNOWN_EMP' else 'UNKNOWN'
        new_id = f"{str(info['empresa_new']).zfill(4)}{str(info['cadastro_new']).zfill(5)}" if info['empresa_new'] != 'UNKNOWN_EMP' else 'UNKNOWN'
        
        old_ok = info['cadastro_old'] != 'UNKNOWN_CAD' and info['empresa_old'] != 'UNKNOWN_EMP'
        new_ok = info['cadastro_new'] != 'UNKNOWN_CAD' and info['empresa_new'] != 'UNKNOWN_EMP'
        
        if not old_ok and new_ok:
            melhorados.append(info)
        elif old_ok and new_ok and old_id == new_id:
            ok_sem_mudanca.append(info)
        elif old_ok and not new_ok:
            regressoes.append(info)
        elif old_ok and new_ok and old_id != new_id:
            mudancas.append(info)
    
    report_lines.append("📊 DETALHAMENTO POR CATEGORIA:")
    report_lines.append("")
    report_lines.append(f"✅ MELHORADOS (eram UNKNOWN, agora funcionam): {len(melhorados)}")
    report_lines.append(f"✓  SEM MUDANÇA (continuam funcionando): {len(ok_sem_mudanca)}")
    report_lines.append(f"⚠️  MUDANÇAS DE ID (funcionavam, mas ID mudou): {len(mudancas)}")
    report_lines.append(f"❌ REGRESSÕES (funcionavam, agora UNKNOWN): {len(regressoes)}")
    report_lines.append("")
    report_lines.append("="*120)
    report_lines.append("")
    
    # Detalhamento por arquivo (limitado a 50 para não ficar muito grande)
    show_limit = 50
    for i, info in enumerate(results, 1):
        if i > show_limit and len(results) > show_limit:
            report_lines.append(f"... e mais {len(results) - show_limit} PDFs (veja resumo acima)")
            break
        if 'error' in info:
            report_lines.append(f"{i}. ❌ {info['filename']}")
            report_lines.append(f"   ERRO: {info['error']}")
            report_lines.append("")
            continue
        
        old_id = f"{str(info['empresa_old']).zfill(4)}{str(info['cadastro_old']).zfill(5)}" if info['empresa_old'] != 'UNKNOWN_EMP' else 'UNKNOWN'
        new_id = f"{str(info['empresa_new']).zfill(4)}{str(info['cadastro_new']).zfill(5)}" if info['empresa_new'] != 'UNKNOWN_EMP' else 'UNKNOWN'
        
        old_ok = info['cadastro_old'] != 'UNKNOWN_CAD' and info['empresa_old'] != 'UNKNOWN_EMP'
        new_ok = info['cadastro_new'] != 'UNKNOWN_CAD' and info['empresa_new'] != 'UNKNOWN_EMP'
        
        if not old_ok and new_ok:
            status = "✅ MELHORADO"
        elif old_ok and new_ok and old_id == new_id:
            status = "✓ OK (sem mudança)"
        elif old_ok and not new_ok:
            status = "❌ REGRESSÃO"
        elif old_ok and new_ok and old_id != new_id:
            status = "⚠️  MUDOU"
        else:
            status = "⚠️  AMBOS FALHARAM"
        
        report_lines.append(f"{i}. {status} | {info['filename']}")
        report_lines.append(f"   Nome:      {info['name']}")
        report_lines.append(f"   CPF:       {info['cpf']}")
        report_lines.append(f"   Período:   {info['month_year']}")
        report_lines.append(f"   Páginas:   {info['pages']}")
        report_lines.append(f"   ID Antigo: {old_id} (Empresa: {info['empresa_old']}, Cadastro: {info['cadastro_old']})")
        report_lines.append(f"   ID Novo:   {new_id} (Empresa: {info['empresa_new']}, Cadastro: {info['cadastro_new']})")
        if info['method_used']:
            report_lines.append(f"   Método:    {info['method_used']}")
        report_lines.append("")
    
    report_lines.append("="*120)
    report_lines.append("CONCLUSÃO:")
    report_lines.append("="*120)
    
    regressions = [r for r in results if 'error' not in r and 
                   r['cadastro_old'] != 'UNKNOWN_CAD' and r['empresa_old'] != 'UNKNOWN_EMP' and
                   (r['cadastro_new'] == 'UNKNOWN_CAD' or r['empresa_new'] == 'UNKNOWN_EMP')]
    
    improvements = [r for r in results if 'error' not in r and 
                    (r['cadastro_old'] == 'UNKNOWN_CAD' or r['empresa_old'] == 'UNKNOWN_EMP') and
                    r['cadastro_new'] != 'UNKNOWN_CAD' and r['empresa_new'] != 'UNKNOWN_EMP']
    
    if len(regressions) > 0:
        report_lines.append(f"❌ NÃO APLICAR - {len(regressions)} regressão(ões) detectada(s)")
    elif len(improvements) > 0:
        report_lines.append(f"✅ SEGURO APLICAR - {len(improvements)} melhoria(s), {len(regressions)} regressão(ões)")
    else:
        report_lines.append("ℹ️  Mudança neutra - sem impacto significativo")
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    import sys
    
    directory = sys.argv[1] if len(sys.argv) > 1 else "tests/validated"
    
    report = generate_report(directory)
    print(report)
    
    # Salvar em arquivo
    report_file = f"VALIDATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Relatório salvo em: {report_file}")
