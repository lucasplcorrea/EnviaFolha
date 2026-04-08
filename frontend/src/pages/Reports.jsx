import React, { useMemo, useState } from 'react';
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
  const [exporting, setExporting] = useState(false);
  const [exportParams, setExportParams] = useState({
    company: '0059',
    year: '2025',
    month: '12',
    payrollType: 'mensal'
  });

  const handleExportParamChange = (field, value) => {
    setExportParams(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const exportReports = async () => {
    try {
      setExporting(true);
      const toastId = toast.loading('Gerando relatório estratégico...');

      const response = await api.get('/reports/exports/infra-analytics', {
        params: {
          company: exportParams.company,
          year: exportParams.year,
          month: exportParams.month,
          payroll_type: exportParams.payrollType
        },
        responseType: 'blob'
      });

      const contentDisposition = response.headers['content-disposition'] || '';
      const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
      const filename = filenameMatch?.[1] || `relatorio_estrategico_${exportParams.company}_${exportParams.year}-${String(exportParams.month).padStart(2, '0')}.xlsx`;

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

      toast.success('Relatório exportado com sucesso', { id: toastId });
    } catch (error) {
      console.error('Erro ao exportar relatório:', error);
      const detail = error?.response?.data?.error;
      toast.error(detail || 'Erro ao exportar relatório estratégico');
    } finally {
      setExporting(false);
    }
  };

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
            <h2 className={`text-lg font-semibold ${config.classes.text}`}>Relatório Estratégico Exportável</h2>
            <p className={`mt-1 text-sm ${config.classes.textSecondary}`}>
              Colaboradores ativos com folha e benefícios segmentados por competência e tipo de folha.
            </p>
          </div>
          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            Produção
          </span>
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

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
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
          <div className="flex items-end">
            <button
              onClick={exportReports}
              disabled={exporting}
              className="w-full inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60"
            >
              <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
              {exporting ? 'Gerando...' : 'Baixar Relatório'}
            </button>
          </div>
        </div>

        <div className="mt-3 inline-flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <FunnelIcon className="h-4 w-4" />
          O filtro padrão é Mensal para evitar mistura com 13º na competência 12.
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