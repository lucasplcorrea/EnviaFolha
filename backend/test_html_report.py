"""
Teste rápido do gerador de relatórios HTML modernos
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.modern_report_generator import ModernReportGenerator
import webbrowser
import tempfile

def test_html_report():
    """Testa a geração de relatório HTML com dados de exemplo"""
    
    # Dados de exemplo
    test_data = {
        'headcount': {
            'total_employees': 448,
            'total_cost': 1500000.00,
            'avg_cost': 3348.21,
            'by_sector': [
                {'sector': 'Administrativo', 'count': 85, 'cost': 340000, 'percentage': 18.97},
                {'sector': 'Vendas', 'count': 120, 'cost': 480000, 'percentage': 26.79},
                {'sector': 'Operações', 'count': 180, 'cost': 540000, 'percentage': 40.18},
                {'sector': 'TI', 'count': 63, 'cost': 140000, 'percentage': 14.06},
            ]
        },
        'overview': {
            'total_employees': 448,
            'admissions': 35,
            'terminations': 22,
            'turnover_rate': 6.36,
            'total_leaves': 18,
            'admission_rate': 7.81,
            'termination_rate': 4.91,
            'leave_rate': 4.02,
            'by_sector': [
                {'sector': 'Administrativo', 'count': 85, 'admissions': 8, 'terminations': 5, 'turnover_rate': 7.65},
                {'sector': 'Vendas', 'count': 120, 'admissions': 12, 'terminations': 8, 'turnover_rate': 8.33},
                {'sector': 'Operações', 'count': 180, 'admissions': 11, 'terminations': 7, 'turnover_rate': 5.0},
                {'sector': 'TI', 'count': 63, 'admissions': 4, 'terminations': 2, 'turnover_rate': 4.76},
            ]
        }
    }
    
    user_info = {
        'name': 'João Silva',
        'email': 'joao.silva@nexorh.com.br'
    }
    
    print("\n" + "="*60)
    print("🚀 Teste de Relatório HTML Moderno - Nexo RH")
    print("="*60 + "\n")
    
    # Criar gerador
    generator = ModernReportGenerator(None)
    
    # Gerar HTML
    print("📊 Gerando relatório de Visão Geral...")
    html_content = generator.generate_report(
        report_type='overview',
        sections=['overview', 'headcount'],
        year=2024,
        month=12,
        months_range=3,
        company='Nexo RH',
        division='Todas',
        data=test_data,
        user_info=user_info
    )
    
    # Salvar arquivo temporário
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, 'NexoRH_Teste_Dez_2024.html')
    
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Relatório HTML gerado com sucesso!")
    print(f"📁 Arquivo: {temp_path}")
    print(f"📏 Tamanho: {len(html_content):,} caracteres")
    print(f"\n🌐 Abrindo no navegador...")
    print(f"💡 Dica: Use Ctrl+P para imprimir ou salvar como PDF\n")
    
    # Abrir no navegador
    webbrowser.open(f'file:///{temp_path}')
    
    print("="*60)
    print("✨ Teste concluído! Verifique o navegador.")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_html_report()
