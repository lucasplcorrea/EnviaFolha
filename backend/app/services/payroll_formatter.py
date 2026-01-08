"""
Serviço de Processamento de Holerites com Novo Formato
========================================================

Formato de nomenclatura: EN_MATRICULA_TIPO_MES_ANO.pdf

Tipos de holerite:
- 11: Mensal
- 31: Adiantamento 13º
- 32: 13º Integral
- 91: Adiantamento Salarial

Matrícula: Sem zeros à esquerda (006000169 → 6000169)
Organização: processed/{tipo}_{mes}_{ano}/
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime
import PyPDF2
from io import BytesIO


class PayrollFormatter:
    """Classe para formatar e organizar holerites no novo padrão"""
    
    PAYROLL_TYPES = {
        '11': 'Mensal',
        '31': 'Adiantamento_13',
        '32': '13_Integral',
        '91': 'Adiantamento_Salarial'
    }
    
    def __init__(self, payroll_type: str, month: int, year: int, base_dir: str = 'processed'):
        """
        Inicializa o formatador
        
        Args:
            payroll_type: Tipo do holerite (11, 31, 32, 91)
            month: Mês de competência (1-12)
            year: Ano de competência
            base_dir: Diretório base para salvar arquivos processados
        """
        self.payroll_type = payroll_type
        self.month = month
        self.year = year
        self.base_dir = base_dir
        
        # Validar tipo
        if payroll_type not in self.PAYROLL_TYPES:
            raise ValueError(f"Tipo de holerite inválido: {payroll_type}. Use: {list(self.PAYROLL_TYPES.keys())}")
        
        # Validar mês
        if not 1 <= month <= 12:
            raise ValueError(f"Mês inválido: {month}. Use 1-12")
        
        # Criar diretório de destino
        self.output_dir = self._create_output_directory()
    
    def _create_output_directory(self) -> str:
        """Cria diretório organizado por tipo/período"""
        type_name = self.PAYROLL_TYPES[self.payroll_type]
        folder_name = f"{type_name}_{self.month:02d}_{self.year}"
        output_path = os.path.join(self.base_dir, folder_name)
        
        os.makedirs(output_path, exist_ok=True)
        print(f"📁 Diretório criado: {output_path}")
        
        return output_path
    
    def remove_leading_zeros(self, matricula: str) -> str:
        """
        Remove zeros à esquerda da matrícula
        
        Exemplo: 005900169 → 5900169
        Exemplo: 006001234 → 6001234
        """
        try:
            return str(int(matricula))
        except (ValueError, TypeError):
            # Se não for um número válido, retornar como está
            return matricula
    
    def format_filename(self, matricula: str) -> str:
        """
        Gera nome do arquivo no novo formato
        
        Formato: EN_MATRICULA_TIPO_MES_ANO.pdf
        Exemplo: EN_6000169_11_12_2024.pdf
        """
        clean_matricula = self.remove_leading_zeros(matricula)
        filename = f"EN_{clean_matricula}_{self.payroll_type}_{self.month:02d}_{self.year}.pdf"
        return filename
    
    def extract_empresa_cadastro_from_text(self, text: str) -> Optional[str]:
        """Extrai empresa + cadastro do PDF para formar matrícula completa
        
        Exemplo:
        - Empresa: 59, Cadastro: 169 → 005900169
        - Empresa: 60, Cadastro: 1234 → 006001234
        """
        # Regex para encontrar o número de cadastro
        cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
        cadastro_num = cadastro_match.group(1) if cadastro_match else None
        
        # Regex para encontrar o número da empresa
        empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
        empresa_num = empresa_field_match.group(3) if empresa_field_match else None
        
        if empresa_num and cadastro_num:
            # Formatação: XXXXYYYYY (empresa com 4 dígitos + cadastro com 5)
            empresa_formatted = str(empresa_num).zfill(4)
            cadastro_formatted = str(cadastro_num).zfill(5)
            full_matricula = f'{empresa_formatted}{cadastro_formatted}'
            return full_matricula
        
        return None
    
    def extract_cpf_from_text(self, text: str) -> Optional[str]:
        """Extrai CPF do texto do PDF"""
        # Procurar padrão XXX.XXX.XXX-XX ou apenas números
        cpf_pattern = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
        match = re.search(cpf_pattern, text)
        
        if match:
            cpf = match.group()
            # Remover formatação
            cpf = re.sub(r'[^\d]', '', cpf)
            if len(cpf) == 11:
                return cpf
        
        return None
    
    def get_cpf_password(self, cpf: str) -> str:
        """
        Retorna senha baseada nos primeiros 4 dígitos do CPF
        """
        if cpf and len(cpf) >= 4:
            return cpf[:4]
        return "0000"  # Senha padrão caso não encontre CPF
    
    def protect_pdf_with_password(self, input_pdf_path: str, output_pdf_path: str, password: str) -> bool:
        """
        Protege PDF com senha
        
        Args:
            input_pdf_path: Caminho do PDF original
            output_pdf_path: Caminho do PDF protegido
            password: Senha para proteção
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            # Ler PDF original
            with open(input_pdf_path, 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                pdf_writer = PyPDF2.PdfWriter()
                
                # Copiar todas as páginas
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                # Adicionar senha (compatível com PyPDF2 1.x e 2.x)
                try:
                    # PyPDF2 >= 2.0
                    pdf_writer.encrypt(user_password=password, owner_password=None)
                except TypeError:
                    # PyPDF2 1.x
                    pdf_writer.encrypt(user_pwd=password, owner_pwd=None)
                
                # Salvar PDF protegido
                with open(output_pdf_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao proteger PDF: {e}")
            return False
    
    def process_payroll_file(self, 
                            pdf_content: bytes, 
                            matricula: str, 
                            cpf: Optional[str] = None,
                            employee_name: str = "") -> Dict:
        """
        Processa um arquivo de holerite individual
        
        Args:
            pdf_content: Conteúdo binário do PDF
            matricula: Matrícula do funcionário
            cpf: CPF do funcionário (opcional, será extraído se não fornecido)
            employee_name: Nome do funcionário
            
        Returns:
            Dict com informações do processamento
        """
        try:
            # Gerar nome do arquivo
            filename = self.format_filename(matricula)
            
            # Salvar temporariamente para processar
            temp_path = os.path.join(self.output_dir, f"temp_{filename}")
            with open(temp_path, 'wb') as f:
                f.write(pdf_content)
            
            # Extrair CPF se não fornecido
            if not cpf:
                try:
                    with open(temp_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        if len(pdf_reader.pages) > 0:
                            text = pdf_reader.pages[0].extract_text()
                            cpf = self.extract_cpf_from_text(text)
                except Exception as e:
                    print(f"⚠️ Erro ao extrair CPF: {e}")
            
            # Gerar senha
            password = self.get_cpf_password(cpf) if cpf else "0000"
            
            # Caminho final
            final_path = os.path.join(self.output_dir, filename)
            
            # Proteger com senha
            success = self.protect_pdf_with_password(temp_path, final_path, password)
            
            # Remover arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if success:
                return {
                    "success": True,
                    "filename": filename,
                    "filepath": final_path,
                    "matricula": self.remove_leading_zeros(matricula),
                    "cpf": cpf,
                    "password": password,
                    "employee_name": employee_name,
                    "folder": os.path.basename(self.output_dir)
                }
            else:
                return {
                    "success": False,
                    "error": "Falha ao proteger PDF com senha"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _copy_to_legacy_folder(self, source_path: str, matricula: str, cpf: Optional[str]) -> None:
        """Copia arquivo para pasta antiga (holerites_formatados_final) para compatibilidade"""
        try:
            import shutil
            
            # Pasta antiga
            legacy_dir = os.path.join(os.path.dirname(self.base_dir), 'holerites_formatados_final')
            os.makedirs(legacy_dir, exist_ok=True)
            
            # Nome no formato antigo: MATRICULA_holerite_mes_ano.pdf
            # Manter zeros à esquerda para compatibilidade
            month_names = {
                1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
                5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
                9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
            }
            month_name = month_names.get(self.month, 'desconhecido')
            legacy_filename = f"{matricula}_holerite_{month_name}_{self.year}.pdf"
            legacy_path = os.path.join(legacy_dir, legacy_filename)
            
            # Copiar arquivo
            shutil.copy2(source_path, legacy_path)
            print(f"📋 Copiado para envio: {legacy_filename}")
            
        except Exception as e:
            print(f"⚠️ Erro ao copiar para pasta antiga: {e}")
    
    def get_export_info(self) -> Dict:
        """Retorna informações sobre o lote processado"""
        files = []
        if os.path.exists(self.output_dir):
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.pdf') and filename.startswith('EN_'):
                    filepath = os.path.join(self.output_dir, filename)
                    files.append({
                        "filename": filename,
                        "size": os.path.getsize(filepath),
                        "created_at": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    })
        
        return {
            "payroll_type": self.payroll_type,
            "type_name": self.PAYROLL_TYPES[self.payroll_type],
            "month": self.month,
            "year": self.year,
            "folder": os.path.basename(self.output_dir),
            "total_files": len(files),
            "files": files
        }


def segment_pdf_by_employee(pdf_path: str, 
                            employees_data: List[Dict],
                            payroll_type: str,
                            month: int,
                            year: int) -> Dict:
    """
    Segmenta PDF único em múltiplos PDFs individuais (agrupando páginas do mesmo colaborador)
    
    Args:
        pdf_path: Caminho do PDF com todos os holerites
        employees_data: Lista de dados dos funcionários
        payroll_type: Tipo do holerite
        month: Mês de competência
        year: Ano de competência
        
    Returns:
        Dict com resultado do processamento
    """
    formatter = PayrollFormatter(payroll_type, month, year)
    
    processed_files = []
    errors = []
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            print(f"📄 PDF tem {total_pages} páginas")
            
            # ========== FASE 1: ANALISAR TODAS AS PÁGINAS ==========
            page_info = []
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Extrair matrícula completa (empresa + cadastro) do PDF
                extracted_matricula = formatter.extract_empresa_cadastro_from_text(text)
                
                # Extrair CPF do texto
                cpf = formatter.extract_cpf_from_text(text)
                
                # Buscar funcionário correspondente
                employee = None
                
                # Primeiro: tentar buscar pela matrícula extraída
                if extracted_matricula:
                    for emp in employees_data:
                        emp_unique_id = emp.get('unique_id', '')
                        if formatter.remove_leading_zeros(emp_unique_id) == formatter.remove_leading_zeros(extracted_matricula):
                            employee = emp
                            break
                
                # Segundo: se não encontrou, tentar por CPF
                if not employee and cpf:
                    for emp in employees_data:
                        emp_cpf = emp.get('cpf', '').replace('.', '').replace('-', '')
                        if emp_cpf == cpf:
                            employee = emp
                            break
                
                # Usar matrícula extraída do PDF ou fallback
                matricula = extracted_matricula if extracted_matricula else (employee.get('unique_id') if employee else f'UNKNOWN_{page_num + 1}')
                name = employee.get('full_name', 'Não identificado') if employee else 'Não identificado'
                
                page_info.append({
                    'page_index': page_num,
                    'page': page,
                    'matricula': matricula,
                    'cpf': cpf,
                    'employee_name': name
                })
                
                print(f"📄 Página {page_num + 1}: {name} (Matrícula: {formatter.remove_leading_zeros(matricula)})")
            
            # ========== FASE 2: AGRUPAR PÁGINAS DO MESMO COLABORADOR ==========
            grouped_pages = {}
            
            for info in page_info:
                matricula = info['matricula']
                
                # Se já existe um grupo para esta matrícula, adicionar página
                if matricula in grouped_pages:
                    grouped_pages[matricula]['pages'].append(info['page'])
                    grouped_pages[matricula]['page_numbers'].append(info['page_index'] + 1)
                else:
                    # Criar novo grupo
                    grouped_pages[matricula] = {
                        'pages': [info['page']],
                        'page_numbers': [info['page_index'] + 1],
                        'cpf': info['cpf'],
                        'employee_name': info['employee_name']
                    }
            
            # ========== FASE 3: CRIAR PDFs AGRUPADOS ==========
            for matricula, group_data in grouped_pages.items():
                try:
                    pages = group_data['pages']
                    cpf = group_data['cpf']
                    name = group_data['employee_name']
                    page_numbers = group_data['page_numbers']
                    
                    # Criar PDF com todas as páginas do colaborador
                    pdf_writer = PyPDF2.PdfWriter()
                    for page in pages:
                        pdf_writer.add_page(page)
                    
                    # Converter para bytes
                    output_buffer = BytesIO()
                    pdf_writer.write(output_buffer)
                    pdf_content = output_buffer.getvalue()
                    output_buffer.close()
                    
                    # Processar e salvar
                    result = formatter.process_payroll_file(
                        pdf_content=pdf_content,
                        matricula=matricula,
                        cpf=cpf,
                        employee_name=name
                    )
                    
                    if result['success']:
                        processed_files.append(result)
                        page_range = f"{page_numbers[0]}" if len(page_numbers) == 1 else f"{page_numbers[0]}-{page_numbers[-1]}"
                        print(f"✅ Página(s) {page_range}: {name} - {result['filename']} ({len(pages)} página(s))")
                    else:
                        errors.append(f"Matrícula {matricula}: {result.get('error')}")
                        print(f"❌ Erro na matrícula {matricula}: {result.get('error')}")
                
                except Exception as group_error:
                    errors.append(f"Matrícula {matricula}: {str(group_error)}")
                    print(f"❌ Erro ao processar matrícula {matricula}: {group_error}")
        
        print(f"✅ Processamento concluído: {len(processed_files)} holerites gerados")
        
        return {
            "success": True,
            "processed_count": len(processed_files),
            "files": processed_files,
            "errors": errors,
            "export_info": formatter.get_export_info()
        }
        
    except Exception as e:
        print(f"❌ Erro geral no processamento: {e}")
        return {
            "success": False,
            "error": str(e),
            "processed_count": 0,
            "files": [],
            "errors": [str(e)]
        }
