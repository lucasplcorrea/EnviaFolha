import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  CurrencyDollarIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  DocumentArrowDownIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';
import { LoadingSpinner, EmptyState, formatCurrency, calcPercentage } from './components';

const Payroll = () => {
  const { config, theme } = useTheme();
  const isDarkMode = theme === 'dark';
  
  // Estados principais
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  
  // Estados de filtros
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [availableEmployees, setAvailableEmployees] = useState([]);
  const [availableDepartments, setAvailableDepartments] = useState([]);
  const [filteredStats, setFilteredStats] = useState(null);
  
  // Estados de filtros de 13º salário
  const [include13Salary, setInclude13Salary] = useState(true); // Incluir valores de 13º
  const [only13Salary, setOnly13Salary] = useState(false); // Mostrar somente 13º
  
  // Estados de UI
  const [showPeriodDropdown, setShowPeriodDropdown] = useState(false);
  const [showDepartmentDropdown, setShowDepartmentDropdown] = useState(false);
  const [showEmployeeDropdown, setShowEmployeeDropdown] = useState(false);
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  
  // Refs
  const exportRef = useRef(null);
  const exportDropdownRef = useRef(null);

  // Carregar dados principais
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/payroll/statistics');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar folha:', error);
      toast.error('Erro ao carregar estatísticas da folha');
    } finally {
      setLoading(false);
    }
  }, []);

  // Carregar filtros
  const loadFiltersData = useCallback(async () => {
    try {
      const [employeesRes, departmentsRes] = await Promise.all([
        api.get('/payroll/employees'),
        api.get('/payroll/divisions')
      ]);
      setAvailableEmployees(employeesRes.data.employees || []);
      setAvailableDepartments(departmentsRes.data.departments || []);
    } catch (error) {
      console.error('Erro ao carregar filtros:', error);
    }
  }, []);

  // Carregar estatísticas filtradas
  const loadFilteredStatistics = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (selectedPeriods.length > 0) params.append('periods', selectedPeriods.join(','));
      if (selectedDepartments.length > 0) params.append('divisions', selectedDepartments.join(','));
      if (selectedEmployees.length > 0) params.append('employees', selectedEmployees.join(','));
      
      const response = await api.get(`/payroll/statistics-filtered?${params.toString()}`);
      setFilteredStats(response.data.stats);
    } catch (error) {
      console.error('Erro ao filtrar:', error);
      toast.error('Erro ao aplicar filtros');
    }
  }, [selectedPeriods, selectedDepartments, selectedEmployees]);

  // Effects
  useEffect(() => {
    loadData();
    loadFiltersData();
  }, [loadData, loadFiltersData]);

  useEffect(() => {
    if (selectedPeriods.length > 0 || selectedDepartments.length > 0 || selectedEmployees.length > 0) {
      loadFilteredStatistics();
    } else {
      setFilteredStats(null);
    }
  }, [selectedPeriods, selectedDepartments, selectedEmployees, loadFilteredStatistics]);

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (exportDropdownRef.current && !exportDropdownRef.current.contains(event.target)) {
        setShowExportDropdown(false);
      }
    };
    if (showExportDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExportDropdown]);

  // Handlers
  const clearFilters = () => {
    setSelectedPeriods([]);
    setSelectedDepartments([]);
    setSelectedEmployees([]);
    setFilteredStats(null);
    setEmployeeSearch('');
  };

  const togglePeriodSelection = (periodId) => {
    setSelectedPeriods(prev => 
      prev.includes(periodId) ? prev.filter(id => id !== periodId) : [...prev, periodId]
    );
  };

  const toggleDepartmentSelection = (deptName) => {
    setSelectedDepartments(prev => {
      const newSelection = prev.includes(deptName) 
        ? prev.filter(name => name !== deptName) 
        : [...prev, deptName];
      
      if (newSelection.length > 0) {
        const validEmployeeIds = availableEmployees
          .filter(emp => newSelection.includes(emp.department))
          .map(emp => emp.id);
        setSelectedEmployees(current => current.filter(id => validEmployeeIds.includes(id)));
      }
      return newSelection;
    });
  };

  const toggleEmployeeSelection = (employeeId) => {
    setSelectedEmployees(prev =>
      prev.includes(employeeId) ? prev.filter(id => id !== employeeId) : [...prev, employeeId]
    );
  };

  // Funções de exportação
  const exportCurrentView = async () => {
    try {
      setShowExportDropdown(false);
      const loadingToast = toast.loading('📄 Gerando PDF...');
      
      if (!exportRef.current) {
        toast.dismiss(loadingToast);
        toast.error('Erro ao capturar tela');
        return;
      }

      const canvas = await html2canvas(exportRef.current, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: isDarkMode ? '#1F2937' : '#FFFFFF'
      });

      const pdf = new jsPDF('p', 'mm', 'a4');
      const imgWidth = 210;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= 297;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= 297;
      }

      pdf.save(`folha_pagamento_${new Date().toISOString().split('T')[0]}.pdf`);
      toast.dismiss(loadingToast);
      toast.success('✅ PDF exportado!');
    } catch (error) {
      console.error('Erro:', error);
      toast.error('❌ Erro ao gerar PDF');
    }
  };

  const exportToExcel = () => {
    try {
      setShowExportDropdown(false);
      const loadingToast = toast.loading('📗 Gerando Excel...');

      const stats = displayStats || {};
      const wb = XLSX.utils.book_new();

      const resumoData = [
        ['RELATÓRIO DE FOLHA DE PAGAMENTO'],
        ['Gerado em:', new Date().toLocaleString('pt-BR')],
        [],
        ['RESUMO'],
        ['Total de Colaboradores', stats.total_employees || 0],
        ['Total Proventos', stats.total_proventos || 0],
        ['Total Descontos', stats.total_descontos || 0],
        ['Total Líquido', stats.total_liquido || 0],
        [],
        ['ENCARGOS'],
        ['INSS', stats.total_inss || 0],
        ['IRRF', stats.total_irrf || 0],
        ['FGTS', stats.total_fgts || 0],
      ];

      const ws = XLSX.utils.aoa_to_sheet(resumoData);
      XLSX.utils.book_append_sheet(wb, ws, 'Resumo');

      XLSX.writeFile(wb, `folha_${new Date().toISOString().split('T')[0]}.xlsx`);
      toast.dismiss(loadingToast);
      toast.success('✅ Excel exportado!');
    } catch (error) {
      console.error('Erro:', error);
      toast.error('❌ Erro ao gerar Excel');
    }
  };

  // Render
  if (loading) {
    return <LoadingSpinner message="Carregando estatísticas da folha..." />;
  }

  if (!data?.success) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado de folha disponível" />;
  }

  const { periods, financial_stats, totals } = data;
  
  // Calcular displayStats
  const displayStats = filteredStats || 
    (financial_stats && financial_stats.length > 0 ? {
      period_name: 'Consolidado de Todos os Períodos',
      total_employees: totals?.total_employees || 0,
      total_periods: totals?.total_periods || financial_stats.length,
      total_proventos: totals?.total_proventos || 0,
      total_descontos: totals?.total_descontos || 0,
      total_liquido: totals?.total_liquido || 0,
      total_inss: totals?.total_inss || 0,
      total_irrf: totals?.total_irrf || 0,
      total_fgts: totals?.total_fgts || 0,
      total_valor_salario: totals?.total_salarios || 0,
      // Usar médias calculadas do backend ao invés de dividir totais
      avg_salario: financial_stats.reduce((sum, p) => sum + (p.avg_salario || 0), 0) / financial_stats.length,
      avg_liquido: financial_stats.reduce((sum, p) => sum + (p.avg_liquido || 0), 0) / financial_stats.length,
      total_he_50_diurnas: financial_stats.reduce((sum, p) => sum + (p.total_he_50_diurnas || 0), 0),
      total_he_50_noturnas: financial_stats.reduce((sum, p) => sum + (p.total_he_50_noturnas || 0), 0),
      total_he_60: financial_stats.reduce((sum, p) => sum + (p.total_he_60 || 0), 0),
      total_he_100_diurnas: financial_stats.reduce((sum, p) => sum + (p.total_he_100_diurnas || 0), 0),
      total_he_100_noturnas: financial_stats.reduce((sum, p) => sum + (p.total_he_100_noturnas || 0), 0),
      total_adicional_noturno: financial_stats.reduce((sum, p) => sum + (p.total_adicional_noturno || 0), 0),
      total_gratificacoes: financial_stats.reduce((sum, p) => sum + (p.total_gratificacoes || 0), 0),
      total_13_salario: financial_stats.reduce((sum, p) => sum + (p.total_13_salario || 0), 0),
      total_ferias_pagas: financial_stats.reduce((sum, p) => sum + (p.total_ferias_pagas || 0), 0),
      total_periculosidade: financial_stats.reduce((sum, p) => sum + (p.total_periculosidade || 0), 0),
      total_insalubridade: financial_stats.reduce((sum, p) => sum + (p.total_insalubridade || 0), 0),
      total_plano_saude: totals?.total_plano_saude || 0,
      total_vale_transporte: financial_stats.reduce((sum, p) => sum + (p.total_vale_transporte || 0), 0),
      trabalhando: Math.round(financial_stats.reduce((sum, p) => sum + (p.trabalhando || 0), 0) / financial_stats.length),
      ferias: Math.round(financial_stats.reduce((sum, p) => sum + (p.ferias || 0), 0) / financial_stats.length),
      afastados: Math.round(financial_stats.reduce((sum, p) => sum + (p.afastados || 0), 0) / financial_stats.length),
      demitidos: Math.round(financial_stats.reduce((sum, p) => sum + (p.demitidos || 0), 0) / financial_stats.length),
      contratados: financial_stats.reduce((sum, p) => sum + (p.contratados || 0), 0),
    } : null);

  const hasActiveFilters = selectedPeriods.length > 0 || selectedDepartments.length > 0 || selectedEmployees.length > 0;
  const selectedPeriodNames = periods?.filter(p => selectedPeriods.includes(p.id)).map(p => p.period_name) || [];
  const selectedEmployeeNames = availableEmployees?.filter(e => selectedEmployees.includes(e.id)).map(e => e.name) || [];
  
  const filteredEmployeesList = availableEmployees
    .filter(emp => selectedDepartments.length === 0 || selectedDepartments.includes(emp.department))
    .filter(emp => emp.name.toLowerCase().includes(employeeSearch.toLowerCase()) || emp.unique_id.includes(employeeSearch));

  // Ajustar displayStats baseado nos filtros de 13º salário
  const adjustedStats = React.useMemo(() => {
    if (!displayStats) return null;
    
    const stats = { ...displayStats };
    
    // Se "Somente 13º" está ativo, zerar tudo exceto 13º e férias
    if (only13Salary) {
      // Zerar valores que NÃO são de 13º/férias
      stats.total_salario_base = 0;
      stats.total_gratificacoes = 0;
      stats.total_periculosidade = 0;
      stats.total_insalubridade = 0;
      stats.total_adicional_noturno = 0;
      stats.total_he_50_diurnas = 0;
      stats.total_he_50_noturnas = 0;
      stats.total_he_60 = 0;
      stats.total_he_100_diurnas = 0;
      stats.total_he_100_noturnas = 0;
      stats.total_vale_transporte = 0;
      stats.total_plano_saude = 0;
      
      // Manter apenas valores de 13º e férias
      // (os campos total_13_* e total_ferias_* ficam intocados)
    }
    // Se "Incluir 13º" está DESATIVADO, zerar valores de 13º
    else if (!include13Salary) {
      stats.total_13_adiantamento = 0;
      stats.total_13_integral = 0;
      stats.total_13_maternidade_gps = 0;
      stats.total_13_med_eventos = 0;
      stats.total_13_med_horas_extras = 0;
      stats.total_13_gratif_adiantamento = 0;
      stats.total_13_gratif_integral = 0;
      stats.total_13_salario = 0; // Gratificações antigas
      stats.total_ferias_base = 0;
      stats.total_ferias_abono_1_3 = 0;
      stats.total_ferias_med_horas_extras = 0;
      stats.total_ferias_pagas = 0; // Gratificações antigas
      stats.total_desconto_13_adiantamento = 0;
      stats.total_desconto_ferias_adiantamento = 0;
    }
    
    return stats;
  }, [displayStats, include13Salary, only13Salary]);

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className={`text-lg font-semibold ${config.classes.text}`}>🔍 Filtros de Análise</h3>
            <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
              Selecione períodos, departamentos ou colaboradores
            </p>
          </div>
          <div className="flex gap-3">
            {/* Botão Exportar */}
            <div className="relative" ref={exportDropdownRef}>
              <button
                onClick={() => setShowExportDropdown(!showExportDropdown)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                <DocumentArrowDownIcon className="w-5 h-5" />
                Exportar
                <ChevronDownIcon className={`w-4 h-4 transition-transform ${showExportDropdown ? 'rotate-180' : ''}`} />
              </button>
              
              {showExportDropdown && (
                <div className={`absolute right-0 mt-2 w-64 ${config.classes.card} rounded-lg shadow-xl border ${config.classes.border} z-30`}>
                  <div className="py-2">
                    <button
                      onClick={exportCurrentView}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 ${config.classes.text}`}
                    >
                      📄 Exportar PDF
                    </button>
                    <button
                      onClick={exportToExcel}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 ${config.classes.text}`}
                    >
                      📗 Exportar Excel
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            {hasActiveFilters && (
              <button onClick={clearFilters} className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg">
                ✕ Limpar Filtros
              </button>
            )}
          </div>
        </div>

        {/* Dropdowns de Filtro */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Períodos */}
          <div className="relative">
            <button
              onClick={() => { setShowPeriodDropdown(!showPeriodDropdown); setShowDepartmentDropdown(false); setShowEmployeeDropdown(false); }}
              className={`w-full px-4 py-3 text-left rounded-lg border-2 transition-all ${
                selectedPeriods.length > 0 ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : `${config.classes.border} ${config.classes.card}`
              }`}
            >
              <span className={`text-sm font-medium ${config.classes.text}`}>📅 Períodos</span>
              <p className={`text-xs ${config.classes.textSecondary} mt-1`}>
                {selectedPeriods.length > 0 ? `${selectedPeriods.length} selecionado(s)` : 'Todos'}
              </p>
            </button>
            
            {showPeriodDropdown && (
              <div className={`absolute z-20 w-full mt-2 ${config.classes.card} rounded-lg shadow-lg border ${config.classes.border} max-h-64 overflow-y-auto`}>
                <div className="p-2 border-b sticky top-0 bg-white dark:bg-gray-800">
                  <button onClick={() => setSelectedPeriods(periods?.map(p => p.id) || [])} className="text-xs text-blue-600 mr-3">
                    Selecionar todos
                  </button>
                  <button onClick={() => setSelectedPeriods([])} className="text-xs text-gray-500">Limpar</button>
                </div>
                {periods?.map(period => (
                  <label key={period.id} className={`flex items-center px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    selectedPeriods.includes(period.id) ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                  }`}>
                    <input type="checkbox" checked={selectedPeriods.includes(period.id)} onChange={() => togglePeriodSelection(period.id)} className="mr-3 h-4 w-4 text-blue-600 rounded" />
                    <span className={`flex-1 text-sm ${config.classes.text}`}>{period.period_name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Departamentos */}
          <div className="relative">
            <button
              onClick={() => { setShowDepartmentDropdown(!showDepartmentDropdown); setShowPeriodDropdown(false); setShowEmployeeDropdown(false); }}
              className={`w-full px-4 py-3 text-left rounded-lg border-2 transition-all ${
                selectedDepartments.length > 0 ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : `${config.classes.border} ${config.classes.card}`
              }`}
            >
              <span className={`text-sm font-medium ${config.classes.text}`}>🏢 Departamentos</span>
              <p className={`text-xs ${config.classes.textSecondary} mt-1`}>
                {selectedDepartments.length > 0 ? `${selectedDepartments.length} selecionado(s)` : 'Todos'}
              </p>
            </button>
            
            {showDepartmentDropdown && (
              <div className={`absolute z-20 w-full mt-2 ${config.classes.card} rounded-lg shadow-lg border ${config.classes.border} max-h-64 overflow-y-auto`}>
                <div className="p-2 border-b sticky top-0 bg-white dark:bg-gray-800">
                  <button onClick={() => setSelectedDepartments(availableDepartments?.map(d => d.name) || [])} className="text-xs text-green-600 mr-3">
                    Selecionar todos
                  </button>
                  <button onClick={() => setSelectedDepartments([])} className="text-xs text-gray-500">Limpar</button>
                </div>
                {availableDepartments?.map(dept => (
                  <label key={dept.name} className={`flex items-center px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    selectedDepartments.includes(dept.name) ? 'bg-green-50 dark:bg-green-900/30' : ''
                  }`}>
                    <input type="checkbox" checked={selectedDepartments.includes(dept.name)} onChange={() => toggleDepartmentSelection(dept.name)} className="mr-3 h-4 w-4 text-green-600 rounded" />
                    <span className={`flex-1 text-sm ${config.classes.text}`}>{dept.name}</span>
                    <span className="text-xs text-gray-400">{dept.total_employees}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Colaboradores */}
          <div className="relative">
            <button
              onClick={() => { setShowEmployeeDropdown(!showEmployeeDropdown); setShowPeriodDropdown(false); setShowDepartmentDropdown(false); }}
              className={`w-full px-4 py-3 text-left rounded-lg border-2 transition-all ${
                selectedEmployees.length > 0 ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' : `${config.classes.border} ${config.classes.card}`
              }`}
            >
              <span className={`text-sm font-medium ${config.classes.text}`}>👥 Colaboradores</span>
              <p className={`text-xs ${config.classes.textSecondary} mt-1`}>
                {selectedEmployees.length > 0 ? `${selectedEmployees.length} selecionado(s)` : 'Todos'}
              </p>
            </button>
            
            {showEmployeeDropdown && (
              <div className={`absolute z-20 w-full mt-2 ${config.classes.card} rounded-lg shadow-lg border ${config.classes.border} max-h-80 overflow-hidden`}>
                <div className="p-2 border-b sticky top-0 bg-white dark:bg-gray-800">
                  <input
                    type="text"
                    placeholder="🔎 Buscar..."
                    value={employeeSearch}
                    onChange={(e) => setEmployeeSearch(e.target.value)}
                    className={`w-full px-3 py-2 text-sm rounded border ${config.classes.border} ${config.classes.card}`}
                  />
                </div>
                <div className="max-h-52 overflow-y-auto">
                  {filteredEmployeesList.slice(0, 50).map(employee => (
                    <label key={employee.id} className={`flex items-center px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      selectedEmployees.includes(employee.id) ? 'bg-purple-50 dark:bg-purple-900/30' : ''
                    }`}>
                      <input type="checkbox" checked={selectedEmployees.includes(employee.id)} onChange={() => toggleEmployeeSelection(employee.id)} className="mr-3 h-4 w-4 text-purple-600 rounded" />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${config.classes.text} truncate`}>{employee.name}</p>
                        <p className="text-xs text-gray-400">{employee.department}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Toggles de 13º Salário */}
        <div className="mt-4 p-4 bg-gradient-to-r from-green-50 to-amber-50 dark:from-green-900/20 dark:to-amber-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex flex-wrap gap-4 items-center">
            <span className="text-sm font-semibold text-green-700 dark:text-green-300">🎄 Filtros de 13º e Férias:</span>
            
            {/* Toggle: Incluir valores de 13º */}
            <label className="flex items-center gap-2 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={include13Salary}
                  onChange={(e) => {
                    setInclude13Salary(e.target.checked);
                    if (!e.target.checked) setOnly13Salary(false); // Desativa "somente 13º" se desmarcar
                  }}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 dark:peer-focus:ring-green-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-green-600"></div>
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {include13Salary ? '✅ Incluir valores de 13º e férias' : '❌ Excluir valores de 13º e férias'}
              </span>
            </label>

            {/* Toggle: Exibir somente 13º */}
            <label className="flex items-center gap-2 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={only13Salary}
                  onChange={(e) => {
                    setOnly13Salary(e.target.checked);
                    if (e.target.checked) setInclude13Salary(true); // Ativa "incluir" se marcar "somente"
                  }}
                  disabled={!include13Salary}
                  className="sr-only peer disabled:opacity-50"
                />
                <div className={`w-11 h-6 ${!include13Salary ? 'opacity-50 cursor-not-allowed' : ''} bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 dark:peer-focus:ring-amber-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-amber-600`}></div>
              </div>
              <span className={`text-sm font-medium ${!include13Salary ? 'opacity-50' : ''} text-gray-700 dark:text-gray-300`}>
                {only13Salary ? '🎯 Exibindo somente 13º e férias' : '📊 Exibir somente 13º e férias'}
              </span>
            </label>
          </div>
          {only13Salary && (
            <p className="mt-2 text-xs text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30 px-3 py-1.5 rounded">
              ℹ️ Mostrando apenas valores relacionados a 13º salário e férias (todos os outros valores estão zerados)
            </p>
          )}
          {!include13Salary && (
            <p className="mt-2 text-xs text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-3 py-1.5 rounded">
              ℹ️ Valores de 13º salário e férias foram excluídos dos totalizadores
            </p>
          )}
        </div>

        {/* Tags de filtros ativos */}
        {hasActiveFilters && (
          <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg">
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">📊 Filtros:</span>
              {selectedPeriodNames.map(name => (
                <span key={name} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 rounded-full">{name}</span>
              ))}
              {selectedDepartments.map(name => (
                <span key={name} className="px-2 py-1 text-xs bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-200 rounded-full">{name}</span>
              ))}
              {selectedEmployeeNames.slice(0, 3).map(name => (
                <span key={name} className="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-200 rounded-full">{name}</span>
              ))}
              {selectedEmployeeNames.length > 3 && (
                <span className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">+{selectedEmployeeNames.length - 3}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Área exportável */}
      <div ref={exportRef} className="space-y-6">
        {/* Totalizadores */}
        {!hasActiveFilters && totals && (
          <div className={`${config.classes.card} p-5 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-sm font-semibold ${config.classes.text} mb-4 flex items-center gap-2`}>
              📊 Totalizadores Consolidados
              <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                {totals.total_periods || 0} períodos • {totals.total_employees || 0} colaboradores
              </span>
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <p className="text-xs text-green-600 dark:text-green-400 font-medium">💰 Total Proventos</p>
                <p className="text-lg font-bold text-green-700 dark:text-green-300 mt-1">R$ {formatCurrency(totals.total_proventos)}</p>
              </div>
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <p className="text-xs text-red-600 dark:text-red-400 font-medium">📉 Total Descontos</p>
                <p className="text-lg font-bold text-red-700 dark:text-red-300 mt-1">R$ {formatCurrency(totals.total_descontos)}</p>
              </div>
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">💵 Total Líquido</p>
                <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300 mt-1">R$ {formatCurrency(totals.total_liquido)}</p>
              </div>
              <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
                <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">🏛️ Total INSS</p>
                <p className="text-lg font-bold text-purple-700 dark:text-purple-300 mt-1">R$ {formatCurrency(totals.total_inss)}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">🏦 Total FGTS</p>
                <p className="text-lg font-bold text-blue-700 dark:text-blue-300 mt-1">R$ {formatCurrency(totals.total_fgts)}</p>
              </div>
              <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
                <p className="text-xs text-orange-600 dark:text-orange-400 font-medium">📋 Total IRRF</p>
                <p className="text-lg font-bold text-orange-700 dark:text-orange-300 mt-1">R$ {formatCurrency(totals.total_irrf)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Estatísticas do período/filtro */}
        {displayStats && (
          <>
            {/* Resumo Principal */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
                📊 {hasActiveFilters ? 'Resumo Filtrado' : adjustedStats.period_name || 'Resumo'}
              </h3>
              {!hasActiveFilters && displayStats.total_periods > 1 && (
                <p className={`text-xs ${config.classes.textSecondary} mb-4 flex items-center gap-2`}>
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full">
                    {adjustedStats.total_periods} períodos consolidados
                  </span>
                  <span>• Médias calculadas por período</span>
                </p>
              )}
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>👥 Funcionários</p>
                  <p className={`text-3xl font-bold ${config.classes.text} mt-2`}>{adjustedStats.total_employees}</p>
                </div>
                <div className="border rounded-lg p-4 bg-green-50 dark:bg-green-900/20">
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💰 Total Proventos</p>
                  <p className="text-2xl font-bold text-green-700 dark:text-green-400 mt-2">R$ {formatCurrency(adjustedStats.total_proventos)}</p>
                </div>
                <div className="border rounded-lg p-4 bg-red-50 dark:bg-red-900/20">
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>📉 Total Descontos</p>
                  <p className="text-2xl font-bold text-red-700 dark:text-red-400 mt-2">R$ {formatCurrency(adjustedStats.total_descontos)}</p>
                </div>
                <div className="border rounded-lg p-4 bg-emerald-50 dark:bg-emerald-900/20">
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💵 Total Líquido</p>
                  <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-2">R$ {formatCurrency(adjustedStats.total_liquido)}</p>
                </div>
              </div>
            </div>

            {/* Salários */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>💼 Informações Salariais</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className={`border rounded-lg p-4 ${config.classes.border}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💰 Total Salários Base</p>
                  <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>R$ {formatCurrency(adjustedStats.total_valor_salario)}</p>
                  <p className="text-xs text-gray-400 mt-1">Soma de todos os salários</p>
                </div>
                <div className={`border rounded-lg p-4 ${config.classes.border}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>📊 Salário Médio</p>
                  <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>R$ {formatCurrency(adjustedStats.avg_salario)}</p>
                  <p className="text-xs text-gray-400 mt-1">Média por funcionário</p>
                </div>
                <div className={`border rounded-lg p-4 ${config.classes.border}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>💵 Líquido Médio</p>
                  <p className={`text-2xl font-bold ${config.classes.text} mt-2`}>R$ {formatCurrency(adjustedStats.avg_liquido)}</p>
                  <p className="text-xs text-gray-400 mt-1">Média por funcionário</p>
                </div>
              </div>
            </div>

            {/* Adicionais e Benefícios */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>💎 Adicionais e Benefícios</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="border rounded-lg p-4 bg-amber-50 dark:bg-amber-900/20">
                  <p className="text-sm font-medium text-amber-700 dark:text-amber-400">🎁 Gratificações</p>
                  <p className="text-2xl font-bold text-amber-700 dark:text-amber-300 mt-2">R$ {formatCurrency(adjustedStats.total_gratificacoes)}</p>
                  <p className="text-xs text-gray-400 mt-1">Função e cargo</p>
                </div>
                <div className="border rounded-lg p-4 bg-green-50 dark:bg-green-900/20">
                  <p className="text-sm font-medium text-green-700 dark:text-green-400">🎄 13º Salário</p>
                  <p className="text-2xl font-bold text-green-700 dark:text-green-300 mt-2">
                    R$ {formatCurrency(
                      (adjustedStats.total_13_adiantamento || 0) +
                      (adjustedStats.total_13_integral || 0) +
                      (adjustedStats.total_13_maternidade_gps || 0) +
                      (adjustedStats.total_13_med_eventos || 0) +
                      (adjustedStats.total_13_med_horas_extras || 0) +
                      (adjustedStats.total_13_gratif_adiantamento || 0) +
                      (adjustedStats.total_13_gratif_integral || 0) +
                      (adjustedStats.total_13_salario || 0)
                    )}
                  </p>
                  {/* Breakdown detalhado */}
                  {(adjustedStats.total_13_adiantamento > 0 || displayStats.total_13_integral > 0) && (
                    <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-800">
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Detalhamento:</p>
                      {adjustedStats.total_13_adiantamento > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Adiant: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_13_adiantamento)}</span>
                        </p>
                      )}
                      {adjustedStats.total_13_integral > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Integral: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_13_integral)}</span>
                        </p>
                      )}
                      {adjustedStats.total_13_maternidade_gps > 0 && (
                        <p className="text-xs text-green-700 dark:text-green-400">
                          • Matern (GPS): <span className="font-medium">R$ {formatCurrency(adjustedStats.total_13_maternidade_gps)}</span>
                          <span className="text-[10px] ml-1">Gov</span>
                        </p>
                      )}
                      {adjustedStats.total_13_med_eventos > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Méd. Eventos: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_13_med_eventos)}</span>
                        </p>
                      )}
                      {adjustedStats.total_13_med_horas_extras > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Méd. HE: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_13_med_horas_extras)}</span>
                        </p>
                      )}
                      {(adjustedStats.total_13_gratif_adiantamento > 0 || displayStats.total_13_gratif_integral > 0) && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Gratif: <span className="font-medium">R$ {formatCurrency(
                            (adjustedStats.total_13_gratif_adiantamento || 0) + 
                            (adjustedStats.total_13_gratif_integral || 0)
                          )}</span>
                        </p>
                      )}
                    </div>
                  )}
                  {!(adjustedStats.total_13_adiantamento > 0 || displayStats.total_13_integral > 0) && (
                    <p className="text-xs text-gray-400 mt-1">Proporcional e abono</p>
                  )}
                </div>
                <div className="border rounded-lg p-4 bg-sky-50 dark:bg-sky-900/20">
                  <p className="text-sm font-medium text-sky-700 dark:text-sky-400">🏖️ Férias</p>
                  <p className="text-2xl font-bold text-sky-700 dark:text-sky-300 mt-2">
                    R$ {formatCurrency(
                      (adjustedStats.total_ferias_base || 0) +
                      (adjustedStats.total_ferias_abono_1_3 || 0) +
                      (adjustedStats.total_ferias_med_horas_extras || 0) +
                      (adjustedStats.total_ferias_pagas || 0)
                    )}
                  </p>
                  {/* Breakdown detalhado */}
                  {(adjustedStats.total_ferias_base > 0 || displayStats.total_ferias_abono_1_3 > 0) && (
                    <div className="mt-3 pt-3 border-t border-sky-200 dark:border-sky-800">
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">Detalhamento:</p>
                      {adjustedStats.total_ferias_base > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Base: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_ferias_base)}</span>
                        </p>
                      )}
                      {adjustedStats.total_ferias_abono_1_3 > 0 && (
                        <p className="text-xs text-sky-700 dark:text-sky-400">
                          • Abono 1/3: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_ferias_abono_1_3)}</span>
                          <span className="text-[10px] ml-1">CF/88</span>
                        </p>
                      )}
                      {adjustedStats.total_ferias_med_horas_extras > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Méd. HE: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_ferias_med_horas_extras)}</span>
                        </p>
                      )}
                      {adjustedStats.total_ferias_pagas > 0 && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          • Gratif: <span className="font-medium">R$ {formatCurrency(adjustedStats.total_ferias_pagas)}</span>
                        </p>
                      )}
                      {adjustedStats.total_desconto_ferias_adiantamento > 0 && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          • Desc. Adiant: <span className="font-medium">-R$ {formatCurrency(adjustedStats.total_desconto_ferias_adiantamento)}</span>
                        </p>
                      )}
                    </div>
                  )}
                  {!(adjustedStats.total_ferias_base > 0 || displayStats.total_ferias_abono_1_3 > 0) && (
                    <p className="text-xs text-gray-400 mt-1">Férias e proporcionais</p>
                  )}
                </div>
                <div className="border rounded-lg p-4 bg-orange-50 dark:bg-orange-900/20">
                  <p className="text-sm font-medium text-orange-700 dark:text-orange-400">⚠️ Periculosidade</p>
                  <p className="text-2xl font-bold text-orange-700 dark:text-orange-300 mt-2">R$ {formatCurrency(adjustedStats.total_periculosidade)}</p>
                  <p className="text-xs text-gray-400 mt-1">Adicional de risco</p>
                </div>
                <div className="border rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/20">
                  <p className="text-sm font-medium text-yellow-700 dark:text-yellow-400">🏥 Insalubridade</p>
                  <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-300 mt-2">R$ {formatCurrency(adjustedStats.total_insalubridade)}</p>
                  <p className="text-xs text-gray-400 mt-1">Condições adversas</p>
                </div>
              </div>
            </div>

            {/* Benefícios */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>🎫 Benefícios</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4 bg-cyan-50 dark:bg-cyan-900/20">
                  <p className="text-sm font-medium text-cyan-700 dark:text-cyan-400">🚌 Vale Transporte</p>
                  <p className="text-2xl font-bold text-cyan-700 dark:text-cyan-300 mt-2">R$ {formatCurrency(adjustedStats.total_vale_transporte)}</p>
                </div>
                <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
                  <p className="text-sm font-medium text-blue-700 dark:text-blue-400">💊 Plano de Saúde</p>
                  <p className="text-2xl font-bold text-blue-700 dark:text-blue-300 mt-2">R$ {formatCurrency(adjustedStats.total_plano_saude)}</p>
                  <p className="text-xs text-gray-400 mt-1">Assistência médica</p>
                </div>
              </div>
            </div>

            {/* Status dos Colaboradores */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>👥 Status dos Colaboradores</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="border rounded-lg p-4 bg-green-50 dark:bg-green-900/20">
                  <p className="text-sm font-medium text-green-700 dark:text-green-400">👷 Trabalhando</p>
                  <p className="text-3xl font-bold text-green-700 dark:text-green-300 mt-2">{adjustedStats.trabalhando || 0}</p>
                  <p className="text-xs text-gray-500 mt-1">{calcPercentage(adjustedStats.trabalhando, displayStats.total_employees)}% do total</p>
                </div>
                <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
                  <p className="text-sm font-medium text-blue-700 dark:text-blue-400">🏖️ Férias</p>
                  <p className="text-3xl font-bold text-blue-700 dark:text-blue-300 mt-2">{adjustedStats.ferias || 0}</p>
                  <p className="text-xs text-gray-500 mt-1">{calcPercentage(adjustedStats.ferias, displayStats.total_employees)}% do total</p>
                </div>
                <div className="border rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/20">
                  <p className="text-sm font-medium text-yellow-700 dark:text-yellow-400">🏥 Afastados</p>
                  <p className="text-3xl font-bold text-yellow-700 dark:text-yellow-300 mt-2">{adjustedStats.afastados || 0}</p>
                  <p className="text-xs text-gray-500 mt-1">{calcPercentage(adjustedStats.afastados, displayStats.total_employees)}% do total</p>
                </div>
                <div className="border rounded-lg p-4 bg-red-50 dark:bg-red-900/20">
                  <p className="text-sm font-medium text-red-700 dark:text-red-400">📤 Desligados</p>
                  <p className="text-3xl font-bold text-red-700 dark:text-red-300 mt-2">{adjustedStats.demitidos || 0}</p>
                  <p className="text-xs text-gray-500 mt-1">{calcPercentage(adjustedStats.demitidos, displayStats.total_employees)}% do total</p>
                </div>
              </div>
            </div>

            {/* Encargos */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>📑 Encargos Trabalhistas</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-purple-50 dark:bg-purple-900/20">
                  <p className="text-sm font-medium text-purple-700 dark:text-purple-400">🏛️ INSS</p>
                  <p className="text-2xl font-bold text-purple-700 dark:text-purple-300 mt-2">R$ {formatCurrency(adjustedStats.total_inss)}</p>
                  <p className="text-xs text-gray-400 mt-1">Previdência social</p>
                </div>
                <div className="border rounded-lg p-4 bg-orange-50 dark:bg-orange-900/20">
                  <p className="text-sm font-medium text-orange-700 dark:text-orange-400">📋 IRRF</p>
                  <p className="text-2xl font-bold text-orange-700 dark:text-orange-300 mt-2">R$ {formatCurrency(adjustedStats.total_irrf)}</p>
                  <p className="text-xs text-gray-400 mt-1">Imposto de renda</p>
                </div>
                <div className="border rounded-lg p-4 bg-indigo-50 dark:bg-indigo-900/20">
                  <p className="text-sm font-medium text-indigo-700 dark:text-indigo-400">🏦 FGTS</p>
                  <p className="text-2xl font-bold text-indigo-700 dark:text-indigo-300 mt-2">R$ {formatCurrency(adjustedStats.total_fgts)}</p>
                  <p className="text-xs text-gray-400 mt-1">Fundo de garantia</p>
                </div>
              </div>
            </div>

            {/* Horas Extras */}
            <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-6`}>⏰ Horas Extras</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
                  <p className="text-sm font-medium text-blue-700 dark:text-blue-400 mb-2">⏰ HE 50%</p>
                  <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                    R$ {formatCurrency((adjustedStats.total_he_50_diurnas || 0) + (adjustedStats.total_he_50_noturnas || 0))}
                  </p>
                </div>
                <div className="border rounded-lg p-4 bg-purple-50 dark:bg-purple-900/20">
                  <p className="text-sm font-medium text-purple-700 dark:text-purple-400 mb-2">⏰ HE 60%</p>
                  <p className="text-2xl font-bold text-purple-700 dark:text-purple-300">R$ {formatCurrency(adjustedStats.total_he_60)}</p>
                </div>
                <div className="border rounded-lg p-4 bg-orange-50 dark:bg-orange-900/20">
                  <p className="text-sm font-medium text-orange-700 dark:text-orange-400 mb-2">⏰ HE 100%</p>
                  <p className="text-2xl font-bold text-orange-700 dark:text-orange-300">
                    R$ {formatCurrency((adjustedStats.total_he_100_diurnas || 0) + (adjustedStats.total_he_100_noturnas || 0))}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Tabela Comparativa */}
        {financial_stats && financial_stats.length > 0 && (
          <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>📈 Comparativo de Períodos</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className={config.classes.background}>
                  <tr>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase`}>Período</th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase`}>Funcionários</th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase`}>Proventos</th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase`}>Descontos</th>
                    <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase`}>Líquido</th>
                  </tr>
                </thead>
                <tbody className={`${config.classes.card} divide-y ${config.classes.border}`}>
                  {[...financial_stats].reverse().map((period, index) => {
                    // Inverter índice para comparar corretamente (do mais antigo para o mais novo)
                    const reversedIndex = financial_stats.length - 1 - index;
                    const prevPeriod = reversedIndex > 0 ? financial_stats[reversedIndex - 1] : null;
                    
                    // Calcular variações percentuais
                    const getVariation = (current, previous) => {
                      if (!previous || previous === 0) return null;
                      return ((current - previous) / previous) * 100;
                    };
                    
                    const empVariation = prevPeriod ? getVariation(period.total_employees, prevPeriod.total_employees) : null;
                    const proventosVariation = prevPeriod ? getVariation(period.total_proventos, prevPeriod.total_proventos) : null;
                    const descontosVariation = prevPeriod ? getVariation(period.total_descontos, prevPeriod.total_descontos) : null;
                    const liquidoVariation = prevPeriod ? getVariation(period.total_liquido, prevPeriod.total_liquido) : null;
                    
                    const TrendIndicator = ({ variation }) => {
                      if (variation === null) return null;
                      const isPositive = variation > 0;
                      const isNeutral = Math.abs(variation) < 0.5;
                      
                      if (isNeutral) {
                        return <span className="text-xs text-gray-400 ml-1">→</span>;
                      }
                      
                      return (
                        <span className={`text-xs ml-1 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                          {isPositive ? '↑' : '↓'} {Math.abs(variation).toFixed(1)}%
                        </span>
                      );
                    };
                    
                    return (
                      <tr key={period.period_id} className={config.classes.cardHover}>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                          {period.period_name}
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                          {period.total_employees}
                          <TrendIndicator variation={empVariation} />
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                          R$ {formatCurrency(period.total_proventos)}
                          <TrendIndicator variation={proventosVariation} />
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                          R$ {formatCurrency(period.total_descontos)}
                          <TrendIndicator variation={descontosVariation} />
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                          R$ {formatCurrency(period.total_liquido)}
                          <TrendIndicator variation={liquidoVariation} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Payroll;
