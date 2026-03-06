"""
Report Generator Service - PDF Generation with ReportLab
Nexo RH - Sistema de Gestão de Recursos Humanos
"""
import io
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Service for generating PDF reports with HR indicators - Nexo RH"""
    
    # Cores da paleta
    COLORS = {
        'primary': colors.HexColor('#4F46E5'),     # Indigo
        'secondary': colors.HexColor('#6366F1'),
        'success': colors.HexColor('#10B981'),     # Green
        'warning': colors.HexColor('#F59E0B'),     # Amber
        'danger': colors.HexColor('#EF4444'),      # Red
        'info': colors.HexColor('#3B82F6'),        # Blue
        'gray': colors.HexColor('#6B7280'),
        'light_gray': colors.HexColor('#F3F4F6'),
        'dark': colors.HexColor('#1F2937'),
        'emerald': colors.HexColor('#059669'),
        'purple': colors.HexColor('#7C3AED'),
        'pink': colors.HexColor('#EC4899'),
        'cyan': colors.HexColor('#06B6D4'),
        'orange': colors.HexColor('#F97316'),
    }
    
    # Cores para gráficos (sequência harmoniosa)
    CHART_COLORS = [
        colors.HexColor('#4F46E5'),  # Indigo
        colors.HexColor('#10B981'),  # Green
        colors.HexColor('#F59E0B'),  # Amber
        colors.HexColor('#EF4444'),  # Red
        colors.HexColor('#3B82F6'),  # Blue
        colors.HexColor('#8B5CF6'),  # Purple
        colors.HexColor('#EC4899'),  # Pink
        colors.HexColor('#06B6D4'),  # Cyan
        colors.HexColor('#F97316'),  # Orange
        colors.HexColor('#6B7280'),  # Gray
    ]
    
    MONTH_NAMES = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configure custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title_Custom',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLORS['primary'],
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLORS['gray'],
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='Section',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.COLORS['primary'],
            spaceBefore=20,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='Subsection',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=self.COLORS['dark'],
            spaceBefore=15,
            spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name='BodyText_Custom',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLORS['dark'],
            spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name='Metric',
            parent=self.styles['Normal'],
            fontSize=28,
            textColor=self.COLORS['primary'],
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLORS['gray'],
            alignment=TA_CENTER
        ))
    
    # ==================== CHART HELPERS ====================
    
    def _create_pie_chart(self, data: List[Dict], value_key: str, label_key: str, 
                          title: str = '', width: int = 250, height: int = 180) -> Drawing:
        """Create a pie chart with legend"""
        drawing = Drawing(width, height)
        
        # Extract values and labels
        values = [item.get(value_key, 0) for item in data if item.get(value_key, 0) > 0]
        labels = [item.get(label_key, 'N/A') for item in data if item.get(value_key, 0) > 0]
        
        if not values:
            return drawing
        
        # Create pie chart
        pie = Pie()
        pie.x = 30
        pie.y = 10
        pie.width = 120
        pie.height = 120
        pie.data = values
        pie.labels = None  # We'll use legend instead
        
        # Apply colors
        for i, _ in enumerate(values):
            pie.slices[i].fillColor = self.CHART_COLORS[i % len(self.CHART_COLORS)]
            pie.slices[i].strokeWidth = 0.5
            pie.slices[i].strokeColor = colors.white
        
        drawing.add(pie)
        
        # Add legend
        legend = Legend()
        legend.x = 165
        legend.y = height - 20
        legend.dx = 8
        legend.dy = 8
        legend.fontName = 'Helvetica'
        legend.fontSize = 8
        legend.boxAnchor = 'nw'
        legend.columnMaximum = 10
        legend.strokeWidth = 0.5
        legend.strokeColor = self.COLORS['light_gray']
        legend.deltax = 75
        legend.deltay = 12
        legend.autoXPadding = 5
        legend.yGap = 0
        legend.dxTextSpace = 5
        legend.alignment = 'right'
        legend.dividerLines = 1|2|4
        legend.dividerOffsY = 4.5
        legend.subCols.rpad = 30
        
        # Create legend entries with percentages
        total = sum(values)
        legend_items = []
        for i, (label, value) in enumerate(zip(labels, values)):
            pct = (value / total * 100) if total > 0 else 0
            display_label = label[:20] + '...' if len(label) > 20 else label
            legend_items.append((self.CHART_COLORS[i % len(self.CHART_COLORS)], f'{display_label} ({pct:.1f}%)'))
        
        legend.colorNamePairs = legend_items
        drawing.add(legend)
        
        return drawing
    
    def _create_bar_chart(self, data: List[Dict], value_key: str, label_key: str,
                          title: str = '', width: int = 400, height: int = 180,
                          bar_color: colors.Color = None) -> Drawing:
        """Create a vertical bar chart"""
        drawing = Drawing(width, height)
        
        values = [item.get(value_key, 0) for item in data[:8]]  # Max 8 bars
        labels = [item.get(label_key, '')[:12] for item in data[:8]]
        
        if not values:
            return drawing
        
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 30
        chart.width = width - 80
        chart.height = height - 60
        chart.data = [values]
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.angle = 30
        chart.categoryAxis.labels.boxAnchor = 'ne'
        chart.categoryAxis.labels.fontSize = 7
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labels.fontSize = 8
        chart.barWidth = 20
        chart.groupSpacing = 15
        
        # Apply color
        color = bar_color or self.COLORS['primary']
        chart.bars[0].fillColor = color
        chart.bars[0].strokeColor = color
        
        drawing.add(chart)
        
        return drawing
    
    def _create_line_chart(self, data: List[Dict], value_keys: List[str], 
                           label_key: str, legend_labels: List[str] = None,
                           width: int = 450, height: int = 180) -> Drawing:
        """Create a line chart for evolution data"""
        drawing = Drawing(width, height)
        
        labels = [item.get(label_key, '') for item in data]
        
        if not labels or not data:
            return drawing
        
        # Prepare data series
        chart_data = []
        for key in value_keys:
            series = [item.get(key, 0) for item in data]
            chart_data.append(series)
        
        if not chart_data or not chart_data[0]:
            return drawing
        
        chart = HorizontalLineChart()
        chart.x = 50
        chart.y = 30
        chart.width = width - 100
        chart.height = height - 60
        chart.data = chart_data
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.angle = 30
        chart.categoryAxis.labels.boxAnchor = 'ne'
        chart.categoryAxis.labels.fontSize = 8
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labels.fontSize = 8
        chart.joinedLines = 1
        
        # Style lines
        for i in range(len(value_keys)):
            chart.lines[i].strokeColor = self.CHART_COLORS[i % len(self.CHART_COLORS)]
            chart.lines[i].strokeWidth = 2
            chart.lines[i].symbol = makeMarker('Circle')
            chart.lines[i].symbol.size = 4
        
        drawing.add(chart)
        
        # Add legend if multiple series
        if legend_labels and len(value_keys) > 1:
            legend = Legend()
            legend.x = width - 100
            legend.y = height - 20
            legend.fontSize = 8
            legend.colorNamePairs = [(self.CHART_COLORS[i], legend_labels[i]) for i in range(len(legend_labels))]
            drawing.add(legend)
        
        return drawing

    # ==================== REPORT GENERATION ====================
    
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
        Generate PDF report with specified sections
        
        Args:
            report_type: Type of report (consolidated, headcount, etc.)
            sections: List of sections to include
            year: Reference year
            month: Reference month
            months_range: Number of months for evolution charts
            company: Filter by company code (optional)
            division: Filter by division (optional)
            data: Pre-fetched data from endpoints (optional)
            user_info: Information about the user generating the report (optional)
        
        Returns:
            PDF file as bytes
        """
        # Store info for page headers/footers
        self.report_info = {
            'report_type': report_type,
            'year': year,
            'month': month,
            'company': company,
            'division': division,
            'user_info': user_info
        }
        
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2*cm
        )
        
        # Build document content
        story = []
        
        # Header / Title Page
        story.extend(self._build_title_page(report_type, year, month, company, division, user_info))
        
        # Add sections based on request
        for section in sections:
            if section == 'overview' and data and 'overview' in data:
                story.extend(self._build_overview_section(data['overview']))
            elif section == 'headcount' and data and 'headcount' in data:
                story.extend(self._build_headcount_section(data['headcount']))
            elif section == 'turnover' and data and 'turnover' in data:
                story.extend(self._build_turnover_section(data['turnover']))
            elif section == 'demographics' and data and 'demographics' in data:
                story.extend(self._build_demographics_section(data['demographics']))
            elif section == 'tenure' and data and 'tenure' in data:
                story.extend(self._build_tenure_section(data['tenure']))
            elif section == 'leaves' and data and 'leaves' in data:
                story.extend(self._build_leaves_section(data['leaves']))
            elif section == 'payroll' and data and 'payroll' in data:
                story.extend(self._build_payroll_section(data['payroll']))
        
        # Footer
        story.extend(self._build_footer())
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_title_page(
        self,
        report_type: str,
        year: int,
        month: int,
        company: Optional[str],
        division: Optional[str],
        user_info: Optional[Dict] = None
    ) -> List:
        """Build report title page with filters and emission info"""
        elements = []
        
        # Spacer for centering
        elements.append(Spacer(1, 2*cm))
        
        # System name header
        elements.append(Paragraph("Nexo RH", self.styles['Title_Custom']))
        elements.append(Paragraph("Sistema de Gestão de Recursos Humanos", self.styles['BodyText_Custom']))
        elements.append(Spacer(1, 1*cm))
        
        # Report type name mapping
        report_names = {
            'consolidated': 'Relatório Consolidado',
            'headcount': 'Relatório de Efetivo',
            'turnover': 'Relatório de Rotatividade',
            'demographics': 'Relatório Demográfico',
            'tenure': 'Relatório de Tempo de Casa',
            'leaves': 'Relatório de Afastamentos',
            'payroll': 'Relatório de Folha de Pagamento',
            'custom': 'Relatório Customizado'
        }
        
        title = report_names.get(report_type, 'Relatório de RH')
        elements.append(Paragraph(title, self.styles['Section']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Period
        month_name = self.MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month)
        
        # Build filters info box
        filters_data = [
            ['FILTROS APLICADOS', ''],
            ['Período de Referência', f'{month_name} de {year}'],
        ]
        
        # Company filter
        company_names = {'0059': 'Infraestrutura', '0060': 'Empreendimentos'}
        if company:
            filters_data.append(['Empresa', company_names.get(company, company)])
        else:
            filters_data.append(['Empresa', 'Todas as empresas'])
        
        # Division filter
        if division:
            filters_data.append(['Setor/Departamento', division])
        else:
            filters_data.append(['Setor/Departamento', 'Todos os setores'])
        
        filter_table = Table(filters_data, colWidths=[6*cm, 9*cm])
        filter_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light_gray']),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
            ('BOX', (0, 0), (-1, -1), 1, self.COLORS['primary']),
        ]))
        
        elements.append(filter_table)
        elements.append(Spacer(1, 1*cm))
        
        # Emission info box
        gen_date = datetime.now()
        emission_data = [
            ['INFORMAÇÕES DE EMISSÃO', ''],
            ['Data de Geração', gen_date.strftime("%d/%m/%Y")],
            ['Hora de Geração', gen_date.strftime("%H:%M:%S")],
        ]
        
        if user_info:
            emission_data.append(['Emitido por', user_info.get('name', 'Sistema')])
            if user_info.get('email'):
                emission_data.append(['E-mail', user_info.get('email')])
        else:
            emission_data.append(['Emitido por', 'Sistema Nexo RH'])
        
        emission_table = Table(emission_data, colWidths=[6*cm, 9*cm])
        emission_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['info']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light_gray']),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
            ('BOX', (0, 0), (-1, -1), 1, self.COLORS['info']),
        ]))
        
        elements.append(emission_table)
        elements.append(PageBreak())
        
        return elements
    
    def _build_overview_section(self, data: Dict) -> List:
        """Build overview section with key metrics"""
        elements = []
        
        elements.append(Paragraph("📊 Visão Geral", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        
        # Main metrics table
        metrics_data = [
            ['Indicador', 'Valor'],
            ['Total de Funcionários', str(current.get('total_employees', 0))],
            ['Admissões no Mês', str(current.get('admissions', 0))],
            ['Demissões no Mês', str(current.get('terminations', 0))],
            ['Taxa de Turnover', f"{current.get('turnover_rate', 0):.1f}%"],
            ['Funcionários Afastados', str(current.get('on_leave', 0))],
        ]
        
        table = Table(metrics_data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light_gray']),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['light_gray'], colors.white]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_headcount_section(self, data: Dict) -> List:
        """Build headcount section with chart"""
        elements = []
        
        elements.append(Paragraph("👥 Efetivo por Setor", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        by_department = current.get('by_department', [])
        
        # Summary info
        total_headcount = current.get('headcount', sum(d.get('count', 0) for d in by_department))
        elements.append(Paragraph(f"<b>Total de Funcionários: {total_headcount}</b>", self.styles['BodyText_Custom']))
        elements.append(Spacer(1, 0.5*cm))
        
        if by_department:
            # Add bar chart for top departments
            sorted_depts = sorted(by_department, key=lambda x: x.get('count', 0), reverse=True)[:10]
            
            if sorted_depts:
                elements.append(Paragraph("Distribuição por Setor (Top 10)", self.styles['Subsection']))
                bar_chart = self._create_bar_chart(
                    sorted_depts, 
                    value_key='count', 
                    label_key='department',
                    bar_color=self.COLORS['info'],
                    width=450, 
                    height=180
                )
                elements.append(bar_chart)
                elements.append(Spacer(1, 0.5*cm))
            
            # Table with departments
            elements.append(Paragraph("Detalhamento por Setor", self.styles['Subsection']))
            table_data = [['Setor', 'Quantidade', '% do Total']]
            total = sum(d.get('count', 0) for d in by_department)
            
            for dept in sorted(by_department, key=lambda x: x.get('count', 0), reverse=True):
                name = dept.get('department', 'Não informado')
                if len(name) > 35:
                    name = name[:32] + '...'
                count = dept.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                table_data.append([name, str(count), f"{pct:.1f}%"])
            
            # Total row
            table_data.append(['TOTAL', str(total), '100%'])
            
            table = Table(table_data, colWidths=[8*cm, 4*cm, 4*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['info']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, -1), (-1, -1), self.COLORS['light_gray']),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("Sem dados de efetivo por setor.", self.styles['BodyText_Custom']))
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_turnover_section(self, data: Dict) -> List:
        """Build turnover section with evolution chart"""
        elements = []
        
        elements.append(Paragraph("🔄 Rotatividade", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        evolution = data.get('evolution', [])
        
        # Current metrics cards (in a table for visual appeal)
        metrics_data = [
            ['Admissões no Mês', 'Demissões no Mês', 'Taxa de Turnover'],
            [str(current.get('admissions', 0)), str(current.get('terminations', 0)), f"{current.get('turnover_rate', 0):.2f}%"],
        ]
        
        table = Table(metrics_data, colWidths=[5*cm, 5*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), self.COLORS['success']),
            ('BACKGROUND', (1, 0), (1, 0), self.COLORS['danger']),
            ('BACKGROUND', (2, 0), (2, 0), self.COLORS['warning']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 16),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light_gray']),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Evolution chart
        if evolution and len(evolution) > 1:
            elements.append(Paragraph("Evolução de Admissões e Demissões", self.styles['Subsection']))
            
            # Create line chart
            line_chart = self._create_line_chart(
                evolution[-6:],  # Last 6 months
                value_keys=['admissions', 'terminations'],
                label_key='period',
                legend_labels=['Admissões', 'Demissões'],
                width=450,
                height=180
            )
            elements.append(line_chart)
            elements.append(Spacer(1, 0.5*cm))
        
        # Evolution table
        if evolution:
            elements.append(Paragraph("Detalhamento Mensal", self.styles['Subsection']))
            
            evol_data = [['Período', 'Efetivo', 'Admissões', 'Demissões', 'Turnover']]
            for item in evolution[-6:]:  # Last 6 months
                period = item.get('period', '')
                headcount = item.get('headcount', 0)
                adm = item.get('admissions', 0)
                term = item.get('terminations', 0)
                rate = item.get('turnover_rate', 0)
                evol_data.append([period, str(headcount), str(adm), str(term), f"{rate:.2f}%"])
            
            evol_table = Table(evol_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm, 3*cm])
            evol_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['light_gray']),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(evol_table)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_demographics_section(self, data: Dict) -> List:
        """Build demographics section"""
        elements = []
        
        elements.append(Paragraph("📊 Perfil Demográfico", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        total_employees = current.get('total_employees', 0)
        
        if total_employees:
            elements.append(Paragraph(f"<b>Total de Funcionários Analisados: {total_employees}</b>", self.styles['BodyText_Custom']))
            elements.append(Spacer(1, 0.3*cm))
        
        # Gender distribution
        by_gender = current.get('by_gender', [])
        if by_gender:
            elements.append(Paragraph("Distribuição por Gênero", self.styles['Subsection']))
            
            # Create side-by-side: pie chart + table
            pie_chart = self._create_pie_chart(
                by_gender,
                value_key='count',
                label_key='gender',
                width=260,
                height=160
            )
            
            gender_data = [['Gênero', 'Qtd', '%']]
            total = sum(g.get('count', 0) for g in by_gender)
            
            for item in by_gender:
                gender = item.get('gender', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                gender_data.append([gender, str(count), f"{pct:.1f}%"])
            
            mini_table = Table(gender_data, colWidths=[4*cm, 2*cm, 2*cm])
            mini_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['success']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            # Combine chart and table
            combined = Table([[pie_chart, mini_table]], colWidths=[9*cm, 7*cm])
            combined.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ]))
            elements.append(combined)
            elements.append(Spacer(1, 0.5*cm))
        
        # Age distribution
        by_age = current.get('by_age_range', [])
        if by_age:
            elements.append(Paragraph("Distribuição por Faixa Etária", self.styles['Subsection']))
            
            # Pie chart for age
            pie_chart = self._create_pie_chart(
                by_age,
                value_key='count',
                label_key='age_range',
                width=260,
                height=160
            )
            
            age_data = [['Faixa', 'Qtd', '%']]
            total = sum(a.get('count', 0) for a in by_age)
            
            for item in by_age:
                age_range = item.get('age_range', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                age_data.append([age_range, str(count), f"{pct:.1f}%"])
            
            mini_table = Table(age_data, colWidths=[4*cm, 2*cm, 2*cm])
            mini_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['info']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            combined = Table([[pie_chart, mini_table]], colWidths=[9*cm, 7*cm])
            combined.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ]))
            elements.append(combined)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_tenure_section(self, data: Dict) -> List:
        """Build tenure section with chart"""
        elements = []
        
        elements.append(Paragraph("⏰ Tempo de Casa", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        
        # Summary metrics
        avg_tenure = current.get('average_tenure_months', 0)
        years = int(avg_tenure // 12)
        months = int(avg_tenure % 12)
        avg_text = f"{years} anos e {months} meses" if years > 0 else f"{months} meses"
        
        elements.append(Paragraph(f"<b>Tempo médio de casa: {avg_text}</b>", self.styles['BodyText_Custom']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Distribution by tenure range
        by_range = current.get('by_tenure_range', [])
        if by_range:
            elements.append(Paragraph("Distribuição por Tempo de Casa", self.styles['Subsection']))
            
            # Bar chart for tenure
            bar_chart = self._create_bar_chart(
                by_range,
                value_key='count',
                label_key='range',
                bar_color=self.COLORS['purple'],
                width=450,
                height=160
            )
            elements.append(bar_chart)
            elements.append(Spacer(1, 0.3*cm))
            
            tenure_data = [['Faixa', 'Quantidade', '% do Total']]
            total = sum(t.get('count', 0) for t in by_range)
            
            for item in by_range:
                range_name = item.get('range', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                tenure_data.append([range_name, str(count), f"{pct:.1f}%"])
            
            table = Table(tenure_data, colWidths=[6*cm, 5*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['purple']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_leaves_section(self, data: Dict) -> List:
        """Build leaves section with chart"""
        elements = []
        
        elements.append(Paragraph("🏥 Afastamentos", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        
        # Summary
        total = current.get('total', 0)
        elements.append(Paragraph(f"<b>Total de afastamentos no período: {total}</b>", self.styles['BodyText_Custom']))
        elements.append(Spacer(1, 0.5*cm))
        
        # By type
        by_type = current.get('by_type', [])
        if by_type:
            elements.append(Paragraph("Distribuição por Tipo de Afastamento", self.styles['Subsection']))
            
            # Pie chart for leave types
            sorted_types = sorted(by_type, key=lambda x: x.get('count', 0), reverse=True)
            pie_chart = self._create_pie_chart(
                sorted_types[:8],  # Top 8 types for chart
                value_key='count',
                label_key='type',
                width=280,
                height=170
            )
            
            type_data = [['Tipo', 'Qtd', '%']]
            total_types = sum(t.get('count', 0) for t in by_type)
            
            for item in sorted_types:
                leave_type = item.get('type', 'Não informado')
                if len(leave_type) > 25:
                    leave_type = leave_type[:22] + '...'
                count = item.get('count', 0)
                pct = (count / total_types * 100) if total_types > 0 else 0
                type_data.append([leave_type, str(count), f"{pct:.1f}%"])
            
            mini_table = Table(type_data, colWidths=[5*cm, 2*cm, 2*cm])
            mini_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['danger']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            # Combine chart and table
            combined = Table([[pie_chart, mini_table]], colWidths=[9.5*cm, 6.5*cm])
            combined.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ]))
            elements.append(combined)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_payroll_section(self, data: Dict) -> List:
        """Build payroll section with charts"""
        elements = []
        
        elements.append(Paragraph("💰 Folha de Pagamento", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        
        if not current:
            elements.append(Paragraph("Sem dados de folha de pagamento para o período.", self.styles['BodyText_Custom']))
            return elements
        
        # Format currency helper
        def fmt_currency(value):
            return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Main metrics as visual cards
        emp_count = current.get('employee_count', 0)
        total_net = current.get('total_net', 0)
        avg_salary = current.get('average_salary', 0)
        
        # Summary cards table
        cards_data = [
            ['Funcionários', 'Total Líquido', 'Salário Médio'],
            [str(emp_count), fmt_currency(total_net), fmt_currency(avg_salary)],
        ]
        
        cards_table = Table(cards_data, colWidths=[5*cm, 5.5*cm, 5.5*cm])
        cards_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), self.COLORS['info']),
            ('BACKGROUND', (1, 0), (1, 0), self.COLORS['emerald']),
            ('BACKGROUND', (2, 0), (2, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 14),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light_gray']),
        ]))
        
        elements.append(cards_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Detailed summary table
        metrics_data = [
            ['Resumo Financeiro', 'Valor'],
            ['Total Salários Base', fmt_currency(current.get('total_salary', 0))],
            ['Total Proventos', fmt_currency(current.get('total_earnings', 0))],
            ['Total Descontos', fmt_currency(current.get('total_deductions', 0))],
            ['Total Líquido', fmt_currency(current.get('total_net', 0))],
        ]
        
        table = Table(metrics_data, colWidths=[8*cm, 7*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['emerald']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.8*cm))
        
        # By department
        by_department = current.get('by_department', [])
        if by_department:
            elements.append(Paragraph("Distribuição por Setor", self.styles['Subsection']))
            
            # Bar chart for top departments by total
            sorted_depts = sorted(by_department, key=lambda x: x.get('total_net', 0), reverse=True)[:8]
            chart_data = [{'department': d.get('department', '')[:15], 'count': d.get('employee_count', 0)} for d in sorted_depts]
            
            if chart_data:
                bar_chart = self._create_bar_chart(
                    chart_data,
                    value_key='count',
                    label_key='department',
                    bar_color=self.COLORS['emerald'],
                    width=450,
                    height=160
                )
                elements.append(bar_chart)
                elements.append(Spacer(1, 0.3*cm))
            
            dept_data = [['Setor', 'Func.', 'Total Salários', 'Total Líquido']]
            
            for dept in by_department[:12]:  # Top 12 departments
                dept_name = dept.get('department', 'Não informado')
                if len(dept_name) > 22:
                    dept_name = dept_name[:19] + '...'
                emp_count = dept.get('employee_count', 0)
                total_sal = dept.get('total_salary', 0)
                total_net = dept.get('total_net', 0)
                dept_data.append([
                    dept_name,
                    str(emp_count),
                    fmt_currency(total_sal),
                    fmt_currency(total_net)
                ])
            
            table = Table(dept_data, colWidths=[5.5*cm, 2*cm, 4.5*cm, 4.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['success']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_footer(self) -> List:
        """Build report footer"""
        elements = []
        
        elements.append(Spacer(1, 1*cm))
        elements.append(HRFlowable(width="100%", color=self.COLORS['gray']))
        elements.append(Spacer(1, 0.3*cm))
        
        footer_text = "<b>Nexo RH</b> - Sistema de Gestão de Recursos Humanos<br/>Este relatório foi gerado automaticamente. Os dados apresentados são baseados nas informações cadastradas no sistema."
        elements.append(Paragraph(footer_text, self.styles['BodyText_Custom']))
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page number and header to each page"""
        canvas.saveState()
        
        # Footer - Page number
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(self.COLORS['gray'])
        
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.drawRightString(doc.width + doc.rightMargin, 1*cm, text)
        
        # Footer - System name
        canvas.drawString(doc.leftMargin, 1*cm, "Nexo RH")
        
        # Header - Report info
        month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        if hasattr(self, 'report_info') and self.report_info:
            info = self.report_info
            month_name = month_names[info.get('month', 1) - 1]
            header_text = f"Relatório {month_name}/{info.get('year', '')} - Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        else:
            header_text = f"Nexo RH - {datetime.now().strftime('%d/%m/%Y')}"
        
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.COLORS['gray'])
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 0.5*cm, header_text)
        
        # Header line
        canvas.setStrokeColor(self.COLORS['light_gray'])
        canvas.line(doc.leftMargin, doc.height + doc.topMargin + 0.3*cm, 
                   doc.width + doc.rightMargin, doc.height + doc.topMargin + 0.3*cm)
        
        canvas.restoreState()
