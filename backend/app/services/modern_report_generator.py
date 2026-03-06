"""
Modern Report Generator Service - HTML + Jinja2 + Pygal
Nexo RH - Sistema de Gestão de Recursos Humanos
Generates beautiful HTML reports that can be printed to PDF from browser
"""
import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
import pygal
from pygal.style import Style

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ModernReportGenerator:
    """Modern HTML report generator using Jinja2 and Pygal - Renders to HTML for browser print"""
    
    # Custom Pygal style matching our color scheme
    NEXO_STYLE = Style(
        background='transparent',
        plot_background='transparent',
        foreground='#1F2937',
        foreground_strong='#111827',
        foreground_subtle='#6B7280',
        colors=(
            '#4F46E5',  # Indigo
            '#10B981',  # Green
            '#F59E0B',  # Amber
            '#EF4444',  # Red
            '#3B82F6',  # Blue
            '#8B5CF6',  # Purple
            '#EC4899',  # Pink
            '#06B6D4',  # Cyan
            '#F97316',  # Orange
            '#6B7280',  # Gray
        ),
        font_family='Segoe UI, Roboto, sans-serif',
        label_font_size=10,
        major_label_font_size=11,
        value_font_size=12,
        title_font_size=14,
    )
    
    MONTH_NAMES = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    REPORT_NAMES = {
        'consolidated': 'Relatório Consolidado',
        'headcount': 'Relatório de Efetivo',
        'turnover': 'Relatório de Rotatividade',
        'demographics': 'Relatório Demográfico',
        'tenure': 'Relatório de Tempo de Casa',
        'leaves': 'Relatório de Afastamentos',
        'payroll': 'Relatório de Folha de Pagamento',
        'custom': 'Relatório Customizado'
    }
    
    def __init__(self, db: Session):
        self.db = db
        
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Register custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['percentage'] = self._format_percentage
    
    def _format_currency(self, value: float) -> str:
        """Format number as Brazilian currency"""
        if value is None or value == '':
            return "R$ 0,00"
        try:
            return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return "R$ 0,00"
    
    def _format_percentage(self, value: float, decimals: int = 2) -> str:
        """Format value as percentage"""
        if value is None or value == '':
            return "0,00"
        try:
            return f"{float(value):.{decimals}f}".replace('.', ',')
        except (ValueError, TypeError):
            return "0,00"
    
    def _create_pie_chart(self, data: List[Dict], value_key: str, label_key: str, 
                          title: str = '') -> str:
        """Create a Pygal pie chart and return as SVG string"""
        pie_chart = pygal.Pie(
            style=self.NEXO_STYLE,
            title=title,
            print_values=False,
            print_labels=True,
            show_legend=True,
            legend_at_bottom=True,
            legend_font_size=10,
            height=250,
            width=400,
            inner_radius=0.4,  # Donut style
        )
        
        for item in data:
            label = item.get(label_key, 'N/A')
            value = item.get(value_key, 0)
            total = sum(d.get(value_key, 0) for d in data)
            pct = (value / total * 100) if total > 0 else 0
            pie_chart.add(f'{label} ({pct:.1f}%)', value)
        
        return pie_chart.render().decode('utf-8')
    
    def _create_bar_chart(self, data: List[Dict], value_key: str, label_key: str,
                          title: str = '', horizontal: bool = False) -> str:
        """Create a Pygal bar chart and return as SVG string"""
        ChartClass = pygal.HorizontalBar if horizontal else pygal.Bar
        
        bar_chart = ChartClass(
            style=self.NEXO_STYLE,
            title=title,
            print_values=True,
            print_labels=True,
            show_legend=False,
            height=300,
            width=600,
            x_label_rotation=30 if not horizontal else 0,
        )
        
        labels = [item.get(label_key, 'N/A')[:25] for item in data]
        values = [item.get(value_key, 0) for item in data]
        
        bar_chart.x_labels = labels
        bar_chart.add('', values)
        
        return bar_chart.render().decode('utf-8')
    
    def _create_line_chart(self, data: List[Dict], value_keys: List[str], 
                           label_key: str, legend_labels: List[str] = None,
                           title: str = '') -> str:
        """Create a Pygal line chart and return as SVG string"""
        line_chart = pygal.Line(
            style=self.NEXO_STYLE,
            title=title,
            show_dots=True,
            show_legend=True,
            legend_at_bottom=True,
            height=300,
            width=700,
            x_label_rotation=30,
        )
        
        labels = [item.get(label_key, '') for item in data]
        line_chart.x_labels = labels
        
        for i, key in enumerate(value_keys):
            values = [item.get(key, 0) for item in data]
            label = legend_labels[i] if legend_labels and i < len(legend_labels) else key
            line_chart.add(label, values)
        
        return line_chart.render().decode('utf-8')
    
    def generate_report(
        self,
        report_type: str,
        sections: List[str],
        year: int,
        month: int,
        months_range: int = 6,
        company: Optional[str] = None,
        division: Optional[str] = None,
        data: Dict[str, Any] = None,
        user_info: Optional[Dict] = None
    ) -> bytes:
        """
        Generate modern PDF report with specified sections
        
        Args:
            report_type: Type of report
            sections: List of sections to include
            year: Reference year
            month: Reference month
            months_range: Number of months for evolution charts
            company: Filter by company code
            division: Filter by division
            data: Pre-fetched data
            user_info: User who generated the report
        
        Returns:
            PDF file as bytes
        """
        # Prepare context for template
        month_name = self.MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month)
        
        company_names = {'0059': 'Infraestrutura', '0060': 'Empreendimentos'}
        company_display = company_names.get(company, company) if company else 'Todas as empresas'
        division_display = division if division else 'Todos os setores'
        
        now = datetime.now()
        
        context = {
            'title': self.REPORT_NAMES.get(report_type, 'Relatório de RH'),
            'period_text': f'{month_name} de {year}',
            'period_display': f'{month_name}/{year}',
            'month_name': month_name,
            'year': year,
            'company_name': company_display,
            'division_name': division_display,
            'generation_date': now.strftime('%d/%m/%Y'),
            'generation_time': now.strftime('%H:%M:%S'),
            'user_name': user_info.get('name', 'Sistema Nexo RH') if user_info else 'Sistema Nexo RH',
            'user_email': user_info.get('email', '') if user_info else '',
            'sections': sections,
        }
        
        # Add data sections directly to context (not nested in 'data')
        if data:
            for section_name, section_data in data.items():
                context[section_name] = section_data
        
        # Generate charts and add to context
        context['charts'] = self._generate_charts(data, sections)
        
        # Render HTML template
        template = self.jinja_env.get_template('reports/report.html')
        html_content = template.render(**context)
        
        # Return HTML directly - browser will handle print/PDF
        logger.info(f"HTML report generated: {len(html_content):,} characters")
        
        return html_content
    
    def _generate_charts(self, data: Dict[str, Any], sections: List[str]) -> Dict[str, str]:
        """Generate all charts for the report sections"""
        charts = {}
        
        if not data:
            return charts
        
        # Headcount charts
        if 'headcount' in sections and 'headcount' in data:
            by_dept = data['headcount'].get('current', {}).get('by_department', [])
            if by_dept:
                top_depts = sorted(by_dept, key=lambda x: x.get('count', 0), reverse=True)[:10]
                charts['headcount_bar'] = self._create_bar_chart(
                    top_depts, 'count', 'department', 
                    title='Top 10 Setores por Efetivo'
                )
        
        # Turnover charts
        if 'turnover' in sections and 'turnover' in data:
            evolution = data['turnover'].get('evolution', [])
            if evolution and len(evolution) > 1:
                charts['turnover_line'] = self._create_line_chart(
                    evolution[-6:], 
                    ['admissions', 'terminations'],
                    'period',
                    ['Admissões', 'Demissões'],
                    title='Evolução de Admissões e Demissões'
                )
        
        # Demographics charts
        if 'demographics' in sections and 'demographics' in data:
            current = data['demographics'].get('current', {})
            
            by_gender = current.get('by_gender', [])
            if by_gender:
                charts['demographics_gender_pie'] = self._create_pie_chart(
                    by_gender, 'count', 'gender', title='Distribuição por Gênero'
                )
            
            by_age = current.get('by_age_range', [])
            if by_age:
                charts['demographics_age_pie'] = self._create_pie_chart(
                    by_age, 'count', 'age_range', title='Distribuição por Faixa Etária'
                )
        
        # Tenure charts
        if 'tenure' in sections and 'tenure' in data:
            by_range = data['tenure'].get('current', {}).get('by_tenure_range', [])
            if by_range:
                charts['tenure_bar'] = self._create_bar_chart(
                    by_range, 'count', 'range',
                    title='Distribuição por Tempo de Casa',
                    horizontal=True
                )
        
        # Leaves charts
        if 'leaves' in sections and 'leaves' in data:
            by_type = data['leaves'].get('current', {}).get('by_type', [])
            if by_type:
                top_types = sorted(by_type, key=lambda x: x.get('count', 0), reverse=True)[:8]
                charts['leaves_pie'] = self._create_pie_chart(
                    top_types, 'count', 'type', title='Distribuição por Tipo de Afastamento'
                )
        
        # Payroll charts
        if 'payroll' in sections and 'payroll' in data:
            by_dept = data['payroll'].get('current', {}).get('by_department', [])
            if by_dept:
                top_depts = sorted(by_dept, key=lambda x: x.get('total_net', 0), reverse=True)[:10]
                charts['payroll_bar'] = self._create_bar_chart(
                    top_depts, 'total_net', 'department',
                    title='Top 10 Setores - Valor Líquido'
                )
        
        return charts
