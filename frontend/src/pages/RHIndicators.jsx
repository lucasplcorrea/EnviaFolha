import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ArrowPathIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  DocumentArrowDownIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import toast from 'react-hot-toast';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';

const RHIndicators = () => {
  const { config } = useTheme();
  const [activeCategory, setActiveCategory] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [indicatorsData, setIndicatorsData] = useState(null);
  const [selectedPayrollPeriod, setSelectedPayrollPeriod] = useState(null);

  // Novos estados para filtros de folha de pagamento
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [availableEmployees, setAvailableEmployees] = useState([]);
  const [availableDepartments, setAvailableDepartments] = useState([]);
  const [filteredStats, setFilteredStats] = useState(null);
  const [showPeriodDropdown, setShowPeriodDropdown] = useState(false);
  const [showDepartmentDropdown, setShowDepartmentDropdown] = useState(false);
  const [showEmployeeDropdown, setShowEmployeeDropdown] = useState(false);
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [debugData, setDebugData] = useState(null);
  const [showDebugModal, setShowDebugModal] = useState(false);
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const exportRef = useRef(null);
  const exportDropdownRef = useRef(null);

  // Carregar dados ao montar ou trocar categoria
  useEffect(() => {
    loadIndicators();
  }, [activeCategory]); // eslint-disable-line react-hooks/exhaustive-deps

  // Inicializar período selecionado quando dados de payroll forem carregados
  useEffect(() => {
    if (activeCategory === 'payroll' && indicatorsData?.periods && indicatorsData.periods.length > 0 && !selectedPayrollPeriod) {
      setSelectedPayrollPeriod(indicatorsData.periods[0].id);
    }
  }, [activeCategory, indicatorsData, selectedPayrollPeriod]);

  // Carregar colaboradores e setores quando entrar na aba payroll
  useEffect(() => {
    if (activeCategory === 'payroll') {
      loadPayrollFiltersData();
    }
  }, [activeCategory]); // eslint-disable-line react-hooks/exhaustive-deps

  // Aplicar filtros quando mudarem
  useEffect(() => {
    if (activeCategory === 'payroll' && (selectedPeriods.length > 0 || selectedDepartments.length > 0 || selectedEmployees.length > 0)) {
      loadFilteredStatistics();
    } else {
      setFilteredStats(null);
    }
  }, [selectedPeriods, selectedDepartments, selectedEmployees, activeCategory]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadIndicators = useCallback(async () => {
    setLoading(true);
    try {
      let response;
      
      switch (activeCategory) {
        case 'overview':
          response = await api.get('/indicators/overview');
          break;
        case 'headcount':
          response = await api.get('/indicators/headcount');
          break;
        case 'turnover':
          response = await api.get('/indicators/turnover');
          break;
        case 'demographics':
          response = await api.get('/indicators/demographics');
          break;
        case 'tenure':
          response = await api.get('/indicators/tenure');
          break;
        case 'leaves':
          response = await api.get('/indicators/leaves');
          break;
        case 'payroll':
          response = await api.get('/payroll/statistics');
          break;
        default:
          response = await api.get('/indicators/overview');
      }
      
      setIndicatorsData(response.data);
    } catch (error) {
      console.error('Erro ao carregar indicadores:', error);
      toast.error('Erro ao carregar indicadores de RH');
    } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  const refreshIndicators = async () => {
    // Invalidar cache no backend primeiro
    try {
      await api.post('/indicators/cache/invalidate');
      toast.success('Cache invalidado, recalculando...');
    } catch (error) {
      console.error('Erro ao invalidar cache:', error);
    }
    
    // Recarregar dados
    await loadIndicators();
    toast.success('Indicadores atualizados!');
  };

  const loadPayrollFiltersData = async () => {
    try {
      const [employeesRes, departmentsRes] = await Promise.all([
        api.get('/payroll/employees'),
        api.get('/payroll/divisions')
      ]);
      
      setAvailableEmployees(employeesRes.data.employees || []);
      setAvailableDepartments(departmentsRes.data.departments || []);
    } catch (error) {
      console.error('Erro ao carregar dados de filtros:', error);
      toast.error('Erro ao carregar filtros');
    }
  };

  const loadFilteredStatistics = async () => {
    try {
      const params = new URLSearchParams();
      
      if (selectedPeriods.length > 0) {
        params.append('periods', selectedPeriods.join(','));
      }
      if (selectedDepartments.length > 0) {
        params.append('divisions', selectedDepartments.join(','));
      }
      if (selectedEmployees.length > 0) {
        params.append('employees', selectedEmployees.join(','));
      }
      
      const response = await api.get(`/payroll/statistics-filtered?${params.toString()}`);
      setFilteredStats(response.data.stats);
    } catch (error) {
      console.error('Erro ao carregar estatísticas filtradas:', error);
      toast.error('Erro ao aplicar filtros');
    }
  };

  const loadDebugData = async () => {
    try {
      const params = new URLSearchParams();
      
      if (selectedPeriods.length > 0) {
        params.append('periods', selectedPeriods.join(','));
      }
      
      const response = await api.get(`/payroll/statistics-debug?${params.toString()}`);
      setDebugData(response.data);
      setShowDebugModal(true);
    } catch (error) {
      console.error('Erro ao carregar dados de debug:', error);
      toast.error('Erro ao carregar detalhes');
    }
  };

  const clearFilters = () => {
    setSelectedPeriods([]);
    setSelectedDepartments([]);
    setSelectedEmployees([]);
    setFilteredStats(null);
    setEmployeeSearch('');
  };

  const togglePeriodSelection = (periodId) => {
    setSelectedPeriods(prev => 
      prev.includes(periodId)
        ? prev.filter(id => id !== periodId)
        : [...prev, periodId]
    );
  };

  const toggleDepartmentSelection = (departmentName) => {
    setSelectedDepartments(prev => {
      const newSelection = prev.includes(departmentName)
        ? prev.filter(name => name !== departmentName)
        : [...prev, departmentName];
      
      // Limpar colaboradores selecionados que não pertencem aos departamentos selecionados
      if (newSelection.length > 0) {
        const validEmployeeIds = availableEmployees
          .filter(emp => newSelection.includes(emp.department))
          .map(emp => emp.id);
        
        setSelectedEmployees(currentSelected => 
          currentSelected.filter(id => validEmployeeIds.includes(id))
        );
      }
      
      return newSelection;
    });
  };

  const toggleEmployeeSelection = (employeeId) => {
    setSelectedEmployees(prev =>
      prev.includes(employeeId)
        ? prev.filter(id => id !== employeeId)
        : [...prev, employeeId]
    );
  };

  // Filtrar colaboradores por departamento selecionado E por busca
  const filteredEmployeesList = availableEmployees
    .filter(emp => {
      // Se há departamentos selecionados, filtrar apenas colaboradores desses departamentos
      if (selectedDepartments.length > 0) {
        return selectedDepartments.includes(emp.department);
      }
      return true;
    })
    .filter(emp =>
      emp.name.toLowerCase().includes(employeeSearch.toLowerCase()) ||
      emp.unique_id.includes(employeeSearch)
    );

  // Função para traduzir labels técnicos para português
  const translateLabel = (key) => {
    const translations = {
      // Headcount/Efetivo
      'total_active': 'Total de Colaboradores Ativos',
      'by_department': 'Por Departamento',
      'by_sector': 'Por Setor',
      'by_company': 'Por Empresa',
      'by_contract_type': 'Por Tipo de Contrato',
      'by_employment_status': 'Por Status de Emprego',
      'department': 'Departamento',
      'sector': 'Setor',
      'company_code': 'Código da Empresa',
      'contract_type': 'Tipo de Contrato',
      'employment_status': 'Status de Emprego',
      'count': 'Quantidade',
      
      // Turnover/Rotatividade
      'period': 'Período',
      'start': 'Início',
      'end': 'Fim',
      'headcount': 'Efetivo',
      'average': 'Média',
      'movements': 'Movimentações',
      'admissions': 'Admissões',
      'terminations': 'Desligamentos',
      'rates': 'Taxas',
      'turnover': 'Rotatividade',
      'admission': 'Admissão',
      'termination': 'Desligamento',
      'termination_reasons': 'Motivos de Desligamento',
      'turnover_by_department': 'Rotatividade por Departamento',
      'reason': 'Motivo',
      
      // Demografia
      'by_sex': 'Por Sexo',
      'age_ranges': 'Faixas Etárias',
      'average_age': 'Idade Média',
      'sex': 'Sexo',
      'range': 'Faixa',
      'M': 'Masculino',
      'F': 'Feminino',
      
      // Tempo de Casa/Tenure
      'average_tenure_years': 'Tempo Médio de Casa (anos)',
      'tenure_ranges': 'Faixas de Tempo de Casa',
      'avg_years': 'Média (anos)',
      
      // Afastamentos/Leaves
      'currently_on_leave': 'Atualmente Afastados',
      'by_leave_type': 'Por Tipo de Afastamento',
      'by_leave_reason': 'Por Motivo de Afastamento',
      'leave_type': 'Tipo de Afastamento',
      'leave_reason': 'Motivo de Afastamento'
    };
    
    // Função auxiliar para capitalizar corretamente (sem afetar após caracteres especiais)
    const capitalizeProper = (str) => {
      return str.toLowerCase().replace(/^\w|\s\w/g, l => l.toUpperCase());
    };
    
    return translations[key] || capitalizeProper(key.replace(/_/g, ' '));
  };

  // Função para formatar tempo (anos/meses)
  const formatTenure = (years, months) => {
    if (!years && !months) return '0 meses';
    
    if (years >= 1) {
      const remainingMonths = months ? months % 12 : 0;
      if (remainingMonths === 0) {
        return years === 1 ? '1 ano' : `${years} anos`;
      }
      return `${years} ${years === 1 ? 'ano' : 'anos'} e ${remainingMonths} ${remainingMonths === 1 ? 'mês' : 'meses'}`;
    }
    
    return `${months} ${months === 1 ? 'mês' : 'meses'}`;
  };


  const categories = [
    { id: 'overview', name: 'Visão Geral', icon: ChartBarIcon, color: 'blue' },
    { id: 'headcount', name: 'Efetivo', icon: UserGroupIcon, color: 'green' },
    { id: 'turnover', name: 'Rotatividade', icon: ArrowPathIcon, color: 'purple' },
    { id: 'demographics', name: 'Demografia', icon: UserGroupIcon, color: 'yellow' },
    { id: 'tenure', name: 'Tempo de Casa', icon: ClockIcon, color: 'indigo' },
    { id: 'leaves', name: 'Afastamentos', icon: ExclamationTriangleIcon, color: 'pink' },
    { id: 'payroll', name: 'Folha de Pagamento', icon: CurrencyDollarIcon, color: 'emerald' }
  ];

  const MetricCard = ({ title, value, unit, trend, trendValue, icon: Icon, color = 'blue' }) => {
    const colorClasses = {
      blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
      green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
      purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
      yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
      indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
      pink: 'bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-400',
      emerald: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
    };

    return (
      <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
          {trend && (
            <div className={`flex items-center text-sm ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
              {trend === 'up' ? (
                <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
              )}
              <span>{trendValue}%</span>
            </div>
          )}
        </div>
        <h3 className={`text-sm font-medium ${config.classes.textSecondary} mb-1`}>{title}</h3>
        <p className={`text-3xl font-bold ${config.classes.text}`}>
          {value}
          {unit && <span className="text-lg ml-1">{unit}</span>}
        </p>
      </div>
    );
  };

  const renderOverview = () => {
    if (!indicatorsData?.headcount) return null;
    
    const { headcount, turnover, tenure, leaves } = indicatorsData;
    
    return (
      <div className="space-y-6">
        {/* Métricas principais */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Total de Colaboradores"
            value={headcount.total_active}
            icon={UserGroupIcon}
            color="blue"
          />
          <MetricCard
            title="Taxa de Rotatividade"
            value={turnover.rates?.turnover || 0}
            unit="%"
            icon={ArrowPathIcon}
            color="green"
          />
          <MetricCard
            title="Tempo Médio de Casa"
            value={formatTenure(tenure.average_tenure_years || 0, tenure.average_tenure_months || 0)}
            icon={ClockIcon}
            color="purple"
          />
          <MetricCard
            title="Colaboradores Afastados"
            value={leaves.currently_on_leave || 0}
            icon={ExclamationTriangleIcon}
            color="yellow"
          />
        </div>

        {/* Distribuição por Departamento */}
        {headcount.by_department && headcount.by_department.length > 0 && (
          <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
              Efetivo por Departamento
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {headcount.by_department.map((dept, idx) => (
                <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                  <p className={`text-sm ${config.classes.textSecondary}`}>{dept.department || 'Não informado'}</p>
                  <p className={`text-2xl font-bold ${config.classes.text}`}>{dept.count}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Faixas Etárias */}
        {indicatorsData.demographics?.age_ranges && (
          <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
              Distribuição por Faixa Etária
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {indicatorsData.demographics.age_ranges.map((range, idx) => (
                <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                  <p className={`text-sm ${config.classes.textSecondary}`}>{range.range}</p>
                  <p className={`text-2xl font-bold ${config.classes.text}`}>{range.count}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderPayroll = () => {
    if (!indicatorsData?.success) return null;
    
    const { periods, financial_stats, totals } = indicatorsData;
    
    // Se não há período selecionado e não há filtros, usar dados consolidados de TODOS os períodos
    const displayStats = filteredStats || 
      (selectedPayrollPeriod 
        ? financial_stats?.find(p => p.period_id === selectedPayrollPeriod)
        : (financial_stats && financial_stats.length > 0 ? {
            // Consolidar todos os períodos
            period_name: 'Todos os Períodos',
            period_id: null,
            total_employees: totals?.total_employees || 0,
            total_proventos: totals?.total_proventos || 0,
            total_descontos: totals?.total_descontos || 0,
            total_vantagens: totals?.total_vantagens || 0,
            total_liquido: totals?.total_liquido || 0,
            total_inss: totals?.total_inss || 0,
            total_irrf: totals?.total_irrf || 0,
            total_fgts: totals?.total_fgts || 0,
            total_salario_base: totals?.total_salarios || 0,
            total_valor_salario: totals?.total_salarios || 0,
            total_salario_mensal: totals?.total_salarios || 0,
            total_he_50_diurnas: financial_stats.reduce((sum, p) => sum + (p.total_he_50_diurnas || 0), 0),
            total_he_50_noturnas: financial_stats.reduce((sum, p) => sum + (p.total_he_50_noturnas || 0), 0),
            total_he_60: financial_stats.reduce((sum, p) => sum + (p.total_he_60 || 0), 0),
            total_he_100_diurnas: financial_stats.reduce((sum, p) => sum + (p.total_he_100_diurnas || 0), 0),
            total_he_100_noturnas: financial_stats.reduce((sum, p) => sum + (p.total_he_100_noturnas || 0), 0),
            total_adicional_noturno: financial_stats.reduce((sum, p) => sum + (p.total_adicional_noturno || 0), 0),
            total_gratificacoes: financial_stats.reduce((sum, p) => sum + (p.total_gratificacoes || 0), 0),
            total_periculosidade: financial_stats.reduce((sum, p) => sum + (p.total_periculosidade || 0), 0),
            total_insalubridade: financial_stats.reduce((sum, p) => sum + (p.total_insalubridade || 0), 0),
            total_plano_saude: totals?.total_plano_saude || 0,
            total_vale_transporte: financial_stats.reduce((sum, p) => sum + (p.total_vale_transporte || 0), 0),
            avg_salario: totals?.total_employees > 0 ? (totals?.total_salarios || 0) / totals?.total_employees : 0,
            trabalhando: Math.round(financial_stats.reduce((sum, p) => sum + (p.trabalhando || 0), 0) / financial_stats.length),
            ferias: Math.round(financial_stats.reduce((sum, p) => sum + (p.ferias || 0), 0) / financial_stats.length),
            afastados: Math.round(financial_stats.reduce((sum, p) => sum + (p.afastados || 0), 0) / financial_stats.length),
            demitidos: Math.round(financial_stats.reduce((sum, p) => sum + (p.demitidos || 0), 0) / financial_stats.length),
          } : null)
      );
    const hasActiveFilters = selectedPeriods.length > 0 || selectedDepartments.length > 0 || selectedEmployees.length > 0;

    // Nomes selecionados para exibição
    const selectedPeriodNames = periods?.filter(p => selectedPeriods.includes(p.id)).map(p => p.period_name) || [];
    const selectedEmployeeNames = availableEmployees?.filter(e => selectedEmployees.includes(e.id)).map(e => e.name) || [];

    // Funções de Exportação
    const exportCurrentView = async () => {
      try {
        setShowExportDropdown(false);
        const loadingToast = toast.loading('📄 Gerando PDF da visualização atual...');
        
        const element = exportRef.current;
        if (!element) {
          toast.error('Erro ao capturar tela');
          return;
        }

        const canvas = await html2canvas(element, {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: isDarkMode ? '#1F2937' : '#FFFFFF'
        });

        const pdf = new jsPDF('p', 'mm', 'a4');
        const imgWidth = 210; // A4 width in mm
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        let heightLeft = imgHeight;
        let position = 0;

        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= 297; // A4 height

        while (heightLeft > 0) {
          position = heightLeft - imgHeight;
          pdf.addPage();
          pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
          heightLeft -= 297;
        }

        const filename = `indicadores_rh_${new Date().toISOString().split('T')[0]}.pdf`;
        pdf.save(filename);
        
        toast.dismiss(loadingToast);
        toast.success('✅ PDF exportado com sucesso!');
      } catch (error) {
        console.error('Erro ao exportar PDF:', error);
        toast.error('❌ Erro ao gerar PDF');
      }
    };

    const exportCompleteReport = () => {
      try {
        setShowExportDropdown(false);
        const loadingToast = toast.loading('📊 Gerando relatório completo...');

        const pdf = new jsPDF('p', 'mm', 'a4');
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        let yPos = 20;

        // Título
        pdf.setFontSize(20);
        pdf.setFont(undefined, 'bold');
        pdf.text('Relatório de Indicadores de RH', pageWidth / 2, yPos, { align: 'center' });
        
        yPos += 10;
        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');
        pdf.text(`Gerado em: ${new Date().toLocaleString('pt-BR')}`, pageWidth / 2, yPos, { align: 'center' });
        
        yPos += 15;

        // Resumo Executivo
        pdf.setFontSize(14);
        pdf.setFont(undefined, 'bold');
        pdf.text('1. Resumo Executivo', 15, yPos);
        yPos += 8;

        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');
        
        const stats = displayStats || {};
        const lines = [
          `Total de Colaboradores: ${stats.total_employees || 0}`,
          `Trabalhando: ${stats.trabalhando || 0}`,
          `Em Férias: ${stats.ferias || 0}`,
          `Afastados: ${stats.afastados || 0}`,
          `Desligados no Período: ${stats.demitidos || 0}`,
          ``,
          `Contratações: ${stats.contratados || 0}`,
          `Desligamentos: ${stats.desligados || 0}`,
          `Taxa de Turnover: ${stats.turnover_rate || 0}%`,
          ``,
          `Folha de Pagamento Total: R$ ${(stats.total_salarios || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Salário Médio: R$ ${(stats.avg_salario || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Média de Líquido: R$ ${(stats.avg_liquido || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
        ];

        lines.forEach(line => {
          if (yPos > pageHeight - 20) {
            pdf.addPage();
            yPos = 20;
          }
          pdf.text(line, 15, yPos);
          yPos += 6;
        });

        // Detalhamento Financeiro
        yPos += 10;
        if (yPos > pageHeight - 40) {
          pdf.addPage();
          yPos = 20;
        }

        pdf.setFontSize(14);
        pdf.setFont(undefined, 'bold');
        pdf.text('2. Detalhamento Financeiro', 15, yPos);
        yPos += 8;

        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');

        const financialLines = [
          `Horas Extras 50%: R$ ${(stats.total_he50 || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Horas Extras 100%: R$ ${(stats.total_he100 || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Adicional Noturno: R$ ${(stats.total_adicional_noturno || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Gratificações: R$ ${(stats.total_gratificacoes || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Insalubridade: R$ ${(stats.total_insalubridade || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Periculosidade: R$ ${(stats.total_periculosidade || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Vale Transporte: R$ ${(stats.total_vale_transporte || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          `Plano de Saúde: R$ ${(stats.total_plano_saude || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
        ];

        financialLines.forEach(line => {
          if (yPos > pageHeight - 20) {
            pdf.addPage();
            yPos = 20;
          }
          pdf.text(line, 15, yPos);
          yPos += 6;
        });

        const filename = `relatorio_completo_rh_${new Date().toISOString().split('T')[0]}.pdf`;
        pdf.save(filename);
        
        toast.dismiss(loadingToast);
        toast.success('✅ Relatório completo exportado!');
      } catch (error) {
        console.error('Erro ao exportar relatório:', error);
        toast.error('❌ Erro ao gerar relatório');
      }
    };

    const exportMovementReport = () => {
      try {
        setShowExportDropdown(false);
        const loadingToast = toast.loading('📈 Gerando relatório de movimentação...');

        const pdf = new jsPDF('p', 'mm', 'a4');
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        let yPos = 20;

        // Título
        pdf.setFontSize(20);
        pdf.setFont(undefined, 'bold');
        pdf.text('Relatório de Movimentação de Pessoal', pageWidth / 2, yPos, { align: 'center' });
        
        yPos += 10;
        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');
        pdf.text(`Período de Análise: ${selectedPeriodNames.length > 0 ? selectedPeriodNames.join(', ') : 'Todos os períodos'}`, pageWidth / 2, yPos, { align: 'center' });
        pdf.text(`Gerado em: ${new Date().toLocaleString('pt-BR')}`, pageWidth / 2, yPos + 5, { align: 'center' });
        
        yPos += 20;

        const stats = displayStats || {};

        // Indicadores de Turnover
        pdf.setFontSize(14);
        pdf.setFont(undefined, 'bold');
        pdf.text('Indicadores de Rotatividade', 15, yPos);
        yPos += 8;

        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');

        const turnoverLines = [
          `Taxa de Turnover: ${stats.turnover_rate || 0}%`,
          ``,
          `Contratações no Período: ${stats.contratados || 0} colaboradores`,
          `Desligamentos no Período: ${stats.desligados || 0} colaboradores`,
          `Saldo Líquido: ${(stats.contratados || 0) - (stats.desligados || 0)} colaboradores`,
          ``,
          `Efetivo Atual: ${stats.total_employees || 0} colaboradores`,
          `Taxa de Crescimento: ${stats.contratados && stats.total_employees ? 
            ((stats.contratados - stats.desligados) / stats.total_employees * 100).toFixed(2) : 0}%`
        ];

        turnoverLines.forEach(line => {
          if (yPos > pageHeight - 20) {
            pdf.addPage();
            yPos = 20;
          }
          pdf.text(line, 15, yPos);
          yPos += 6;
        });

        // Análise de Status
        yPos += 10;
        if (yPos > pageHeight - 40) {
          pdf.addPage();
          yPos = 20;
        }

        pdf.setFontSize(14);
        pdf.setFont(undefined, 'bold');
        pdf.text('Distribuição por Status', 15, yPos);
        yPos += 8;

        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');

        const statusLines = [
          `Trabalhando: ${stats.trabalhando || 0} (${stats.total_employees ? ((stats.trabalhando / stats.total_employees) * 100).toFixed(1) : 0}%)`,
          `Em Férias: ${stats.ferias || 0} (${stats.total_employees ? ((stats.ferias / stats.total_employees) * 100).toFixed(1) : 0}%)`,
          `Afastados: ${stats.afastados || 0} (${stats.total_employees ? ((stats.afastados / stats.total_employees) * 100).toFixed(1) : 0}%)`,
          `Demitidos: ${stats.demitidos || 0} (${stats.total_employees ? ((stats.demitidos / stats.total_employees) * 100).toFixed(1) : 0}%)`
        ];

        statusLines.forEach(line => {
          if (yPos > pageHeight - 20) {
            pdf.addPage();
            yPos = 20;
          }
          pdf.text(line, 15, yPos);
          yPos += 6;
        });

        const filename = `relatorio_movimentacao_${new Date().toISOString().split('T')[0]}.pdf`;
        pdf.save(filename);
        
        toast.dismiss(loadingToast);
        toast.success('✅ Relatório de movimentação exportado!');
      } catch (error) {
        console.error('Erro ao exportar relatório de movimentação:', error);
        toast.error('❌ Erro ao gerar relatório');
      }
    };

    const exportToExcel = () => {
      try {
        setShowExportDropdown(false);
        const loadingToast = toast.loading('📗 Gerando arquivo Excel...');

        const stats = displayStats || {};

        // Criar workbook
        const wb = XLSX.utils.book_new();

        // Sheet 1: Resumo
        const resumoData = [
          ['RELATÓRIO DE INDICADORES DE RH'],
          ['Gerado em:', new Date().toLocaleString('pt-BR')],
          ['Período:', selectedPeriodNames.length > 0 ? selectedPeriodNames.join(', ') : 'Todos os períodos'],
          [],
          ['RESUMO EXECUTIVO'],
          ['Total de Colaboradores', stats.total_employees || 0],
          ['Trabalhando', stats.trabalhando || 0],
          ['Em Férias', stats.ferias || 0],
          ['Afastados', stats.afastados || 0],
          ['Desligados no Período', stats.demitidos || 0],
          [],
          ['MOVIMENTAÇÃO'],
          ['Contratações', stats.contratados || 0],
          ['Desligamentos', stats.desligados || 0],
          ['Taxa de Turnover (%)', stats.turnover_rate || 0],
          [],
          ['FOLHA DE PAGAMENTO'],
          ['Total', stats.total_salarios || 0],
          ['Salário Médio', stats.avg_salario || 0],
          ['Média de Líquido', stats.avg_liquido || 0]
        ];

        const wsResumo = XLSX.utils.aoa_to_sheet(resumoData);
        XLSX.utils.book_append_sheet(wb, wsResumo, 'Resumo');

        // Sheet 2: Detalhamento Financeiro
        const financeiroData = [
          ['DETALHAMENTO FINANCEIRO'],
          [],
          ['Rubrica', 'Valor (R$)'],
          ['Salários', stats.total_salarios || 0],
          ['Horas Extras 50%', stats.total_he50 || 0],
          ['Horas Extras 100%', stats.total_he100 || 0],
          ['Adicional Noturno', stats.total_adicional_noturno || 0],
          ['Gratificações', stats.total_gratificacoes || 0],
          ['Insalubridade', stats.total_insalubridade || 0],
          ['Periculosidade', stats.total_periculosidade || 0],
          ['Vale Transporte', stats.total_vale_transporte || 0],
          ['Plano de Saúde', stats.total_plano_saude || 0]
        ];

        const wsFinanceiro = XLSX.utils.aoa_to_sheet(financeiroData);
        XLSX.utils.book_append_sheet(wb, wsFinanceiro, 'Financeiro');

        // Sheet 3: Análise de Turnover
        const turnoverData = [
          ['ANÁLISE DE TURNOVER'],
          [],
          ['Indicador', 'Valor'],
          ['Taxa de Turnover (%)', stats.turnover_rate || 0],
          ['Contratações', stats.contratados || 0],
          ['Desligamentos', stats.desligados || 0],
          ['Saldo Líquido', (stats.contratados || 0) - (stats.desligados || 0)],
          ['Efetivo Atual', stats.total_employees || 0],
          [],
          ['DISTRIBUIÇÃO POR STATUS'],
          ['Status', 'Quantidade', 'Percentual (%)'],
          ['Trabalhando', stats.trabalhando || 0, stats.total_employees ? ((stats.trabalhando / stats.total_employees) * 100).toFixed(2) : 0],
          ['Em Férias', stats.ferias || 0, stats.total_employees ? ((stats.ferias / stats.total_employees) * 100).toFixed(2) : 0],
          ['Afastados', stats.afastados || 0, stats.total_employees ? ((stats.afastados / stats.total_employees) * 100).toFixed(2) : 0],
          ['Demitidos', stats.demitidos || 0, stats.total_employees ? ((stats.demitidos / stats.total_employees) * 100).toFixed(2) : 0]
        ];

        const wsTurnover = XLSX.utils.aoa_to_sheet(turnoverData);
        XLSX.utils.book_append_sheet(wb, wsTurnover, 'Turnover');

        const filename = `dados_rh_${new Date().toISOString().split('T')[0]}.xlsx`;
        XLSX.writeFile(wb, filename);
        
        toast.dismiss(loadingToast);
        toast.success('✅ Arquivo Excel exportado!');
      } catch (error) {
        console.error('Erro ao exportar Excel:', error);
        toast.error('❌ Erro ao gerar arquivo Excel');
      }
    };

    // Click fora do dropdown para fechar
    useEffect(() => {
      const handleClickOutside = (event) => {
        if (exportDropdownRef.current && !exportDropdownRef.current.contains(event.target)) {
          setShowExportDropdown(false);
        }
      };

      if (showExportDropdown) {
        document.addEventListener('mousedown', handleClickOutside);
      }

      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }, [showExportDropdown]);

    // Função auxiliar para renderizar conteúdo baseado na categoria ativa
    const renderOverview = () => {
      const metrics = indicatorsData?.metrics || {};
      return null; // Implementação futura
    };

    const renderContent = () => {
      if (loading) {
        return (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <span className={`ml-4 text-lg ${config.classes.textSecondary}`}>Carregando indicadores...</span>
          </div>
        );
      }

      if (!indicatorsData) {
        return (
          <div className={`${config.classes.card} rounded-lg shadow p-8 text-center`}>
            <ExclamationTriangleIcon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <p className={config.classes.text}>Nenhum dado disponível</p>
          </div>
        );
      }

      if (activeCategory === 'overview') {
        return renderOverview();
      }

      const metrics = indicatorsData.metrics || {};

      return (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Object.entries(metrics).map(([key, value]) => {
              if (typeof value === 'object' && !Array.isArray(value)) return null;
              if (Array.isArray(value)) return null;
              
              // Formatação especial para campos específicos
              let displayValue = value;
              let displayUnit = '';
              
              if (key === 'average_age') {
                displayValue = value;
                displayUnit = value === 1 ? 'ano' : 'anos';
              } else if (key === 'average_tenure_years') {
                displayValue = formatTenure(indicatorsData.metrics?.average_tenure_years, indicatorsData.metrics?.average_tenure_months);
              } else if (typeof value === 'number') {
                displayValue = Number.isInteger(value) ? value : value.toFixed(2);
              }
              
              return (
                <MetricCard
                  key={key}
                  title={translateMetricKey(key)}
                  value={displayValue}
                  unit={displayUnit}
                />
              );
            })}
          </div>

          {/* Distribuições */}
          {Object.entries(indicatorsData.distributions || {}).map(([distKey, distData]) => {
            if (!distData || Object.keys(distData).length === 0) return null;
            
            return (
              <div key={distKey} className={`${config.classes.card} rounded-lg shadow p-6`}>
                <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
                  {translateMetricKey(distKey)}
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(distData).map(([key, count]) => (
                    <div key={key} className={`${config.classes.card} p-4 rounded-lg ${config.classes.border}`}>
                      <p className={`text-sm ${config.classes.textSecondary}`}>{translateMetricKey(key)}</p>
                      <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>{count}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      );
    };

    return (
      <div className="space-y-6">
        {/* Seção de Filtros Modernizada */}
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className={`text-lg font-semibold ${config.classes.text}`}>
                🔍 Filtros de Análise
              </h3>
              <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
                Selecione períodos, departamentos ou colaboradores para análise detalhada
              </p>
            </div>
            <div className="flex gap-3">
              {/* Botão de Exportação */}
              <div className="relative" ref={exportDropdownRef}>
                <button
                  onClick={() => setShowExportDropdown(!showExportDropdown)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-sm"
                >
                  <DocumentArrowDownIcon className="w-5 h-5" />
                  Exportar Relatório
                  <ChevronDownIcon className={`w-4 h-4 transition-transform ${showExportDropdown ? 'rotate-180' : ''}`} />
                </button>
                
                {showExportDropdown && (
                  <div className={`absolute right-0 mt-2 w-72 ${config.classes.card} rounded-lg shadow-xl border ${config.classes.border} z-30 overflow-hidden`}>
                    <div className={`px-4 py-3 border-b ${config.classes.border} bg-gray-50 dark:bg-gray-800`}>
                      <p className={`text-sm font-semibold ${config.classes.text}`}>Selecione o formato</p>
                    </div>
                    <div className="py-2">
                      <button
                        onClick={exportCurrentView}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-3 ${config.classes.text}`}
                      >
                        <span className="text-2xl">📄</span>
                        <div>
                          <p className="font-medium">Visualização Atual (PDF)</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Captura da tela atual</p>
                        </div>
                      </button>
                      
                      <button
                        onClick={exportCompleteReport}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-3 ${config.classes.text}`}
                      >
                        <span className="text-2xl">📊</span>
                        <div>
                          <p className="font-medium">Relatório Completo (PDF)</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Todas as métricas detalhadas</p>
                        </div>
                      </button>
                      
                      <button
                        onClick={exportMovementReport}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-3 ${config.classes.text}`}
                      >
                        <span className="text-2xl">📈</span>
                        <div>
                          <p className="font-medium">Relatório de Movimentação (PDF)</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Foco em turnover e contratações</p>
                        </div>
                      </button>
                      
                      <button
                        onClick={exportToExcel}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-3 ${config.classes.text}`}
                      >
                        <span className="text-2xl">📗</span>
                        <div>
                          <p className="font-medium">Exportar Dados (Excel)</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Planilha com dados brutos</p>
                        </div>
                      </button>
                    </div>
                  </div>
                )}
              </div>
              
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors shadow-sm"
                >
                  ✕ Limpar Filtros
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Dropdown de Períodos */}
            <div className="relative">
              <button
                onClick={() => { setShowPeriodDropdown(!showPeriodDropdown); setShowDepartmentDropdown(false); setShowEmployeeDropdown(false); }}
                className={`w-full px-4 py-3 text-left rounded-lg border-2 transition-all ${
                  selectedPeriods.length > 0 
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                    : `${config.classes.border} ${config.classes.card}`
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className={`text-sm font-medium ${config.classes.text}`}>📅 Períodos</span>
                    <p className={`text-xs ${config.classes.textSecondary} mt-1`}>
                      {selectedPeriods.length > 0 
                        ? `${selectedPeriods.length} selecionado(s)` 
                        : 'Todos os períodos'}
                    </p>
                  </div>
                  <svg className={`w-5 h-5 transition-transform ${showPeriodDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>
              
              {showPeriodDropdown && (
                <div className={`absolute z-20 w-full mt-2 ${config.classes.card} rounded-lg shadow-lg border ${config.classes.border} max-h-64 overflow-y-auto`}>
                  <div className="p-2 border-b sticky top-0 bg-white dark:bg-gray-800">
                    <button
                      onClick={() => setSelectedPeriods(periods?.map(p => p.id) || [])}
                      className="text-xs text-blue-600 hover:text-blue-700 mr-3"
                    >
                      Selecionar todos
                    </button>
                    <button
                      onClick={() => setSelectedPeriods([])}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      Limpar
                    </button>
                  </div>
                  {periods?.map(period => (
                    <label key={period.id} className={`flex items-center px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      selectedPeriods.includes(period.id) ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                    }`}>
                      <input
                        type="checkbox"
                        checked={selectedPeriods.includes(period.id)}
                        onChange={() => togglePeriodSelection(period.id)}
                        className="mr-3 h-4 w-4 text-blue-600 rounded"
                      />
                      <span className={`flex-1 text-sm ${config.classes.text}`}>{period.period_name}</span>
                      <span className="text-xs text-gray-400">{period.total_records} reg.</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Dropdown de Departamentos */}
            <div className="relative">
              <button
                onClick={() => { setShowDepartmentDropdown(!showDepartmentDropdown); setShowPeriodDropdown(false); setShowEmployeeDropdown(false); }}
                className={`w-full px-4 py-3 text-left rounded-lg border-2 transition-all ${
                  selectedDepartments.length > 0 
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20' 
                    : `${config.classes.border} ${config.classes.card}`
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className={`text-sm font-medium ${config.classes.text}`}>🏢 Departamentos</span>
                    <p className={`text-xs ${config.classes.textSecondary} mt-1`}>
                      {selectedDepartments.length > 0 
                        ? `${selectedDepartments.length} selecionado(s)` 
                        : 'Todos os departamentos'}
                    </p>
                  </div>
                  <svg className={`w-5 h-5 transition-transform ${showDepartmentDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>
              
              {showDepartmentDropdown && (
                <div className={`absolute z-20 w-full mt-2 ${config.classes.card} rounded-lg shadow-lg border ${config.classes.border} max-h-64 overflow-y-auto`}>
                  <div className="p-2 border-b sticky top-0 bg-white dark:bg-gray-800">
                    <button
                      onClick={() => setSelectedDepartments(availableDepartments?.map(d => d.name) || [])}
                      className="text-xs text-green-600 hover:text-green-700 mr-3"
                    >
                      Selecionar todos
                    </button>
                    <button
                      onClick={() => setSelectedDepartments([])}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      Limpar
                    </button>
                  </div>
                  {availableDepartments?.length > 0 ? availableDepartments.map(dept => (
                    <label key={dept.name} className={`flex items-center px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      selectedDepartments.includes(dept.name) ? 'bg-green-50 dark:bg-green-900/30' : ''
                    }`}>
                      <input
                        type="checkbox"
                        checked={selectedDepartments.includes(dept.name)}
                        onChange={() => toggleDepartmentSelection(dept.name)}
                        className="mr-3 h-4 w-4 text-green-600 rounded"
                      />
                      <span className={`flex-1 text-sm ${config.classes.text}`}>{dept.name}</span>
                      <span className="text-xs text-gray-400">{dept.total_employees} colab.</span>
                    </label>
                  )) : (
                    <p className="px-4 py-3 text-sm text-gray-500">Nenhum departamento disponível</p>
                  )}
                </div>
              )}
            </div>

            {/* Dropdown de Colaboradores com Busca */}
            <div className="relative">
              <button
                onClick={() => { setShowEmployeeDropdown(!showEmployeeDropdown); setShowPeriodDropdown(false); setShowDepartmentDropdown(false); }}
                className={`w-full px-4 py-3 text-left rounded-lg border-2 transition-all ${
                  selectedEmployees.length > 0 
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' 
                    : `${config.classes.border} ${config.classes.card}`
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className={`text-sm font-medium ${config.classes.text}`}>👥 Colaboradores</span>
                    <p className={`text-xs ${config.classes.textSecondary} mt-1`}>
                      {selectedEmployees.length > 0 
                        ? `${selectedEmployees.length} selecionado(s)` 
                        : selectedDepartments.length > 0
                          ? `${filteredEmployeesList.length} do(s) departamento(s) selecionado(s)`
                          : 'Todos os colaboradores'}
                    </p>
                  </div>
                  <svg className={`w-5 h-5 transition-transform ${showEmployeeDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>
              
              {showEmployeeDropdown && (
                <div className={`absolute z-20 w-full mt-2 ${config.classes.card} rounded-lg shadow-lg border ${config.classes.border} max-h-80 overflow-hidden`}>
                  {selectedDepartments.length > 0 && (
                    <div className="px-3 py-2 bg-blue-50 dark:bg-blue-900/30 border-b text-xs text-blue-700 dark:text-blue-300">
                      🔗 Mostrando apenas colaboradores de: {selectedDepartments.join(', ')}
                    </div>
                  )}
                  <div className="p-2 border-b sticky top-0 bg-white dark:bg-gray-800">
                    <input
                      type="text"
                      placeholder="🔎 Buscar por nome ou matrícula..."
                      value={employeeSearch}
                      onChange={(e) => setEmployeeSearch(e.target.value)}
                      className={`w-full px-3 py-2 text-sm rounded border ${config.classes.border} ${config.classes.card} focus:ring-2 focus:ring-purple-500`}
                    />
                    <div className="flex justify-between mt-2">
                      <button
                        onClick={() => setSelectedEmployees(filteredEmployeesList.map(e => e.id))}
                        className="text-xs text-purple-600 hover:text-purple-700"
                      >
                        Selecionar filtrados ({filteredEmployeesList.length})
                      </button>
                      <button
                        onClick={() => setSelectedEmployees([])}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Limpar
                      </button>
                    </div>
                  </div>
                  <div className="max-h-52 overflow-y-auto">
                    {filteredEmployeesList.length > 0 ? filteredEmployeesList.map(employee => (
                      <label key={employee.id} className={`flex items-center px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                        selectedEmployees.includes(employee.id) ? 'bg-purple-50 dark:bg-purple-900/30' : ''
                      }`}>
                        <input
                          type="checkbox"
                          checked={selectedEmployees.includes(employee.id)}
                          onChange={() => toggleEmployeeSelection(employee.id)}
                          className="mr-3 h-4 w-4 text-purple-600 rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm ${config.classes.text} truncate`}>{employee.name}</p>
                          <p className="text-xs text-gray-400">{employee.department}</p>
                        </div>
                      </label>
                    )) : (
                      <p className="px-4 py-3 text-sm text-gray-500">Nenhum colaborador encontrado</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Resumo dos filtros selecionados */}
          {hasActiveFilters && (
            <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-sm font-medium text-blue-700 dark:text-blue-300">📊 Filtros ativos:</span>
                {selectedPeriodNames.map(name => (
                  <span key={name} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 rounded-full">
                    {name}
                  </span>
                ))}
                {selectedDepartments.map(name => (
                  <span key={name} className="px-2 py-1 text-xs bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-200 rounded-full">
                    {name}
                  </span>
                ))}
                {selectedEmployeeNames.slice(0, 3).map(name => (
                  <span key={name} className="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-200 rounded-full">
                    {name}
                  </span>
                ))}
                {selectedEmployeeNames.length > 3 && (
                  <span className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
                    +{selectedEmployeeNames.length - 3} mais
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Área de conteúdo exportável */}
        <div ref={exportRef}>

        {/* Dashboard de Totalizadores Gerais */}
        {!hasActiveFilters && (
          <div className={`${config.classes.card} p-5 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-sm font-semibold ${config.classes.text} mb-4 flex items-center gap-2`}>
              📊 Totalizadores Consolidados
              <span className={`text-xs font-normal px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400`}>
                {totals?.total_periods || 0} períodos • {totals?.total_employees || 0} colaboradores
              </span>
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {/* Proventos */}
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <p className="text-xs text-green-600 dark:text-green-400 font-medium">💰 Total Proventos</p>
                <p className="text-lg font-bold text-green-700 dark:text-green-300 mt-1">
                  R$ {(totals?.total_proventos || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-green-600/70 dark:text-green-400/70 mt-1">
                  Média: R$ {((totals?.total_proventos || 0) / (totals?.total_periods || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              {/* Descontos */}
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <p className="text-xs text-red-600 dark:text-red-400 font-medium">📉 Total Descontos</p>
                <p className="text-lg font-bold text-red-700 dark:text-red-300 mt-1">
                  R$ {(totals?.total_descontos || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-red-600/70 dark:text-red-400/70 mt-1">
                  Média: R$ {((totals?.total_descontos || 0) / (totals?.total_periods || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              {/* Líquido */}
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">💵 Total Líquido</p>
                <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300 mt-1">
                  R$ {(totals?.total_liquido || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-emerald-600/70 dark:text-emerald-400/70 mt-1">
                  Média: R$ {((totals?.total_liquido || 0) / (totals?.total_periods || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              {/* INSS */}
              <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
                <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">🏛️ Total INSS</p>
                <p className="text-lg font-bold text-purple-700 dark:text-purple-300 mt-1">
                  R$ {(totals?.total_inss || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-purple-600/70 dark:text-purple-400/70 mt-1">
                  Média: R$ {((totals?.total_inss || 0) / (totals?.total_periods || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              {/* FGTS */}
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">🏦 Total FGTS</p>
                <p className="text-lg font-bold text-blue-700 dark:text-blue-300 mt-1">
                  R$ {(totals?.total_fgts || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-blue-600/70 dark:text-blue-400/70 mt-1">
                  Média: R$ {((totals?.total_fgts || 0) / (totals?.total_periods || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>

              {/* IRRF */}
              <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
                <p className="text-xs text-orange-600 dark:text-orange-400 font-medium">📋 Total IRRF</p>
                <p className="text-lg font-bold text-orange-700 dark:text-orange-300 mt-1">
                  R$ {(totals?.total_irrf || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-orange-600/70 dark:text-orange-400/70 mt-1">
                  Média: R$ {((totals?.total_irrf || 0) / (totals?.total_periods || 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Detalhes das Estatísticas */}
        {displayStats && (
          <>
            {/* Cards Principais de Folha */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                📊 Resumo {hasActiveFilters ? 'Filtrado' : displayStats.period_name ? `- ${displayStats.period_name}` : 'do Período'}
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-blue-50 dark:bg-blue-900/20`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>👥 Funcionários</p>
                  <p className={`text-3xl font-bold ${config.classes.text} mt-2`}>
                    {displayStats.total_employees}
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-green-50 dark:bg-green-900/20`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💰 Total Proventos</p>
                  <p className="text-2xl font-bold text-green-700 dark:text-green-400 mt-2">
                    R$ {displayStats.total_proventos.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-red-50 dark:bg-red-900/20`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>📉 Total Descontos</p>
                  <p className="text-2xl font-bold text-red-700 dark:text-red-400 mt-2">
                    R$ {displayStats.total_descontos.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-emerald-50 dark:bg-emerald-900/20`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💵 Total Líquido</p>
                  <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-2">
                    R$ {displayStats.total_liquido.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>
              </div>
            </div>

            {/* Salários */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                💼 Informações Salariais
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💰 Total Valor Salário</p>
                  <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>
                    R$ {displayStats.total_valor_salario.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>📊 Salário Médio</p>
                  <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>
                    R$ {displayStats.avg_salario.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💰 Média de Líquido</p>
                  <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>
                    R$ {(displayStats.avg_liquido || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Por funcionário/período
                  </p>
                </div>
              </div>
            </div>

            {/* Status dos Colaboradores */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <div className="flex items-center justify-between mb-6">
                <h3 className={`text-lg font-semibold ${config.classes.text}`}>
                  👥 Status dos Colaboradores
                </h3>
                <div className="flex items-center gap-2">
                  {displayStats.period_name === 'Todos os Períodos' && (
                    <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 px-2 py-1 rounded">
                      ℹ️ Média de todos os períodos
                    </span>
                  )}
                  {filteredStats && selectedPeriods.length > 1 && (
                    <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-2 py-1 rounded">
                      ℹ️ Status em {filteredStats.most_recent_period ? `${String(filteredStats.most_recent_period.month).padStart(2, '0')}/${filteredStats.most_recent_period.year}` : 'período mais recente'}
                    </span>
                  )}
                  {filteredStats && selectedPeriods.length > 0 && (
                    <button
                      onClick={loadDebugData}
                      className="text-xs bg-yellow-100 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:hover:bg-yellow-900/50 text-yellow-700 dark:text-yellow-400 px-3 py-1 rounded transition-colors"
                    >
                      🔍 Ver Detalhes
                    </button>
                  )}
                </div>
              </div>
              
              {/* Lógica condicional de exibição dos cards de status */}
              {/* SEMPRE usa novo layout: Linha 1 (3 cards principais) + Linha 2 (2 cards secundários quando aplicável) */}
              <>
                {/* Linha 1: Principais indicadores - SEMPRE exibido */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className={`border rounded-lg p-4 ${config.classes.border} bg-green-50 dark:bg-green-900/20`}>
                    <p className={`text-sm font-medium text-green-700 dark:text-green-400`}>👷 Trabalhando</p>
                    <p className="text-3xl font-bold text-green-700 dark:text-green-300 mt-2">
                      {displayStats.trabalhando || 0}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {displayStats.total_employees > 0 ? ((displayStats.trabalhando || 0) / displayStats.total_employees * 100).toFixed(1) : 0}% do total
                    </p>
                  </div>

                  <div className={`border rounded-lg p-4 ${config.classes.border} bg-blue-50 dark:bg-blue-900/20`}>
                    <p className={`text-sm font-medium text-blue-700 dark:text-blue-400`}>✨ Contratados</p>
                    <p className="text-3xl font-bold text-blue-700 dark:text-blue-300 mt-2">
                      {displayStats.contratados || 0}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      No período selecionado
                    </p>
                  </div>

                  <div className={`border rounded-lg p-4 ${config.classes.border} bg-red-50 dark:bg-red-900/20`}>
                    <p className={`text-sm font-medium text-red-700 dark:text-red-400`}>📤 Desligados</p>
                    <p className="text-3xl font-bold text-red-700 dark:text-red-300 mt-2">
                      {displayStats.demitidos || 0}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {displayStats.total_employees > 0 ? ((displayStats.demitidos || 0) / displayStats.total_employees * 100).toFixed(1) : 0}% do total
                    </p>
                  </div>
                </div>
                
                {/* Linha 2: Férias e Afastados (apenas quando visualizando período único - com ou sem seleção explícita) */}
                {(selectedPeriods.length === 1 || (selectedPeriods.length === 0 && displayStats.period_name !== 'Todos os Períodos')) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div className={`border rounded-lg p-4 ${config.classes.border} bg-blue-50 dark:bg-blue-900/20`}>
                      <p className={`text-sm font-medium text-blue-700 dark:text-blue-400`}>🏖️ Férias</p>
                      <p className="text-3xl font-bold text-blue-700 dark:text-blue-300 mt-2">
                        {displayStats.ferias || 0}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {displayStats.total_employees > 0 ? ((displayStats.ferias || 0) / displayStats.total_employees * 100).toFixed(1) : 0}% do total
                      </p>
                    </div>

                    <div className={`border rounded-lg p-4 ${config.classes.border} bg-yellow-50 dark:bg-yellow-900/20`}>
                      <p className={`text-sm font-medium text-yellow-700 dark:text-yellow-400`}>🏥 Afastados</p>
                      <p className="text-3xl font-bold text-yellow-700 dark:text-yellow-300 mt-2">
                        {displayStats.afastados || 0}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {displayStats.total_employees > 0 ? ((displayStats.afastados || 0) / displayStats.total_employees * 100).toFixed(1) : 0}% do total
                      </p>
                    </div>
                  </div>
                )}
              </>
            </div>

            {/* Encargos e Benefícios */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                📑 Encargos, Impostos e Benefícios
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-purple-50 dark:bg-purple-900/20`}>
                  <p className={`text-sm font-medium text-purple-700 dark:text-purple-400`}>🏛️ INSS</p>
                  <p className="text-2xl font-bold text-purple-700 dark:text-purple-300 mt-2">
                    R$ {(displayStats.total_inss || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {displayStats.total_proventos > 0 ? (((displayStats.total_inss || 0) / displayStats.total_proventos) * 100).toFixed(1) : 0}% dos proventos
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-orange-50 dark:bg-orange-900/20`}>
                  <p className={`text-sm font-medium text-orange-700 dark:text-orange-400`}>📋 IRRF</p>
                  <p className="text-2xl font-bold text-orange-700 dark:text-orange-300 mt-2">
                    R$ {(displayStats.total_irrf || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {displayStats.total_proventos > 0 ? (((displayStats.total_irrf || 0) / displayStats.total_proventos) * 100).toFixed(1) : 0}% dos proventos
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-indigo-50 dark:bg-indigo-900/20`}>
                  <p className={`text-sm font-medium text-indigo-700 dark:text-indigo-400`}>🏦 FGTS</p>
                  <p className="text-2xl font-bold text-indigo-700 dark:text-indigo-300 mt-2">
                    R$ {(displayStats.total_fgts || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {displayStats.total_proventos > 0 ? (((displayStats.total_fgts || 0) / displayStats.total_proventos) * 100).toFixed(1) : 0}% dos proventos
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-blue-50 dark:bg-blue-900/20`}>
                  <p className={`text-sm font-medium text-blue-700 dark:text-blue-400`}>💊 Plano de Saúde</p>
                  <p className="text-2xl font-bold text-blue-700 dark:text-blue-300 mt-2">
                    R$ {(displayStats.total_plano_saude || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Benefício total
                  </p>
                </div>
              </div>
            </div>

            {/* Horas Extras Segmentadas */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                ⏰ Horas Extras Detalhadas
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* HE 50% */}
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-blue-50 dark:bg-blue-900/20`}>
                  <p className={`text-sm font-medium text-blue-700 dark:text-blue-400 mb-2`}>⏰ HE 50%</p>
                  <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                    R$ {((displayStats.total_he_50_diurnas || 0) + (displayStats.total_he_50_noturnas || 0)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      ☀️ Diurnas: R$ {(displayStats.total_he_50_diurnas || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      🌙 Noturnas: R$ {(displayStats.total_he_50_noturnas || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-blue-600 dark:text-blue-400 font-medium mt-1">
                      {displayStats.total_proventos > 0 ? ((((displayStats.total_he_50_diurnas || 0) + (displayStats.total_he_50_noturnas || 0)) / displayStats.total_proventos) * 100).toFixed(2) : 0}% dos proventos
                    </p>
                  </div>
                </div>

                {/* HE 60% */}
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-purple-50 dark:bg-purple-900/20`}>
                  <p className={`text-sm font-medium text-purple-700 dark:text-purple-400 mb-2`}>⏰ HE 60%</p>
                  <p className="text-2xl font-bold text-purple-700 dark:text-purple-300">
                    R$ {(displayStats.total_he_60 || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                    Horas extras com adicional de 60%
                  </p>
                  <p className="text-xs text-purple-600 dark:text-purple-400 font-medium mt-1">
                    {displayStats.total_proventos > 0 ? (((displayStats.total_he_60 || 0) / displayStats.total_proventos) * 100).toFixed(2) : 0}% dos proventos
                  </p>
                </div>

                {/* HE 100% */}
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-orange-50 dark:bg-orange-900/20`}>
                  <p className={`text-sm font-medium text-orange-700 dark:text-orange-400 mb-2`}>⏰ HE 100%</p>
                  <p className="text-2xl font-bold text-orange-700 dark:text-orange-300">
                    R$ {((displayStats.total_he_100_diurnas || 0) + (displayStats.total_he_100_noturnas || 0)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      ☀️ Diurnas: R$ {(displayStats.total_he_100_diurnas || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      🌙 Noturnas: R$ {(displayStats.total_he_100_noturnas || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-orange-600 dark:text-orange-400 font-medium mt-1">
                      {displayStats.total_proventos > 0 ? ((((displayStats.total_he_100_diurnas || 0) + (displayStats.total_he_100_noturnas || 0)) / displayStats.total_proventos) * 100).toFixed(2) : 0}% dos proventos
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Adicional Noturno */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                🌙 Adicional Noturno
              </h3>
              
              <div className="grid grid-cols-1 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-indigo-50 dark:bg-indigo-900/20`}>
                  <p className={`text-sm font-medium text-indigo-700 dark:text-indigo-400`}>💰 Valor Total</p>
                  <p className="text-3xl font-bold text-indigo-700 dark:text-indigo-300 mt-2">
                    R$ {(displayStats.total_adicional_noturno || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Total de adicional noturno pago
                  </p>
                  <p className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mt-1">
                    {displayStats.total_proventos > 0 ? (((displayStats.total_adicional_noturno || 0) / displayStats.total_proventos) * 100).toFixed(2) : 0}% dos proventos
                  </p>
                </div>
              </div>
            </div>

            {/* Gratificações */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                🎁 Gratificações
              </h3>
              
              <div className="grid grid-cols-1 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-teal-50 dark:bg-teal-900/20`}>
                  <p className={`text-sm font-medium text-teal-700 dark:text-teal-400`}>💰 Total de Gratificações</p>
                  <p className="text-3xl font-bold text-teal-700 dark:text-teal-300 mt-2">
                    R$ {(displayStats.total_gratificacoes || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Gratificação de Função + Gratificação de Função 20%
                  </p>
                </div>
              </div>
            </div>

            {/* Adicionais Legais */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                ⚠️ Adicionais de Risco
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-red-50 dark:bg-red-900/20`}>
                  <p className={`text-sm font-medium text-red-700 dark:text-red-400`}>⚠️ Periculosidade</p>
                  <p className="text-2xl font-bold text-red-700 dark:text-red-300 mt-2">
                    R$ {(displayStats.total_periculosidade || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>

                <div className={`border rounded-lg p-4 ${config.classes.border} bg-yellow-50 dark:bg-yellow-900/20`}>
                  <p className={`text-sm font-medium text-yellow-700 dark:text-yellow-400`}>⚠️ Insalubridade</p>
                  <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-300 mt-2">
                    R$ {(displayStats.total_insalubridade || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>
              </div>
            </div>

            {/* Vale Transporte */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>
                🚌 Vale Transporte
              </h3>
              
              <div className="grid grid-cols-1 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border} bg-cyan-50 dark:bg-cyan-900/20`}>
                  <p className={`text-sm font-medium text-cyan-700 dark:text-cyan-400`}>💰 Valor Total</p>
                  <p className="text-3xl font-bold text-cyan-700 dark:text-cyan-300 mt-2">
                    R$ {(displayStats.total_vale_transporte || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Total de vale transporte descontado
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Tabela Comparativa */}
        {financial_stats && financial_stats.length > 0 && (() => {
          // Manter ordem original (mais recente primeiro)
          const sortedPeriods = [...financial_stats];
          return (
          <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
              Comparativo de Todos os Períodos
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className={config.classes.background}>
                  <tr>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                      Período
                    </th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                      Funcionários
                    </th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                      Proventos
                    </th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                      Descontos
                    </th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                      Líquido
                    </th>
                  </tr>
                </thead>
                <tbody className={`${config.classes.card} divide-y ${config.classes.border}`}>
                  {sortedPeriods.map((period, index) => {
                    const nextPeriod = index < sortedPeriods.length - 1 ? sortedPeriods[index + 1] : null;
                    const empChange = nextPeriod ? period.total_employees - nextPeriod.total_employees : 0;
                    const provChange = nextPeriod ? ((period.total_proventos - nextPeriod.total_proventos) / nextPeriod.total_proventos) * 100 : 0;
                    const descChange = nextPeriod ? ((period.total_descontos - nextPeriod.total_descontos) / nextPeriod.total_descontos) * 100 : 0;
                    const liqChange = nextPeriod ? ((period.total_liquido - nextPeriod.total_liquido) / nextPeriod.total_liquido) * 100 : 0;
                    
                    return (
                      <tr key={period.period_id} className={config.classes.cardHover}>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                          {period.period_name}
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                          <div className="flex items-center gap-2">
                            {period.total_employees}
                            {nextPeriod && empChange !== 0 && (
                              <span className={empChange > 0 ? 'text-green-600' : 'text-red-600'}>
                                {empChange > 0 ? '↑' : '↓'} {Math.abs(empChange)}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                          <div className="flex flex-col">
                            <span>R$ {period.total_proventos.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            {nextPeriod && provChange !== 0 && (
                              <span className={`text-xs ${provChange > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {provChange > 0 ? '↑' : '↓'} {Math.abs(provChange).toFixed(1)}%
                              </span>
                            )}
                          </div>
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                          <div className="flex flex-col">
                            <span>R$ {period.total_descontos.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            {nextPeriod && descChange !== 0 && (
                              <span className={`text-xs ${descChange > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                {descChange > 0 ? '↑' : '↓'} {Math.abs(descChange).toFixed(1)}%
                              </span>
                            )}
                          </div>
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                          <div className="flex flex-col">
                            <span>R$ {period.total_liquido.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            {nextPeriod && liqChange !== 0 && (
                              <span className={`text-xs ${liqChange > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {liqChange > 0 ? '↑' : '↓'} {Math.abs(liqChange).toFixed(1)}%
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          );
        })()}
        </div> {/* Fecha exportRef */}
        </div> {/* Fecha space-y-6 */}
      </div> {/* Fecha max-w-7xl */}
    </div> {/* Fecha min-h-screen */}
  );
};

export default RHIndicators;
