"""
Report Generator Service - PDF Generation with ReportLab
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
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """Service for generating PDF reports with HR indicators"""
    
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
    }
    
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
    
    def generate_report(
        self,
        report_type: str,
        sections: List[str],
        year: int,
        month: int,
        months_range: int = 6,
        company: Optional[str] = None,
        division: Optional[str] = None,
        data: Dict[str, Any] = None
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
        
        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build document content
        story = []
        
        # Header / Title Page
        story.extend(self._build_title_page(report_type, year, month, company, division))
        
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
        division: Optional[str]
    ) -> List:
        """Build report title page"""
        elements = []
        
        # Spacer for centering
        elements.append(Spacer(1, 3*cm))
        
        # Report type name mapping
        report_names = {
            'consolidated': 'Relatório Consolidado de RH',
            'headcount': 'Relatório de Efetivo',
            'turnover': 'Relatório de Rotatividade',
            'demographics': 'Relatório Demográfico',
            'tenure': 'Relatório de Tempo de Casa',
            'leaves': 'Relatório de Afastamentos',
            'custom': 'Relatório Customizado'
        }
        
        title = report_names.get(report_type, 'Relatório de RH')
        elements.append(Paragraph(title, self.styles['Title_Custom']))
        
        # Period
        month_name = self.MONTH_NAMES[month - 1] if 1 <= month <= 12 else str(month)
        period_text = f"Período: {month_name} de {year}"
        elements.append(Paragraph(period_text, self.styles['Subtitle']))
        
        # Filters applied
        filters_text = []
        if company:
            company_names = {'0059': 'Infraestrutura', '0060': 'Empreendimentos'}
            filters_text.append(f"Empresa: {company_names.get(company, company)}")
        if division:
            filters_text.append(f"Setor: {division}")
        
        if filters_text:
            elements.append(Paragraph(" | ".join(filters_text), self.styles['BodyText_Custom']))
        
        elements.append(Spacer(1, 1*cm))
        
        # Generation info
        gen_date = datetime.now().strftime("%d/%m/%Y às %H:%M")
        elements.append(Paragraph(f"Gerado em: {gen_date}", self.styles['BodyText_Custom']))
        
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
        """Build headcount section"""
        elements = []
        
        elements.append(Paragraph("👥 Efetivo por Setor", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        by_department = current.get('by_department', [])
        
        if by_department:
            # Table with departments
            table_data = [['Setor', 'Quantidade', '% do Total']]
            total = sum(d.get('count', 0) for d in by_department)
            
            for dept in sorted(by_department, key=lambda x: x.get('count', 0), reverse=True):
                name = dept.get('department', 'Não informado')
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
        """Build turnover section"""
        elements = []
        
        elements.append(Paragraph("🔄 Rotatividade", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        evolution = data.get('evolution', [])
        
        # Current metrics
        metrics_data = [
            ['Métrica', 'Valor'],
            ['Admissões', str(current.get('admissions', 0))],
            ['Demissões', str(current.get('terminations', 0))],
            ['Taxa de Turnover', f"{current.get('turnover_rate', 0):.2f}%"],
        ]
        
        table = Table(metrics_data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['warning']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Evolution table
        if evolution:
            elements.append(Paragraph("Evolução Mensal", self.styles['Subsection']))
            
            evol_data = [['Período', 'Admissões', 'Demissões', 'Turnover']]
            for item in evolution[-6:]:  # Last 6 months
                period = item.get('period', '')
                adm = item.get('admissions', 0)
                term = item.get('terminations', 0)
                rate = item.get('turnover_rate', 0)
                evol_data.append([period, str(adm), str(term), f"{rate:.2f}%"])
            
            evol_table = Table(evol_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
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
        
        # Gender distribution
        by_gender = current.get('by_gender', [])
        if by_gender:
            elements.append(Paragraph("Distribuição por Gênero", self.styles['Subsection']))
            
            gender_data = [['Gênero', 'Quantidade', '% do Total']]
            total = sum(g.get('count', 0) for g in by_gender)
            
            for item in by_gender:
                gender = item.get('gender', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                gender_data.append([gender, str(count), f"{pct:.1f}%"])
            
            table = Table(gender_data, colWidths=[6*cm, 5*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['success']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))
        
        # Age distribution
        by_age = current.get('by_age_range', [])
        if by_age:
            elements.append(Paragraph("Distribuição por Faixa Etária", self.styles['Subsection']))
            
            age_data = [['Faixa Etária', 'Quantidade', '% do Total']]
            total = sum(a.get('count', 0) for a in by_age)
            
            for item in by_age:
                age_range = item.get('age_range', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                age_data.append([age_range, str(count), f"{pct:.1f}%"])
            
            table = Table(age_data, colWidths=[6*cm, 5*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['info']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))
        
        # Education distribution
        by_education = current.get('by_education', [])
        if by_education:
            elements.append(Paragraph("Distribuição por Escolaridade", self.styles['Subsection']))
            
            edu_data = [['Escolaridade', 'Quantidade', '% do Total']]
            total = sum(e.get('count', 0) for e in by_education)
            
            for item in sorted(by_education, key=lambda x: x.get('count', 0), reverse=True):
                education = item.get('education', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                edu_data.append([education[:30], str(count), f"{pct:.1f}%"])  # Truncate long names
            
            table = Table(edu_data, colWidths=[8*cm, 4*cm, 4*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['secondary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_tenure_section(self, data: Dict) -> List:
        """Build tenure section"""
        elements = []
        
        elements.append(Paragraph("⏰ Tempo de Casa", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        
        # Summary metrics
        avg_tenure = current.get('average_tenure_months', 0)
        years = int(avg_tenure // 12)
        months = int(avg_tenure % 12)
        avg_text = f"{years} anos e {months} meses" if years > 0 else f"{months} meses"
        
        elements.append(Paragraph(f"Tempo médio de casa: <b>{avg_text}</b>", self.styles['BodyText_Custom']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Distribution by tenure range
        by_range = current.get('by_tenure_range', [])
        if by_range:
            elements.append(Paragraph("Distribuição por Tempo de Casa", self.styles['Subsection']))
            
            tenure_data = [['Faixa', 'Quantidade', '% do Total']]
            total = sum(t.get('count', 0) for t in by_range)
            
            for item in by_range:
                range_name = item.get('range', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total * 100) if total > 0 else 0
                tenure_data.append([range_name, str(count), f"{pct:.1f}%"])
            
            table = Table(tenure_data, colWidths=[6*cm, 5*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
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
        """Build leaves section"""
        elements = []
        
        elements.append(Paragraph("🏥 Afastamentos", self.styles['Section']))
        elements.append(HRFlowable(width="100%", color=self.COLORS['light_gray']))
        
        current = data.get('current', {})
        
        # Summary
        total = current.get('total', 0)
        elements.append(Paragraph(f"Total de afastamentos no período: <b>{total}</b>", self.styles['BodyText_Custom']))
        elements.append(Spacer(1, 0.5*cm))
        
        # By type
        by_type = current.get('by_type', [])
        if by_type:
            elements.append(Paragraph("Distribuição por Tipo", self.styles['Subsection']))
            
            type_data = [['Tipo de Afastamento', 'Quantidade', '% do Total']]
            total_types = sum(t.get('count', 0) for t in by_type)
            
            for item in sorted(by_type, key=lambda x: x.get('count', 0), reverse=True):
                leave_type = item.get('type', 'Não informado')
                count = item.get('count', 0)
                pct = (count / total_types * 100) if total_types > 0 else 0
                type_data.append([leave_type, str(count), f"{pct:.1f}%"])
            
            table = Table(type_data, colWidths=[8*cm, 4*cm, 4*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['danger']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_gray']]),
            ]))
            
            elements.append(table)
        
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_footer(self) -> List:
        """Build report footer"""
        elements = []
        
        elements.append(Spacer(1, 2*cm))
        elements.append(HRFlowable(width="100%", color=self.COLORS['gray']))
        elements.append(Spacer(1, 0.5*cm))
        
        footer_text = "Este relatório foi gerado automaticamente pelo Sistema de RH. Os dados apresentados são baseados nas informações cadastradas no sistema."
        elements.append(Paragraph(footer_text, self.styles['BodyText_Custom']))
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page number to each page"""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(self.COLORS['gray'])
        
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.drawRightString(doc.width + doc.rightMargin, 1*cm, text)
        
        # Header with date
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 0.5*cm, 
                         f"Relatório RH - {datetime.now().strftime('%d/%m/%Y')}")
        
        canvas.restoreState()
