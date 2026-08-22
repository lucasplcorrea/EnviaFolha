import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowDownTrayIcon,
  ArrowTopRightOnSquareIcon,
  ClipboardDocumentCheckIcon,
  FunnelIcon,
  QueueListIcon,
  TableCellsIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const Reports = () => {
  const { config } = useTheme();
  const [exportingAction, setExportingAction] = useState('');
  const [exportParams, setExportParams] = useState({
    company: '0059',
    year: '2025',
    month: '12',
    payrollType: 'mensal',
    department: '',
    employeeId: ''
  });
  const [reportType, setReportType] = useState('strategic');
  const [terminationScenario, setTerminationScenario] = useState('sem_justa_causa');
  const [terminationDay, setTerminationDay] = useState('15');
  const [employees, setEmployees] = useState([]);
  const [loadingEmployees, setLoadingEmployees] = useState(false);

  const handleExportParamChange = (field, value) => {
    setExportParams(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const downloadXlsx = async ({ endpoint, params, defaultFilename, loadingMessage, successMessage, errorMessage, actionKey }) => {
    try {
      setExportingAction(actionKey);
      const toastId = toast.loading(loadingMessage);

      const response = await api.get(endpoint, {
        params,
        responseType: 'blob'
      });

      const contentDisposition = response.headers['content-disposition'] || '';
      const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
      const filename = filenameMatch?.[1] || defaultFilename;

      const blob = new Blob([
        response.data
      ], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

      toast.success(successMessage, { id: toastId });
    } catch (error) {
      console.error('Erro ao exportar relatório:', error);
      const detail = error?.response?.data?.error;
      toast.error(detail || errorMessage);
    } finally {
      setExportingAction('');
    }
  };

  const getBaseExportParams = () => ({
    company: exportParams.company,
    year: exportParams.year,
    month: exportParams.month,
    payroll_type: exportParams.payrollType,
    department: exportParams.department || undefined,
    employee_id: exportParams.employeeId || undefined,
  });

  const exportReports = async () => {
    const baseParams = getBaseExportParams();
    await downloadXlsx({
      endpoint: '/reports/exports/infra-analytics',
      params: baseParams,
      defaultFilename: `relatorio_estrategico_${exportParams.company}_${exportParams.year}-${String(exportParams.month).padStart(2, '0')}.xlsx`,
      loadingMessage: 'Gerando relatório estratégico...',
      successMessage: 'Relatório estratégico exportado com sucesso',
      errorMessage: 'Erro ao exportar relatório estratégico',
      actionKey: 'strategic',
    });
  };

  const exportMonthlyProvisions = async () => {
    const baseParams = getBaseExportParams();
    await downloadXlsx({
      endpoint: '/reports/exports/monthly-provisions',
      params: baseParams,
      defaultFilename: `relatorio_provisoes_${exportParams.company}_${exportParams.year}-${String(exportParams.month).padStart(2, '0')}.xlsx`,
      loadingMessage: 'Gerando relatório de provisões...',
      successMessage: 'Relatório de provisões exportado com sucesso',
      errorMessage: 'Erro ao exportar relatório de provisões',
      actionKey: 'provisions',
    });
  };

  const exportTerminationSimulation = async () => {
    const baseParams = getBaseExportParams();
    await downloadXlsx({
      endpoint: '/reports/exports/termination-simulation',
      params: {
        ...baseParams,
        scenario: terminationScenario,
        termination_day: terminationDay,
      },
      defaultFilename: `simulacao_rescisoes_${exportParams.company}_${exportParams.year}-${String(exportParams.month).padStart(2, '0')}_${terminationScenario}.xlsx`,
      loadingMessage: 'Gerando simulação de rescisão...',
      successMessage: 'Simulação de rescisão exportada com sucesso',
      errorMessage: 'Erro ao exportar simulação de rescisão',
      actionKey: 'termination',
    });
  };

  const exportFundPersonnelCost = async () => {
    const baseParams = getBaseExportParams();
    await downloadXlsx({
      endpoint: '/reports/exports/fund-personnel-cost',
      params: baseParams,
      defaultFilename: `relatorio_custo_fundo_${exportParams.company}_${exportParams.year}-${String(exportParams.month).padStart(2, '0')}.xlsx`,
      loadingMessage: 'Gerando relatório de custo de pessoal para o fundo...',
      successMessage: 'Relatório de custo de pessoal para o fundo exportado com sucesso',
      errorMessage: 'Erro ao exportar relatório de custo de pessoal para o fundo',
      actionKey: 'fund_cost',
    });
  };

  const reportTypeOptions = [
    {
      key: 'strategic',
      title: 'Estratégico',
      description: 'Folha e benefícios por competência com visão analítica.',
      actionLabel: 'Baixar Relatório Estratégico',
      actionLoadingLabel: 'Gerando relatório estratégico...',
      action: exportReports,
    },
    {
      key: 'provisions',
      title: 'Provisões Mensais',
      description: 'Provisões de caixa e encargos por colaborador/setor.',
      actionLabel: 'Baixar Relatório de Provisões',
      actionLoadingLabel: 'Gerando relatório de provisões...',
      action: exportMonthlyProvisions,
    },
    {
      key: 'termination',
      title: 'Simulação de Rescisão',
      description: 'Estimativa de desligamento por colaborador e cenário.',
      actionLabel: 'Baixar Simulação de Rescisão',
      actionLoadingLabel: 'Gerando simulação de rescisão...',
      action: exportTerminationSimulation,
    },
    {
      key: 'fund_cost',
      title: 'Custo de Pessoal Fundo',
      description: 'Custo consolidado por colaborador/setor para prestação ao fundo.',
      actionLabel: 'Baixar Relatório do Fundo',
      actionLoadingLabel: 'Gerando relatório do fundo...',
      action: exportFundPersonnelCost,
    },
  ];

  const selectedReportType = reportTypeOptions.find((item) => item.key === reportType) || reportTypeOptions[0];

  const monthOptions = useMemo(() => {
    return [
      { value: '1', label: 'Janeiro' },
      { value: '2', label: 'Fevereiro' },
      { value: '3', label: 'Março' },
      { value: '4', label: 'Abril' },
      { value: '5', label: 'Maio' },
      { value: '6', label: 'Junho' },
      { value: '7', label: 'Julho' },
      { value: '8', label: 'Agosto' },
      { value: '9', label: 'Setembro' },
      { value: '10', label: 'Outubro' },
      { value: '11', label: 'Novembro' },
      { value: '12', label: 'Dezembro' },
    ];
  }, []);

  const roadmapReports = [
    {
      title: 'Relatório de Custo de Folha por Centro de Custo',
      status: 'Conceito',
      scope: 'Quebra por empresa, setor, cargo e variação mensal.',
      source: 'PayrollData + Employee + WorkLocation',
    },
    {
      title: 'Relatório de Benefícios Consolidado',
      status: 'Conceito',
      scope: 'VA/VR/Mobilidade/Livre por colaborador e agregados.',
      source: 'BenefitsData + Employee',
    },
    {
      title: 'Relatório de Afastamentos e Impacto Financeiro',
      status: 'Conceito',
      scope: 'Afastamentos por tipo e correlação com custo de folha.',
      source: 'LeaveRecord + PayrollData',
    },
    {
      title: 'Relatório de Elegibilidade de Envio (WhatsApp)',
      status: 'Conceito',
      scope: 'Cobertura de telefone válido, opt-out e risco operacional.',
      source: 'Employee + Queue/Send logs',
    },
  ];

  const setQuickFilter = (preset) => {
    const now = new Date();
    if (preset === 'current') {
      handleExportParamChange('year', String(now.getFullYear()));
      handleExportParamChange('month', String(now.getMonth() + 1));
      handleExportParamChange('payrollType', 'mensal');
      return;
    }
    if (preset === 'previous') {
      const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      handleExportParamChange('year', String(prev.getFullYear()));
      handleExportParamChange('month', String(prev.getMonth() + 1));
      handleExportParamChange('payrollType', 'mensal');
      return;
    }
    if (preset === 'year_end') {
      handleExportParamChange('month', '12');
      handleExportParamChange('payrollType', 'mensal');
    }
  };

  useEffect(() => {
    const loadEmployees = async () => {
      try {
        setLoadingEmployees(true);
        const response = await api.get('/employees');
        const list = Array.isArray(response?.data?.employees) ? response.data.employees : [];
        setEmployees(list);
      } catch (error) {
        console.error('Erro ao carregar colaboradores para filtros do relatório:', error);
        toast.error('Não foi possível carregar lista de colaboradores para filtros');
      } finally {
        setLoadingEmployees(false);
      }
    };

    loadEmployees();
  }, []);

  const employeesByCompany = useMemo(() => {
    return employees.filter((employee) => {
      const companyCode = String(employee?.company_code || '');
      const uniqueId = String(employee?.unique_id || '');
      const absoluteId = String(employee?.absolute_id || '');
      return (
        companyCode === exportParams.company ||
        uniqueId.startsWith(exportParams.company) ||
        absoluteId.startsWith(exportParams.company)
      );
    });
  }, [employees, exportParams.company]);

  const departments = useMemo(() => {
    const values = new Set();
    employeesByCompany.forEach((employee) => {
      const dept = (employee?.department || '').trim();
      if (dept) values.add(dept);
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }, [employeesByCompany]);

  const filteredEmployees = useMemo(() => {
    if (!exportParams.department) return employeesByCompany;
    return employeesByCompany.filter((employee) => (employee?.department || '').trim() === exportParams.department);
  }, [employeesByCompany, exportParams.department]);

  useEffect(() => {
    if (!exportParams.employeeId) return;
    const exists = filteredEmployees.some((employee) => String(employee.id) === String(exportParams.employeeId));
    if (!exists) {
      setExportParams((prev) => ({ ...prev, employeeId: '' }));
    }
  }, [filteredEmployees, exportParams.employeeId]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className={`text-2xl font-semibold ${config.classes.text}`}>Relatórios Exportáveis</h1>
          <p className={`mt-1 text-sm ${config.classes.textSecondary}`}>
            Central de extração de dados analíticos para apoio à decisão.
          </p>
        </div>
      </div>

      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className={`text-lg font-semibold ${config.classes.text}`}>Exportação de Relatórios</h2>
            <p className={`mt-1 text-sm ${config.classes.textSecondary}`}>
              Selecione o tipo de relatório para aplicar os mesmos filtros com regras específicas.
            </p>
          </div>
          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            Produção
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
          {reportTypeOptions.map((option) => {
            const selected = reportType === option.key;
            return (
              <button
                key={option.key}
                type="button"
                onClick={() => setReportType(option.key)}
                className={`text-left rounded-lg border px-4 py-3 transition ${selected ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200 hover:bg-slate-50'}`}
              >
                <p className={`text-sm font-semibold ${selected ? 'text-emerald-800' : 'text-slate-800'}`}>{option.title}</p>
                <p className={`mt-1 text-xs ${selected ? 'text-emerald-700' : 'text-slate-500'}`}>{option.description}</p>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => setQuickFilter('current')}
            className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
          >
            Competência atual
          </button>
          <button
            onClick={() => setQuickFilter('previous')}
            className="inline-flex items-center rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
          >
            Mês anterior
          </button>
          <button
            onClick={() => setQuickFilter('year_end')}
            className="inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
          >
            Fechamento (dezembro)
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Empresa</label>
            <select
              value={exportParams.company}
              onChange={(e) => handleExportParamChange('company', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
            >
              <option value="0059">0059 - Infraestrutura</option>
              <option value="0060">0060 - Empreendimentos</option>
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Ano</label>
            <input
              type="number"
              value={exportParams.year}
              onChange={(e) => handleExportParamChange('year', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.input}`}
              min="2000"
              max="2100"
            />
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Mês</label>
            <select
              value={exportParams.month}
              onChange={(e) => handleExportParamChange('month', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
            >
              {monthOptions.map((monthOption) => (
                <option key={monthOption.value} value={monthOption.value}>
                  {monthOption.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Tipo de Folha</label>
            <select
              value={exportParams.payrollType}
              onChange={(e) => handleExportParamChange('payrollType', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
            >
              <option value="mensal">Mensal</option>
              <option value="13_adiantamento">13º - 1ª Parcela</option>
              <option value="13_integral">13º - 2ª Parcela</option>
              <option value="complementar">Complementar</option>
              <option value="adiantamento_salario">Adiantamento Salarial</option>
              <option value="all">Todos os tipos</option>
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Setor</label>
            <select
              value={exportParams.department}
              onChange={(e) => {
                handleExportParamChange('department', e.target.value);
                handleExportParamChange('employeeId', '');
              }}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
            >
              <option value="">Todos os setores</option>
              {departments.map((department) => (
                <option key={department} value={department}>
                  {department}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Colaborador</label>
            <select
              value={exportParams.employeeId}
              onChange={(e) => handleExportParamChange('employeeId', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
              disabled={loadingEmployees}
            >
              <option value="">Todos os colaboradores</option>
              {filteredEmployees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name || employee.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <div className="w-full rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
              Tipo selecionado: <span className="font-semibold text-slate-800">{selectedReportType.title}</span>
            </div>
          </div>
        </div>

        {reportType === 'termination' && (
          <div className="mt-3 grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="md:col-span-2">
              <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Cenário de rescisão</label>
              <select
                value={terminationScenario}
                onChange={(e) => setTerminationScenario(e.target.value)}
                className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
                disabled={exportingAction !== ''}
              >
                <option value="sem_justa_causa">Rescisão sem justa causa</option>
                <option value="pedido_demissao">Pedido de demissão</option>
                <option value="termino_contrato">Término de contrato</option>
              </select>
            </div>
            <div>
              <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Dia de referência</label>
              <input
                type="number"
                min="1"
                max="31"
                value={terminationDay}
                onChange={(e) => setTerminationDay(e.target.value)}
                className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.input}`}
                disabled={exportingAction !== ''}
                title="Dia de referência para simulação"
              />
            </div>
          </div>
        )}

        <div className="mt-3">
          <button
            onClick={selectedReportType.action}
            disabled={exportingAction !== ''}
            className="w-full md:w-auto inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60"
          >
            <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
            {exportingAction === selectedReportType.key ? selectedReportType.actionLoadingLabel : selectedReportType.actionLabel}
          </button>
        </div>

        <div className="mt-3 inline-flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <FunnelIcon className="h-4 w-4" />
          O filtro padrão é Mensal para evitar mistura com 13º na competência 12. Selecione o tipo do relatório para clareza na exportação.
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className={`xl:col-span-2 ${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className={`text-lg font-semibold ${config.classes.text}`}>Roadmap de Relatórios</h2>
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
              Planejamento
            </span>
          </div>

          <div className="space-y-3">
            {roadmapReports.map((item) => (
              <div key={item.title} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className={`text-sm font-semibold ${config.classes.text}`}>{item.title}</h3>
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {item.status}
                  </span>
                </div>
                <p className={`mt-1 text-sm ${config.classes.textSecondary}`}>{item.scope}</p>
                <p className="mt-2 text-xs text-slate-500">Fonte: {item.source}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-md bg-slate-50 p-3 text-xs text-slate-700">
            Sugestão de arquitetura: manter esta tela focada em extração analítica e concentrar logs operacionais em Queue Management e System Logs.
          </div>
        </div>

        <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
          <h2 className={`text-lg font-semibold ${config.classes.text} mb-4`}>Operações e Logs</h2>
          <div className="space-y-3">
            <Link
              to="/queue-management"
              className="flex items-center justify-between rounded-lg border border-slate-200 p-3 hover:bg-slate-50"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">Queue Management</p>
                <p className="text-xs text-slate-500">Status de fila, processamento e reenvios.</p>
              </div>
              <QueueListIcon className="h-5 w-5 text-slate-500" />
            </Link>

            <Link
              to="/system-logs"
              className="flex items-center justify-between rounded-lg border border-slate-200 p-3 hover:bg-slate-50"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">System Logs</p>
                <p className="text-xs text-slate-500">Logs técnicos e trilha de execução.</p>
              </div>
              <ClipboardDocumentCheckIcon className="h-5 w-5 text-slate-500" />
            </Link>

            <div className="rounded-lg border border-dashed border-slate-300 p-3">
              <p className="text-sm font-medium text-slate-700">/logs dedicado (futuro)</p>
              <p className="mt-1 text-xs text-slate-500">
                Pode consolidar logs funcionais + técnicos em visão única com busca avançada.
              </p>
            </div>

            <div className="pt-2">
              <button
                disabled
                className="w-full inline-flex items-center justify-center rounded-md bg-slate-200 px-3 py-2 text-sm font-medium text-slate-600 cursor-not-allowed"
              >
                <WrenchScrewdriverIcon className="h-4 w-4 mr-2" />
                Evolução em próximas sprints
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <div className="flex items-center gap-2 mb-3">
          <TableCellsIcon className="h-5 w-5 text-slate-600" />
          <h2 className={`text-lg font-semibold ${config.classes.text}`}>Escopo Atual da Página</h2>
        </div>
        <div className={`grid grid-cols-1 md:grid-cols-2 gap-3 text-sm ${config.classes.textSecondary}`}>
          <div className="rounded-md bg-slate-50 p-3">
            <p className="font-medium text-slate-700">Inclui</p>
            <p className="mt-1">Exportáveis estratégicos com filtros de competência, empresa e tipo de folha.</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <p className="font-medium text-slate-700">Não inclui</p>
            <p className="mt-1">Contadores operacionais de envio e logs de execução em tempo real.</p>
          </div>
        </div>
        <div className="mt-3 text-xs text-slate-500 inline-flex items-center gap-1">
          <ArrowTopRightOnSquareIcon className="h-4 w-4" />
          Para operação diária, use Queue Management e System Logs.
        </div>
      </div>
    </div>
  );
};

export default Reports;