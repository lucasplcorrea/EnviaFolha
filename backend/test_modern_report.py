"""
Script de teste para geração de relatórios modernos com WeasyPrint
"""
import os
import sys
from datetime import datetime

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.modern_report_generator import ModernReportGenerator

def test_modern_report():
    """Testa a geração de um relatório moderno"""
    
    # Dados de exemplo para teste
    test_data = {
        'headcount': {
            'total_employees': 150,
            'total_cost': 450000.00,
            'avg_cost': 3000.00,
            'by_sector': [
                {'sector': 'Administrativo', 'count': 30, 'cost': 120000, 'percentage': 20.0},
                {'sector': 'Vendas', 'count': 45, 'cost': 135000, 'percentage': 30.0},
                {'sector': 'Operações', 'count': 50, 'cost': 150000, 'percentage': 33.33},
                {'sector': 'TI', 'count': 25, 'cost': 45000, 'percentage': 16.67},
            ]
        },
        'overview': {
            'total_employees': 150,
            'admissions': 12,
            'terminations': 8,
            'turnover_rate': 6.67,
            'total_leaves': 5,
            'admission_rate': 8.0,
            'termination_rate': 5.33,
            'leave_rate': 3.33,
            'by_sector': [
                {'sector': 'Administrativo', 'count': 30, 'admissions': 3, 'terminations': 2, 'turnover_rate': 6.67},
                {'sector': 'Vendas', 'count': 45, 'admissions': 5, 'terminations': 3, 'turnover_rate': 7.41},
                {'sector': 'Operações', 'count': 50, 'admissions': 3, 'terminations': 2, 'turnover_rate': 4.0},
                {'sector': 'TI', 'count': 25, 'admissions': 1, 'terminations': 1, 'turnover_rate': 4.0},
            ]
        },
        'turnover': {
            'avg_rate': 6.5,
            'total_admissions': 36,
            'total_terminations': 24,
            'net_change': 12,
            'by_month': [
                {'month_name': 'Janeiro', 'initial_headcount': 140, 'admissions': 3, 'terminations': 2, 'final_headcount': 141, 'rate': 7.14},
                {'month_name': 'Fevereiro', 'initial_headcount': 141, 'admissions': 4, 'terminations': 2, 'final_headcount': 143, 'rate': 6.99},
                {'month_name': 'Março', 'initial_headcount': 143, 'admissions': 5, 'terminations': 4, 'final_headcount': 144, 'rate': 6.29},
            ]
        },
        'demographics': {
            'by_gender': [
                {'gender': 'Masculino', 'count': 90, 'percentage': 60.0},
                {'gender': 'Feminino', 'count': 60, 'percentage': 40.0},
            ],
            'by_age': [
                {'age_range': '18-25', 'count': 30, 'percentage': 20.0},
                {'age_range': '26-35', 'count': 60, 'percentage': 40.0},
                {'age_range': '36-45', 'count': 40, 'percentage': 26.67},
                {'age_range': '46-55', 'count': 15, 'percentage': 10.0},
                {'age_range': '56+', 'count': 5, 'percentage': 3.33},
            ],
            'avg_age_by_sector': [
                {'sector': 'TI', 'avg_age': 28},
                {'sector': 'Vendas', 'avg_age': 32},
                {'sector': 'Operações', 'avg_age': 35},
                {'sector': 'Administrativo', 'avg_age': 38},
            ]
        },
        'tenure': {
            'avg_tenure_years': 3.5,
            'avg_tenure_months': 42,
            'median_tenure_months': 36,
            'longest_tenure': 15,
            'newest_employees': 25,
            'total_employees': 150,
            'by_range': [
                {'range': '0-6 meses', 'count': 25, 'percentage': 16.67},
                {'range': '6-12 meses', 'count': 20, 'percentage': 13.33},
                {'range': '1-3 anos', 'count': 45, 'percentage': 30.0},
                {'range': '3-5 anos', 'count': 35, 'percentage': 23.33},
                {'range': '5-10 anos', 'count': 20, 'percentage': 13.33},
                {'range': '10+ anos', 'count': 5, 'percentage': 3.33},
            ]
        },
        'leaves': {
            'total_leaves': 15,
            'leave_rate': 10.0,
            'avg_duration': 12,
            'total_days': 180,
            'most_common_type': 'Licença Médica',
            'by_type': [
                {'type': 'Licença Médica', 'count': 8, 'percentage': 53.33, 'total_days': 120, 'avg_days': 15},
                {'type': 'Licença Maternidade', 'count': 4, 'percentage': 26.67, 'total_days': 480, 'avg_days': 120},
                {'type': 'Acidente de Trabalho', 'count': 2, 'percentage': 13.33, 'total_days': 60, 'avg_days': 30},
                {'type': 'Outros', 'count': 1, 'percentage': 6.67, 'total_days': 10, 'avg_days': 10},
            ],
            'by_sector': [
                {'sector': 'Operações', 'count': 8, 'total_employees': 50, 'rate': 16.0},
                {'sector': 'Vendas', 'count': 4, 'total_employees': 45, 'rate': 8.89},
                {'sector': 'Administrativo', 'count': 2, 'total_employees': 30, 'rate': 6.67},
                {'sector': 'TI', 'count': 1, 'total_employees': 25, 'rate': 4.0},
            ]
        },
        'payroll': {
            'total_gross': 600000.00,
            'total_net': 450000.00,
            'avg_gross': 4000.00,
            'avg_net': 3000.00,
            'total_benefits': 75000.00,
            'total_employees': 150,
            'by_sector': [
                {'sector': 'TI', 'count': 25, 'total_gross': 200000, 'total_net': 150000, 'avg_gross': 8000, 'avg_net': 6000, 'percentage': 33.33},
                {'sector': 'Vendas', 'count': 45, 'total_gross': 180000, 'total_net': 135000, 'avg_gross': 4000, 'avg_net': 3000, 'percentage': 30.0},
                {'sector': 'Operações', 'count': 50, 'total_gross': 150000, 'total_net': 112500, 'avg_gross': 3000, 'avg_net': 2250, 'percentage': 25.0},
                {'sector': 'Administrativo', 'count': 30, 'total_gross': 70000, 'total_net': 52500, 'avg_gross': 2333, 'avg_net': 1750, 'percentage': 11.67},
            ],
            'by_salary_range': [
                {'range': 'Até R$ 2.000', 'count': 30, 'percentage': 20.0},
                {'range': 'R$ 2.001 - R$ 4.000', 'count': 60, 'percentage': 40.0},
                {'range': 'R$ 4.001 - R$ 6.000', 'count': 35, 'percentage': 23.33},
                {'range': 'R$ 6.001 - R$ 10.000', 'count': 20, 'percentage': 13.33},
                {'range': 'Acima de R$ 10.000', 'count': 5, 'percentage': 3.33},
            ]
        }
    }
    
    # Informações de teste
    user_info = {
        'name': 'João Silva',
        'email': 'joao.silva@nexorh.com.br'
    }
    
    # Criar gerador (sem DB para teste)
    generator = ModernReportGenerator(None)
    
    # Testar diferentes tipos de relatório
    report_types = [
        ('overview', ['overview', 'headcount']),
        ('headcount', ['headcount']),
        ('turnover', ['turnover']),
        ('demographics', ['demographics']),
        ('tenure', ['tenure']),
        ('leaves', ['leaves']),
        ('payroll', ['payroll']),
        ('complete', ['overview', 'headcount', 'turnover', 'demographics', 'tenure', 'leaves', 'payroll'])
    ]
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'test_reports')
    os.makedirs(output_dir, exist_ok=True)
    
    for report_name, sections in report_types:
        try:
            print(f"\n{'='*60}")
            print(f"📊 Gerando relatório: {report_name}")
            print(f"📋 Seções: {', '.join(sections)}")
            
            pdf_bytes = generator.generate_report(
                report_type=report_name,
                sections=sections,
                year=2024,
                month=12,
                months_range=3,
                company='Nexo RH',
                division='Todas',
                data=test_data,
                user_info=user_info
            )
            
            # Salvar PDF
            output_path = os.path.join(output_dir, f'test_{report_name}.pdf')
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"✅ Relatório gerado com sucesso!")
            print(f"📁 Salvo em: {output_path}")
            print(f"📏 Tamanho: {len(pdf_bytes):,} bytes")
            
        except Exception as e:
            print(f"❌ Erro ao gerar relatório {report_name}:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"✨ Teste concluído!")
    print(f"📂 Relatórios salvos em: {output_dir}")

if __name__ == '__main__':
    test_modern_report()
