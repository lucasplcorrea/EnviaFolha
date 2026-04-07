import React, { useState, useEffect, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import api from '../../services/api';
import toast from 'react-hot-toast';
import MultiSelect from '../../components/MultiSelect';
import ExportPDFButton from '../../components/ExportPDFButton';

/**
 * VERSÃO V2 - REFATORADA
 * Organizada nas 7 seções especificadas pelo RH
 * Sem filtros complexos de 13º (agora é período separado)
 */
const PayrollV2 = () => {
  const { config, theme } = useTheme();
  const isDarkMode = theme === 'dark';
  
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [timecardStats, setTimecardStats] = useState(null);
  const [showFilters, setShowFilters] = useState(true); // Controle de expansão dos filtros
  
  // Dados brutos dos filtros (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores)
  const [allCompanies, setAllCompanies] = useState([]);
  const [allPeriods, setAllPeriods] = useState([]);
  const [allYears, setAllYears] = useState([]);
  const [allMonths, setAllMonths] = useState([]);
  const [allDepartments, setAllDepartments] = useState([]);
  const [allEmployees, setAllEmployees] = useState([]);
  
  // Seleções (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores)
  const [selectedCompanies, setSelectedCompanies] = useState([]);
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [selectedYears, setSelectedYears] = useState([]);
  const [selectedMonths, setSelectedMonths] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);

  // Carregar filtros disponíveis
  useEffect(() => {
    loadFilters();
  }, []);

  // Carregar estatísticas quando mudar qualquer filtro
  useEffect(() => {
    if (selectedCompanies.length > 0 || selectedPeriods.length > 0 || selectedYears.length > 0 || selectedMonths.length > 0) {
      loadStatistics();
    }
  }, [selectedCompanies, selectedPeriods, selectedYears, selectedMonths, selectedDepartments, selectedEmployees]);

  // ============================================
  // FILTROS CASCATA (DRILL-THROUGH)
  // ============================================
  
  // Períodos filtrados baseado em ano/mês selecionado
  const filteredPeriods = useMemo(() => {
    let filtered = allPeriods;
    
    if (selectedYears.length > 0) {
      filtered = filtered.filter(p => selectedYears.includes(p.year));
    }
    
    if (selectedMonths.length > 0) {
      filtered = filtered.filter(p => selectedMonths.includes(p.month));
    }
    
    return filtered;
  }, [allPeriods, selectedYears, selectedMonths]);

  // Anos disponíveis baseado nos períodos selecionados
  const filteredYears = useMemo(() => {
    if (selectedPeriods.length > 0) {
      const yearsFromPeriods = allPeriods
        .filter(p => selectedPeriods.includes(p.id))
        .map(p => p.year);
      return allYears.filter(y => yearsFromPeriods.includes(y));
    }
    return allYears;
  }, [allPeriods, allYears, selectedPeriods]);

  // Meses disponíveis baseado nos períodos/anos selecionados
  const filteredMonths = useMemo(() => {
    let relevantPeriods = allPeriods;
    
    if (selectedPeriods.length > 0) {
      relevantPeriods = relevantPeriods.filter(p => selectedPeriods.includes(p.id));
    } else if (selectedYears.length > 0) {
      relevantPeriods = relevantPeriods.filter(p => selectedYears.includes(p.year));
    }
    
    const monthsFromPeriods = relevantPeriods.map(p => p.month);
    return allMonths.filter(m => monthsFromPeriods.includes(m.number));
  }, [allPeriods, allMonths, selectedPeriods, selectedYears]);

  // Departamentos disponíveis (sem filtro por enquanto, mas pode ser implementado)
  const filteredDepartments = useMemo(() => {
    return allDepartments;
  }, [allDepartments]);

  // Colaboradores disponíveis (sem filtro por enquanto, mas pode ser implementado)
  const filteredEmployees = useMemo(() => {
    return allEmployees;
  }, [allEmployees]);

  const loadFilters = async () => {
    try {
      // Carregar empresas
      const companiesRes = await api.get('/payroll/companies');
      setAllCompanies(companiesRes.data.companies || []);
      
      // Selecionar Empreendimentos (0060) por padrão
      if (companiesRes.data.companies && companiesRes.data.companies.length > 0) {
        setSelectedCompanies(['0060']);
      }
      
      // Carregar períodos
      const periodsRes = await api.get('/payroll/periods');
      setAllPeriods(periodsRes.data.periods || []);
      
      // Selecionar último período por padrão
      if (periodsRes.data.periods && periodsRes.data.periods.length > 0) {
        setSelectedPeriods([periodsRes.data.periods[0].id]);
      }

      // Carregar anos disponíveis
      const yearsRes = await api.get('/payroll/years');
      setAllYears(yearsRes.data.years || []);

      // Carregar meses disponíveis
      const monthsRes = await api.get('/payroll/months');
      setAllMonths(monthsRes.data.months || []);

      // Carregar departamentos
      const deptsRes = await api.get('/payroll/divisions');
      setAllDepartments(deptsRes.data.departments || []);

      // Carregar colaboradores
      const empsRes = await api.get('/payroll/employees');
      setAllEmployees(empsRes.data.employees || []);
      
    } catch (error) {
      console.error('Erro ao carregar filtros:', error);
      toast.error('Erro ao carregar filtros');
    }
  };

  const loadStatistics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCompanies.length > 0) params.append('companies', selectedCompanies.join(','));
      if (selectedYears.length > 0) params.append('years', selectedYears.join(','));
      if (selectedMonths.length > 0) params.append('months', selectedMonths.join(','));
      if (selectedPeriods.length > 0) params.append('periods', selectedPeriods.join(','));
      if (selectedDepartments.length > 0) params.append('departments', selectedDepartments.join(','));
      if (selectedEmployees.length > 0) params.append('employees', selectedEmployees.join(','));
      
      const response = await api.get(`/payroll/statistics?${params}`);
      setData(response.data);
      
      // Carregar estatísticas do cartão ponto
      await loadTimecardStats();
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
      toast.error('Erro ao carregar estatísticas');
    } finally {
      setLoading(false);
    }
  };

  const loadTimecardStats = async () => {
    try {
      const params = new URLSearchParams();
      
      console.log('🔍 DEBUG loadTimecardStats:', {
        selectedPeriods,
        selectedYears,
        selectedMonths,
        selectedCompanies,
        selectedDepartments,
        selectedEmployees,
        allPeriods
      });
      
      // Prioridade 1: Se há período específico selecionado, usar ele
      if (selectedPeriods.length > 0) {
        const period = allPeriods.find(p => p.id === selectedPeriods[0]);
        if (period) {
          params.append('year', period.year);
          params.append('month', period.month);
          console.log('✅ Usando período selecionado:', period.year, '/', period.month);
        }
      }
      // Prioridade 2: Se há ano E mês selecionados, usar eles
      else if (selectedYears.length > 0 && selectedMonths.length > 0) {
        params.append('year', selectedYears[0]);
        params.append('month', selectedMonths[0]);
        console.log('✅ Usando ano + mês selecionados:', selectedYears[0], '/', selectedMonths[0]);
      }
      // Prioridade 3: Se há apenas ano, usar o ano com o mês mais recente disponível
      else if (selectedYears.length > 0) {
        const yearPeriods = allPeriods.filter(p => p.year === selectedYears[0]);
        if (yearPeriods.length > 0) {
          const latestPeriod = yearPeriods.sort((a, b) => b.month - a.month)[0];
          params.append('year', latestPeriod.year);
          params.append('month', latestPeriod.month);
          console.log('✅ Usando ano com mês mais recente:', latestPeriod.year, '/', latestPeriod.month);
        }
      } else {
        console.log('⚠️ Sem filtros - carregando TODOS os dados de timecard');
      }
      
      // Filtrar por colaboradores
      if (selectedEmployees.length > 0) {
        params.append('employees', selectedEmployees.join(','));
        console.log('✅ Filtrando por colaboradores:', selectedEmployees);
      }

      // Filtrar por empresas
      if (selectedCompanies.length > 0) {
        params.append('companies', selectedCompanies.join(','));
        console.log('✅ Filtrando por empresas:', selectedCompanies);
      }

      // Filtrar por setores
      if (selectedDepartments.length > 0) {
        params.append('departments', selectedDepartments.join(','));
        console.log('✅ Filtrando por setores:', selectedDepartments);
      }
      
      const url = `/timecard/stats?${params}`;
      console.log('📡 Chamando API:', url);
      const response = await api.get(url);
      console.log('📊 Resposta da API timecard/stats:', response.data);
      setTimecardStats(response.data);
    } catch (error) {
      console.error('Erro ao carregar estatísticas do cartão ponto:', error);
      // Não mostrar toast de erro, apenas log (é opcional)
      setTimecardStats(null);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  // Função para converter horas decimais para formato HH:MM
  const formatHoursMinutes = (decimalHours) => {
    if (!decimalHours || isNaN(decimalHours)) return '00:00';
    const hours = Math.floor(decimalHours);
    const minutes = Math.round((decimalHours - hours) * 60);
    return `${hours}:${minutes.toString().padStart(2, '0')}`;
  };

  const escapeHtml = (value) => {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  const formatReportCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(Number(value || 0));
  };

  const formatReportHours = (value) => formatHoursMinutes(Number(value || 0));

  const getSelectedFilterLabels = () => {
    const monthLabelByNumber = {
      1: 'Janeiro',
      2: 'Fevereiro',
      3: 'Março',
      4: 'Abril',
      5: 'Maio',
      6: 'Junho',
      7: 'Julho',
      8: 'Agosto',
      9: 'Setembro',
      10: 'Outubro',
      11: 'Novembro',
      12: 'Dezembro',
    };

    const companyLabels = selectedCompanies.length > 0
      ? selectedCompanies.map((companyCode) => {
          const company = allCompanies.find((item) => item.code === companyCode);
          return company?.full_name || company?.name || companyCode;
        })
      : ['Todas as empresas'];

    const periodLabels = selectedPeriods.length > 0
      ? selectedPeriods.map((periodId) => {
          const period = allPeriods.find((item) => item.id === periodId);
          return period?.period_name || `Período ${periodId}`;
        })
      : [];

    const yearLabels = selectedYears.length > 0 ? selectedYears.map(String) : [];
    const monthLabels = selectedMonths.length > 0
      ? selectedMonths.map((monthNumber) => monthLabelByNumber[monthNumber] || String(monthNumber))
      : [];

    const departmentLabels = selectedDepartments.length > 0
      ? selectedDepartments.slice(0, 6)
      : [];

    const employeeLabels = selectedEmployees.length > 0
      ? selectedEmployees.slice(0, 6).map((employeeId) => {
          const employee = allEmployees.find((item) => item.id === employeeId);
          return employee?.name || String(employeeId);
        })
      : [];

    return {
      companyLabels,
      periodLabels,
      yearLabels,
      monthLabels,
      departmentLabels,
      employeeLabels,
    };
  };

  const buildExecutiveReportHtml = () => {
    if (!data) return null;

    const resumo = resumo_filtro || {};
    const salarios = informacoes_salariais || {};
    const beneficios = adicionais_beneficios || {};
    const encargos = encargos_trabalhistas || {};
    const horas = horas_extras || {};
    const faltas = atestados_faltas || {};
    const emprestimosData = emprestimos || {};
    const timecard = timecardStats || {};
    const filters = getSelectedFilterLabels();

    const filterPills = [
      ...filters.companyLabels.map((label) => `<span class="pill pill-company">${escapeHtml(label)}</span>`),
      ...filters.yearLabels.map((label) => `<span class="pill pill-year">${escapeHtml(label)}</span>`),
      ...filters.monthLabels.map((label) => `<span class="pill pill-month">${escapeHtml(label)}</span>`),
      ...filters.periodLabels.map((label) => `<span class="pill pill-period">${escapeHtml(label)}</span>`),
      ...filters.departmentLabels.map((label) => `<span class="pill pill-department">${escapeHtml(label)}</span>`),
      ...filters.employeeLabels.map((label) => `<span class="pill pill-employee">${escapeHtml(label)}</span>`),
    ].join('');

    const timecardCards = [
      { icon: '⏰', label: 'HE 50%', value: formatReportHours(timecard.overtime_50) },
      { icon: '⏰⏰', label: 'HE 100%', value: formatReportHours(timecard.overtime_100) },
      { icon: '📊', label: 'Total HE Diurnas', value: formatReportHours(timecard.total_overtime_hours) },
      { icon: '🌙⏰', label: 'HE Noturna 50%', value: formatReportHours(timecard.night_overtime_50) },
      { icon: '🌙⏰⏰', label: 'HE Noturna 100%', value: formatReportHours(timecard.night_overtime_100) },
      { icon: '🌙', label: 'Adic. Noturno', value: formatReportHours(timecard.night_hours) },
      { icon: '📊', label: 'Total Noturnas', value: formatReportHours(timecard.total_night_hours) },
    ].map((item) => `
      <div class="mini-card ${item.label.includes('Total') ? 'accent' : ''}">
        <div class="mini-icon">${item.icon}</div>
        <div class="mini-meta">
          <div class="mini-label">${escapeHtml(item.label)}</div>
          <div class="mini-value">${escapeHtml(item.value)}</div>
        </div>
      </div>
    `).join('');

    const benefitRows = [
      ['Gratificações', beneficios.gratificacoes],
      ['Periculosidade', beneficios.periculosidade],
      ['Insalubridade', beneficios.insalubridade],
      ['Vale Transporte', beneficios.vale_transporte],
      ['Plano de Saúde', beneficios.plano_saude],
      ['Vale Refeição', beneficios.vale_refeicao],
    ].map(([label, value]) => `
      <tr>
        <td>${escapeHtml(label)}</td>
        <td class="num">R$ ${escapeHtml(formatReportCurrency(value))}</td>
      </tr>
    `).join('');

    const chargeRows = [
      ['INSS', encargos.inss],
      ['IRRF', encargos.irrf],
      ['FGTS', encargos.fgts],
    ].map(([label, value]) => `
      <tr>
        <td>${escapeHtml(label)}</td>
        <td class="num">R$ ${escapeHtml(formatReportCurrency(value))}</td>
      </tr>
    `).join('');

    const hoursRows = [
      ['DSR Diurno', horas.dsr_diurno],
      ['HE 50% Diurno', horas.he50_diurno],
      ['HE 100% Diurno', horas.he100_diurno],
      ['Adicional Noturno', horas.adicional_noturno],
      ['DSR Noturno', horas.dsr_noturno],
      ['HE 50% Noturno', horas.he50_noturno],
      ['HE 100% Noturno', horas.he100_noturno],
    ].map(([label, value]) => `
      <tr>
        <td>${escapeHtml(label)}</td>
        <td class="num">${escapeHtml(formatReportHours(value))}</td>
      </tr>
    `).join('');

    const timecardCompanyRows = timecard.by_company
      ? Object.entries(timecard.by_company).map(([companyCode, companyData]) => `
        <tr>
          <td>${escapeHtml(companyCode === '0060' ? 'Empreendimentos' : companyCode === '0059' ? 'Infraestrutura' : companyCode)}</td>
          <td class="num">${escapeHtml(String(companyData.employees || 0))}</td>
          <td class="num">${escapeHtml(formatReportHours(companyData.total_overtime || 0))}</td>
          <td class="num">${escapeHtml(formatReportHours(companyData.total_night_hours || 0))}</td>
        </tr>
      `).join('')
      : '';

    const html = `
      <!DOCTYPE html>
      <html lang="pt-BR">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Relatório Executivo - Folha e Ponto</title>
        <style>
          @page {
            size: A4 landscape;
            margin: 12mm;
          }

          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            color: #0f172a;
            background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 24%, #ffffff 100%);
          }

          .page {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0;
          }

          .hero {
            background: linear-gradient(135deg, #111827 0%, #4338ca 42%, #7c3aed 100%);
            color: #fff;
            border-radius: 28px;
            padding: 28px 30px;
            box-shadow: 0 30px 60px rgba(17, 24, 39, 0.18);
            overflow: hidden;
            position: relative;
          }

          .hero:after {
            content: '';
            position: absolute;
            inset: auto -80px -80px auto;
            width: 220px;
            height: 220px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.12);
            filter: blur(0px);
          }

          .hero-top {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            align-items: flex-start;
            position: relative;
            z-index: 1;
          }

          .brand {
            font-size: 13px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            opacity: 0.8;
            margin-bottom: 8px;
          }

          .title {
            font-size: 34px;
            line-height: 1.04;
            font-weight: 800;
            margin: 0 0 10px 0;
          }

          .subtitle {
            font-size: 15px;
            opacity: 0.9;
            margin: 0;
          }

          .hero-side {
            text-align: right;
            min-width: 220px;
          }

          .hero-side .period {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 6px;
          }

          .hero-side .meta {
            font-size: 12px;
            opacity: 0.86;
            line-height: 1.7;
          }

          .chip-row {
            margin-top: 18px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            position: relative;
            z-index: 1;
          }

          .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.18);
            backdrop-filter: blur(10px);
          }

          .section {
            margin-top: 18px;
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 24px;
            padding: 22px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
            break-inside: avoid;
          }

          .section-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 16px;
          }

          .section-title h2 {
            font-size: 18px;
            margin: 0;
            color: #111827;
          }

          .section-title p {
            margin: 0;
            font-size: 12px;
            color: #64748b;
          }

          .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
          }

          .summary-card {
            border-radius: 18px;
            padding: 16px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
          }

          .summary-card .label {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #64748b;
          }

          .summary-card .value {
            margin-top: 8px;
            font-size: 22px;
            line-height: 1.1;
            font-weight: 800;
            color: #0f172a;
          }

          .summary-card.primary { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); }
          .summary-card.primary .value { color: #1d4ed8; }
          .summary-card.success { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); }
          .summary-card.success .value { color: #047857; }
          .summary-card.warning { background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); }
          .summary-card.warning .value { color: #b45309; }
          .summary-card.danger { background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%); }
          .summary-card.danger .value { color: #b91c1c; }
          .summary-card.purple { background: linear-gradient(135deg, #f5f3ff 0%, #e9d5ff 100%); }
          .summary-card.purple .value { color: #7c3aed; }

          .kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
          }

          .mini-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
          }

          .mini-card {
            display: flex;
            align-items: center;
            gap: 12px;
            border-radius: 16px;
            padding: 14px;
            background: #fff;
            border: 1px solid #e5e7eb;
          }

          .mini-card.accent {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-color: #bfdbfe;
          }

          .mini-icon {
            width: 44px;
            height: 44px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(79, 70, 229, 0.08);
            font-size: 18px;
            flex: 0 0 auto;
          }

          .mini-meta { min-width: 0; }
          .mini-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 800;
          }
          .mini-value {
            margin-top: 4px;
            font-size: 18px;
            font-weight: 800;
            color: #0f172a;
          }

          .dual-grid {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 16px;
          }

          .card {
            border-radius: 20px;
            border: 1px solid #e5e7eb;
            background: #fff;
            padding: 16px;
          }

          .card h3 {
            margin: 0 0 12px 0;
            font-size: 15px;
            color: #111827;
          }

          .table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
          }

          .table th,
          .table td {
            padding: 10px 8px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
          }

          .table th {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #64748b;
            background: #f8fafc;
          }

          .table td.num,
          .table th.num { text-align: right; }

          .note {
            margin-top: 12px;
            padding: 12px 14px;
            border-radius: 16px;
            background: #f8fafc;
            color: #475569;
            font-size: 12px;
            line-height: 1.55;
            border: 1px solid #e2e8f0;
          }

          .footer {
            margin: 18px 0 4px;
            color: #64748b;
            font-size: 11px;
            text-align: center;
          }

          @media print {
            body { background: white; }
            .page { max-width: none; }
            .section, .hero { box-shadow: none; }
            .no-print { display: none !important; }
          }
        </style>
      </head>
      <body>
        <div class="page">
          <div class="hero">
            <div class="hero-top">
              <div>
                <div class="brand">EnviaFolha • Relatório Executivo</div>
                <h1 class="title">Indicadores de Folha e Cartão Ponto</h1>
                <p class="subtitle">Visão consolidada do período selecionado com foco em leitura rápida e apresentação executiva.</p>
              </div>
              <div class="hero-side">
                <div class="period">${escapeHtml(selectedPeriods.length > 0 ? (allPeriods.find((item) => item.id === selectedPeriods[0])?.period_name || 'Período selecionado') : 'Período selecionado')}</div>
                <div class="meta">
                  Gerado em ${escapeHtml(new Date().toLocaleString('pt-BR'))}<br />
                  Empresa: ${escapeHtml(filters.companyLabels.join(' · '))}<br />
                  Filtros ativos: ${escapeHtml(String(totalActiveFilters))}
                </div>
              </div>
            </div>
            <div class="chip-row">
              ${filterPills || '<span class="pill">Sem filtros adicionais</span>'}
            </div>
          </div>

          <div class="section">
            <div class="section-title">
              <div>
                <h2>Resumo Executivo</h2>
                <p>Os principais números da folha no recorte atual.</p>
              </div>
            </div>
            <div class="summary-grid">
              <div class="summary-card primary"><div class="label">Funcionários</div><div class="value">${escapeHtml(String(resumo.funcionarios || 0))}</div></div>
              <div class="summary-card success"><div class="label">Total Líquido</div><div class="value">R$ ${escapeHtml(formatReportCurrency(resumo.total_liquido))}</div></div>
              <div class="summary-card warning"><div class="label">Total Proventos</div><div class="value">R$ ${escapeHtml(formatReportCurrency(resumo.total_proventos))}</div></div>
              <div class="summary-card danger"><div class="label">Total Descontos</div><div class="value">R$ ${escapeHtml(formatReportCurrency(resumo.total_descontos))}</div></div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">
              <div>
                <h2>Informações Salariais</h2>
                <p>Base salarial e médias do período.</p>
              </div>
            </div>
            <div class="kpi-grid">
              <div class="summary-card purple"><div class="label">Total Salários Base</div><div class="value">R$ ${escapeHtml(formatReportCurrency(salarios.total_salarios_base))}</div></div>
              <div class="summary-card primary"><div class="label">Salário Médio</div><div class="value">R$ ${escapeHtml(formatReportCurrency(salarios.salario_medio))}</div></div>
              <div class="summary-card success"><div class="label">Líquido Médio</div><div class="value">R$ ${escapeHtml(formatReportCurrency(salarios.liquido_medio))}</div></div>
            </div>
          </div>

          <div class="dual-grid">
            <div class="section">
              <div class="section-title">
                <div>
                  <h2>Adicionais e Benefícios</h2>
                  <p>Itens de remuneração variável e benefícios principais.</p>
                </div>
              </div>
              <div class="summary-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr)); margin-bottom: 12px;">
                <div class="summary-card purple"><div class="label">Total Geral</div><div class="value">R$ ${escapeHtml(formatReportCurrency(beneficios.total))}</div></div>
                <div class="summary-card primary"><div class="label">Adicionais / Benefícios</div><div class="value">${escapeHtml(String(beneficios.total ? 'Consolidados' : '0'))}</div></div>
              </div>
              <table class="table">
                <thead><tr><th>Item</th><th class="num">Valor</th></tr></thead>
                <tbody>${benefitRows}</tbody>
              </table>
            </div>

            <div class="section">
              <div class="section-title">
                <div>
                  <h2>Encargos</h2>
                  <p>Custos trabalhistas consolidados.</p>
                </div>
              </div>
              <div class="summary-grid" style="grid-template-columns: repeat(1, minmax(0, 1fr)); margin-bottom: 12px;">
                <div class="summary-card danger"><div class="label">Total Encargos</div><div class="value">R$ ${escapeHtml(formatReportCurrency(encargos.total))}</div></div>
              </div>
              <table class="table">
                <thead><tr><th>Encargo</th><th class="num">Valor</th></tr></thead>
                <tbody>${chargeRows}</tbody>
              </table>
            </div>
          </div>

          <div class="section">
            <div class="section-title">
              <div>
                <h2>Cartão Ponto - Horas por Tipo</h2>
                <p>Leitura executiva dos totais de horas importadas no período.</p>
              </div>
            </div>
            <div class="mini-grid">${timecardCards}</div>
            <div class="note">
              <strong>Observação:</strong> este resumo enfatiza o consumo de horas extras e noturnas. Indicadores operacionais como DSR foram excluídos desta visualização para manter o foco executivo.
            </div>
            <div style="margin-top: 14px;">
              <table class="table">
                <thead><tr><th>Empresa</th><th class="num">Colaboradores</th><th class="num">HE Total</th><th class="num">Noturnas</th></tr></thead>
                <tbody>${timecardCompanyRows || '<tr><td colspan="4">Sem detalhamento por empresa disponível.</td></tr>'}</tbody>
              </table>
            </div>
          </div>

          <div class="section">
            <div class="section-title">
              <div>
                <h2>Horas Extras Consolidadas</h2>
                <p>Indicadores complementares da folha atual.</p>
              </div>
            </div>
            <div class="mini-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr));">
              ${[
                ['☀️', 'DSR Diurno', horas.dsr_diurno],
                ['⏰', 'HE 50% Diurno', horas.he50_diurno],
                ['⏰⏰', 'HE 100% Diurno', horas.he100_diurno],
                ['🌙', 'Adic. Noturno', horas.adicional_noturno],
                ['🌙', 'DSR Noturno', horas.dsr_noturno],
                ['🌙⏰', 'HE 50% Noturno', horas.he50_noturno],
                ['🌙⏰⏰', 'HE 100% Noturno', horas.he100_noturno],
                ['💰', 'Total Horas Extras', horas.total],
              ].map(([icon, label, value]) => `
                <div class="mini-card">
                  <div class="mini-icon">${icon}</div>
                  <div class="mini-meta">
                    <div class="mini-label">${escapeHtml(label)}</div>
                    <div class="mini-value">${escapeHtml(formatReportHours(value))}</div>
                  </div>
                </div>
              `).join('')}
            </div>
            <div style="margin-top: 14px;">
              <table class="table">
                <thead><tr><th>Indicador</th><th class="num">Total</th></tr></thead>
                <tbody>${hoursRows}</tbody>
              </table>
            </div>
          </div>

          <div class="section">
            <div class="section-title">
              <div>
                <h2>Atestados, Faltas e Empréstimos</h2>
                <p>Itens de desconto e ocorrências complementares.</p>
              </div>
            </div>
            <div class="summary-grid" style="grid-template-columns: repeat(3, minmax(0, 1fr));">
              <div class="summary-card warning"><div class="label">Total Atestados/Faltas</div><div class="value">R$ ${escapeHtml(formatReportCurrency(faltas.total))}</div></div>
              <div class="summary-card danger"><div class="label">Total Empréstimos</div><div class="value">R$ ${escapeHtml(formatReportCurrency(emprestimosData.total))}</div></div>
              <div class="summary-card primary"><div class="label">Líquido Estimado</div><div class="value">R$ ${escapeHtml(formatReportCurrency(resumo.total_liquido))}</div></div>
            </div>
          </div>

          <div class="footer">
            EnviaFolha • Relatório executivo gerado automaticamente em ${escapeHtml(new Date().toLocaleString('pt-BR'))}
          </div>
        </div>
      </body>
      </html>
    `;

    return html;
  };

  const handleExportExecutivePdf = () => {
    const html = buildExecutiveReportHtml();
    if (!html) {
      toast.error('Nenhum dado disponível para exportação');
      return;
    }

    const reportWindow = window.open('', '_blank', 'width=1400,height=1000');
    if (!reportWindow) {
      const fallbackFrame = document.createElement('iframe');
      fallbackFrame.style.position = 'fixed';
      fallbackFrame.style.right = '0';
      fallbackFrame.style.bottom = '0';
      fallbackFrame.style.width = '0';
      fallbackFrame.style.height = '0';
      fallbackFrame.style.border = '0';
      fallbackFrame.style.visibility = 'hidden';
      fallbackFrame.srcdoc = html;
      document.body.appendChild(fallbackFrame);

      fallbackFrame.onload = () => {
        try {
          const fallbackWindow = fallbackFrame.contentWindow;
          if (fallbackWindow) {
            fallbackWindow.focus();
            fallbackWindow.print();
          }
        } catch (error) {
          console.error('Erro ao abrir relatório executivo no fallback:', error);
          toast.error('Não foi possível abrir o relatório executivo');
        }

        setTimeout(() => {
          if (fallbackFrame.parentNode) {
            fallbackFrame.parentNode.removeChild(fallbackFrame);
          }
        }, 1000);
      };

      toast('Abrindo relatório executivo nesta página');
      return;
    }

    reportWindow.document.open();
    reportWindow.document.write(html);
    reportWindow.document.close();
    reportWindow.focus();
    reportWindow.document.title = 'Relatorio_Executivo_Folha_Ponto';

    setTimeout(() => {
      try {
        reportWindow.print();
      } catch (error) {
        console.error('Erro ao imprimir relatório executivo:', error);
      }
    }, 700);
  };

  // Contar total de filtros ativos (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores)
  const totalActiveFilters = selectedCompanies.length + selectedYears.length + 
                             selectedMonths.length + selectedPeriods.length +
                             selectedDepartments.length + selectedEmployees.length;

  // Limpar todos os filtros
  const clearAllFilters = () => {
    setSelectedCompanies([]);
    setSelectedYears([]);
    setSelectedMonths([]);
    setSelectedPeriods([]);
    setSelectedDepartments([]);
    setSelectedEmployees([]);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-gray-500 py-12">
        Nenhum dado disponível
      </div>
    );
  }

  const { resumo_filtro, informacoes_salariais, adicionais_beneficios, encargos_trabalhistas, horas_extras, atestados_faltas, emprestimos } = data;

  return (
    <div className="space-y-6">
      {/* Header com Filtros */}
      <div className={`${config.classes.card} rounded-lg shadow`}>
        {/* Cabeçalho dos Filtros */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className={`text-2xl font-bold ${config.classes.text}`}>
              📊 Indicadores de Folha de Pagamento
            </h2>
            
            <div className="flex items-center gap-3">
              <ExportPDFButton
                className="no-print"
                onClick={handleExportExecutivePdf}
                label="Exportar PDF Executivo"
                title="Gerar PDF executivo da visão atual"
              />
              {totalActiveFilters > 0 && (
                <>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {totalActiveFilters} {totalActiveFilters === 1 ? 'filtro ativo' : 'filtros ativos'}
                  </span>
                  <button
                    onClick={clearAllFilters}
                    className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium"
                  >
                    Limpar tudo
                  </button>
                </>
              )}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  showFilters 
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200' 
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}
              >
                {showFilters ? '🔽 Ocultar Filtros' : '🔼 Mostrar Filtros'}
              </button>
            </div>
          </div>
        </div>

        {/* Grid de Filtros - Colapsável (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores) */}
        {showFilters && (
          <div className="p-6 bg-gray-50 dark:bg-gray-800/50">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              {/* 1. Filtro de Empresa */}
              <MultiSelect
                label="Empresa"
                options={allCompanies.map(c => ({ value: c.code, label: c.full_name }))}
                selected={selectedCompanies}
                onChange={setSelectedCompanies}
                placeholder="Todas as empresas"
              />

              {/* 2. Filtro de Anos */}
              <MultiSelect
                label="Anos"
                options={filteredYears.map(y => ({ value: y, label: y.toString() }))}
                selected={selectedYears}
                onChange={setSelectedYears}
                placeholder="Todos os anos"
              />

              {/* 3. Filtro de Meses */}
              <MultiSelect
                label="Meses"
                options={filteredMonths.map(m => ({ value: m.number, label: m.name }))}
                selected={selectedMonths}
                onChange={setSelectedMonths}
                placeholder="Todos os meses"
              />

              {/* 4. Filtro de Períodos */}
              <MultiSelect
                label="Períodos"
                options={filteredPeriods.map(p => ({ value: p.id, label: p.period_name }))}
                selected={selectedPeriods}
                onChange={setSelectedPeriods}
                placeholder="Todos os períodos"
              />

              {/* 5. Filtro de Setores */}
              <MultiSelect
                label="Setores"
                options={filteredDepartments.map(d => ({ value: d.name, label: d.name }))}
                selected={selectedDepartments}
                onChange={setSelectedDepartments}
                placeholder="Todos os setores"
                searchable={true}
              />

              {/* 6. Filtro de Colaboradores */}
              <MultiSelect
                label="Colaboradores"
                options={filteredEmployees.map(e => ({ value: e.id, label: e.name }))}
                selected={selectedEmployees}
                onChange={setSelectedEmployees}
                placeholder="Todos os colaboradores"
                searchable={true}
              />
            </div>
          </div>
        )}

        {/* Resumo Compacto dos Filtros Ativos - Sempre Visível (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores) */}
        {totalActiveFilters > 0 && (
          <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-100 dark:border-blue-800">
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Filtros aplicados:
              </span>
              
              {/* Empresas */}
              {selectedCompanies.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {allCompanies.filter(c => selectedCompanies.includes(c.code)).map(c => (
                    <span key={c.code} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                      {c.name}
                    </span>
                  ))}
                </div>
              )}

              {/* Anos */}
              {selectedYears.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedYears.map(y => (
                    <span key={y} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200">
                      {y}
                    </span>
                  ))}
                </div>
              )}

              {/* Meses */}
              {selectedMonths.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {filteredMonths.filter(m => selectedMonths.includes(m.number)).slice(0, 3).map(m => (
                    <span key={m.number} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                      {m.name}
                    </span>
                  ))}
                  {selectedMonths.length > 3 && (
                    <span className="px-2 py-0.5 text-xs text-green-700 dark:text-green-300">
                      +{selectedMonths.length - 3} meses
                    </span>
                  )}
                </div>
              )}

              {/* Períodos */}
              {selectedPeriods.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {filteredPeriods.filter(p => selectedPeriods.includes(p.id)).slice(0, 2).map(p => (
                    <span key={p.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                      {p.period_name}
                    </span>
                  ))}
                  {selectedPeriods.length > 2 && (
                    <span className="px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300">
                      +{selectedPeriods.length - 2} períodos
                    </span>
                  )}
                </div>
              )}

              {/* Anos */}
              {selectedYears.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedYears.map(y => (
                    <span key={y} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200">
                      {y}
                    </span>
                  ))}
                </div>
              )}

              {/* Meses */}
              {selectedMonths.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {filteredMonths.filter(m => selectedMonths.includes(m.number)).slice(0, 3).map(m => (
                    <span key={m.number} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                      {m.name}
                    </span>
                  ))}
                  {selectedMonths.length > 3 && (
                    <span className="px-2 py-0.5 text-xs text-green-700 dark:text-green-300">
                      +{selectedMonths.length - 3} meses
                    </span>
                  )}
                </div>
              )}

              {/* Setores */}
              {selectedDepartments.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                    {selectedDepartments.length} {selectedDepartments.length === 1 ? 'setor' : 'setores'}
                  </span>
                </div>
              )}

              {/* Colaboradores */}
              {selectedEmployees.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-teal-100 dark:bg-teal-900 text-teal-800 dark:text-teal-200">
                    {selectedEmployees.length} {selectedEmployees.length === 1 ? 'colaborador' : 'colaboradores'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* SEÇÃO 1: Resumo de Filtro */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          📋 Resumo Filtrado
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <CardStat 
            icon="👥"
            label="Funcionários"
            value={resumo_filtro.funcionarios}
            color="blue"
            isNumber
          />
          <CardStat 
            icon="💰"
            label="Total Proventos"
            value={resumo_filtro.total_proventos}
            color="green"
            prefix="R$"
          />
          <CardStat 
            icon="💸"
            label="Total Descontos"
            value={resumo_filtro.total_descontos}
            color="red"
            prefix="R$"
          />
          <CardStat 
            icon="💵"
            label="Total Líquido"
            value={resumo_filtro.total_liquido}
            color="teal"
            prefix="R$"
          />
        </div>
      </div>

      {/* SEÇÃO 2: Informações Salariais */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          💼 Informações Salariais
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardStat 
            icon="💵"
            label="Total Salários Base"
            value={informacoes_salariais.total_salarios_base}
            color="blue"
            prefix="R$"
            subtitle="Soma de todos os salários"
          />
          <CardStat 
            icon="📊"
            label="Salário Médio"
            value={informacoes_salariais.salario_medio}
            color="indigo"
            prefix="R$"
            subtitle="Média por funcionário"
          />
          <CardStat 
            icon="💎"
            label="Líquido Médio"
            value={informacoes_salariais.liquido_medio}
            color="purple"
            prefix="R$"
            subtitle="Média por funcionário"
          />
        </div>
      </div>

      {/* SEÇÃO 3: Adicionais e Benefícios */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          💎 Adicionais e Benefícios
        </h3>
        
        {/* Card Totalizador */}
        <div className="mb-4">
          <CardStat 
            icon="💰" 
            label="Total Adicionais e Benefícios" 
            value={adicionais_beneficios.total} 
            color="purple" 
            prefix="R$" 
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <CardStatMini icon="🎁" label="Gratificações" value={adicionais_beneficios.gratificacoes} color="amber" />
          <CardStatMini icon="⚠️" label="Periculosidade" value={adicionais_beneficios.periculosidade} color="orange" />
          <CardStatMini icon="🏥" label="Insalubridade" value={adicionais_beneficios.insalubridade} color="yellow" />
          <CardStatMini icon="🚌" label="Vale Transporte" value={adicionais_beneficios.vale_transporte} color="gray" />
          <CardStatMini icon="🏥" label="Plano de Saúde" value={adicionais_beneficios.plano_saude} color="blue" />
          <CardStatMini icon="🚗" label="Vale Mobilidade" value={adicionais_beneficios.vale_mobilidade} color="gray" />
          <CardStatMini icon="🍽️" label="Vale Refeição" value={adicionais_beneficios.vale_refeicao} color="gray" />
          <CardStatMini icon="🛒" label="Vale Alimentação" value={adicionais_beneficios.vale_alimentacao} color="gray" />
          <CardStatMini icon="💰" label="Saldo Livre" value={adicionais_beneficios.saldo_livre} color="gray" />
          <CardStatMini icon="🔄" label="Transferência Filial" value={adicionais_beneficios.transferencia_filial} color="cyan" />
          <CardStatMini icon="💵" label="Ajuda de Custo" value={adicionais_beneficios.ajuda_custo} color="teal" />
          <CardStatMini icon="👶" label="Licença Paternidade" value={adicionais_beneficios.licenca_paternidade} color="pink" />
        </div>
      </div>

      {/* SEÇÃO 4: Encargos Trabalhistas */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          🏛️ Encargos Trabalhistas
        </h3>
        
        {/* Card Totalizador */}
        <div className="mb-4">
          <CardStat 
            icon="💰" 
            label="Total Encargos" 
            value={encargos_trabalhistas.total} 
            color="purple" 
            prefix="R$" 
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardStat icon="🏛️" label="INSS" value={encargos_trabalhistas.inss} color="blue" prefix="R$" />
          <CardStat icon="📝" label="IRRF" value={encargos_trabalhistas.irrf} color="indigo" prefix="R$" />
          <CardStat icon="🏦" label="FGTS" value={encargos_trabalhistas.fgts} color="green" prefix="R$" />
        </div>
      </div>

      {/* SEÇÃO 5: Horas Extras */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          ⏰ Horas Extras
        </h3>
        
        {/* Card Totalizador */}
        <div className="mb-4">
          <CardStat 
            icon="💰" 
            label="Total Horas Extras" 
            value={horas_extras.total} 
            color="purple" 
            prefix="R$" 
          />
        </div>

        {/* Cartão Ponto - Horas por Tipo (Período Mais Recente) */}
        {timecardStats && (
          <div className="mb-4">
            <h4 className={`text-sm font-medium ${config.classes.text} mb-2`}>📋 Cartão Ponto - Horas por Tipo</h4>
            
            {/* Linha 1: Horas Extras Diurnas */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
              <CardStatMini 
                icon="⏰" 
                label="HE 50%" 
                value={parseFloat(timecardStats.overtime_50 || 0)} 
                color="amber" 
                isTime={true}
              />
              <CardStatMini 
                icon="⏰⏰" 
                label="HE 100%" 
                value={parseFloat(timecardStats.overtime_100 || 0)} 
                color="orange" 
                isTime={true}
              />
              <CardStatMini 
                icon="📊" 
                label="Total HE Diurnas" 
                value={parseFloat(timecardStats.total_overtime_hours || 0)} 
                color="red" 
                isTime={true}
              />
            </div>
            
            {/* Linha 2: Horas Extras Noturnas */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              <CardStatMini 
                icon="🌙⏰" 
                label="HE Noturna 50%" 
                value={parseFloat(timecardStats.night_overtime_50 || 0)} 
                color="purple" 
                isTime={true}
              />
              <CardStatMini 
                icon="🌙⏰⏰" 
                label="HE Noturna 100%" 
                value={parseFloat(timecardStats.night_overtime_100 || 0)} 
                color="violet" 
                isTime={true}
              />
              <CardStatMini 
                icon="🌙" 
                label="Adic. Noturno" 
                value={parseFloat(timecardStats.night_hours || 0)} 
                color="indigo" 
                isTime={true}
              />
              <CardStatMini 
                icon="📊" 
                label="Total Noturnas" 
                value={parseFloat(timecardStats.total_night_hours || 0)} 
                color="blue" 
                isTime={true}
              />
            </div>
            
          </div>
        )}
        
        {/* Horas Extras Diurnas */}
        <div className="mb-4">
          <h4 className={`text-sm font-medium ${config.classes.text} mb-2`}>☀️ Diurnas</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <CardStatMini icon="☀️" label="DSR Diurno" value={horas_extras.dsr_diurno} color="yellow" />
            <CardStatMini icon="⏰" label="HE 50% Diurno" value={horas_extras.he50_diurno} color="amber" />
            <CardStatMini icon="⏰⏰" label="HE 100% Diurno" value={horas_extras.he100_diurno} color="orange" />
          </div>
        </div>
        
        {/* Horas Extras Noturnas */}
        <div>
          <h4 className={`text-sm font-medium ${config.classes.text} mb-2`}>🌙 Noturnas</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <CardStatMini icon="🌙" label="Adicional Noturno" value={horas_extras.adicional_noturno} color="indigo" />
            <CardStatMini icon="🌙" label="DSR Noturno" value={horas_extras.dsr_noturno} color="blue" />
            <CardStatMini icon="🌙⏰" label="HE 50% Noturno" value={horas_extras.he50_noturno} color="purple" />
            <CardStatMini icon="🌙⏰⏰" label="HE 100% Noturno" value={horas_extras.he100_noturno} color="violet" />
          </div>
        </div>
      </div>

      {/* SEÇÃO 6: Atestados Médicos e Horas Faltas */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          🏥 Atestados Médicos e Horas Faltas
        </h3>
        
        {/* Card Totalizador */}
        <div className="mb-4">
          <CardStat 
            icon="💰" 
            label="Total Atestados e Faltas" 
            value={atestados_faltas.total} 
            color="purple" 
            prefix="R$" 
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardStat icon="❌" label="Horas Faltas" value={atestados_faltas.horas_faltas} color="red" prefix="R$" />
          <CardStat icon="🏥" label="Atestados Médicos" value={atestados_faltas.atestados_medicos} color="blue" prefix="R$" />
        </div>
      </div>

      {/* SEÇÃO 7: Empréstimos */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          💳 Empréstimos
        </h3>
        
        {/* Card Totalizador */}
        <div className="mb-4">
          <CardStat 
            icon="💰" 
            label="Total Empréstimos" 
            value={emprestimos.total} 
            color="purple" 
            prefix="R$" 
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardStat icon="💳" label="Empréstimo do Trabalhador" value={emprestimos.emprestimo_trabalhador} color="orange" prefix="R$" />
          <CardStat icon="💰" label="Adiantamentos" value={emprestimos.adiantamentos} color="amber" prefix="R$" />
        </div>
      </div>
    </div>
  );
};

// Componente para cards grandes
const CardStat = ({ icon, label, value, color, prefix = '', subtitle = '', isNumber = false }) => {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    green: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    red: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    teal: 'bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-800',
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800',
    purple: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
    amber: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
  };

  const formatValue = (val) => {
    if (isNumber) return val;
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val || 0);
  };

  return (
    <div className={`border rounded-lg p-4 ${colorClasses[color] || colorClasses.blue}`}>
      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 flex items-center gap-2">
        <span>{icon}</span>
        {label}
      </p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
        {prefix && <span className="text-lg">{prefix} </span>}
        {formatValue(value)}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
      )}
    </div>
  );
};

// Componente para cards pequenos
const CardStatMini = ({ icon, label, value, color, isTime = false, isNumber = false }) => {
  const colorClasses = {
    amber: 'bg-amber-50 dark:bg-amber-900/20',
    orange: 'bg-orange-50 dark:bg-orange-900/20',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/20',
    blue: 'bg-blue-50 dark:bg-blue-900/20',
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20',
    purple: 'bg-purple-50 dark:bg-purple-900/20',
    violet: 'bg-violet-50 dark:bg-violet-900/20',
    cyan: 'bg-cyan-50 dark:bg-cyan-900/20',
    teal: 'bg-teal-50 dark:bg-teal-900/20',
    pink: 'bg-pink-50 dark:bg-pink-900/20',
    gray: 'bg-gray-50 dark:bg-gray-800/50',
    green: 'bg-green-50 dark:bg-green-900/20',
    red: 'bg-red-50 dark:bg-red-900/20',
  };

  const formatValue = (val) => {
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val || 0);
  };

  // Função para formatar horas decimais em HH:MM
  const formatTimeValue = (decimalHours) => {
    if (!decimalHours || isNaN(decimalHours)) return '00:00';
    const hours = Math.floor(decimalHours);
    const minutes = Math.round((decimalHours - hours) * 60);
    return `${hours}:${minutes.toString().padStart(2, '0')}`;
  };

  // Determinar como exibir o valor
  const displayValue = () => {
    if (isTime) return formatTimeValue(value);
    if (isNumber) return value;
    return `R$ ${formatValue(value)}`;
  };

  return (
    <div className={`border rounded-lg p-3 ${colorClasses[color] || colorClasses.gray}`}>
      <p className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center gap-1">
        <span>{icon}</span>
        {label}
      </p>
      <p className="text-lg font-bold text-gray-900 dark:text-white mt-1">
        {displayValue()}
      </p>
    </div>
  );
};

export default PayrollV2;
