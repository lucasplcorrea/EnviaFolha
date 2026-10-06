import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import api from '../services/api';
import {
  DocumentTextIcon,
  PaperAirplaneIcon,
  ArrowUpTrayIcon,
  DocumentArrowUpIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  FunnelIcon,
  ArrowPathIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

const currentYear = new Date().getFullYear();
const defaultSendTemplates = [
  'Olá {nome}, segue seu Informe de Rendimentos do ano-calendário {ano_calendario}. A senha do PDF são os 4 primeiros dígitos do seu CPF. Confirme o recebimento com um 👍',
  'Prezado(a) {nome}, seu Informe de Rendimentos de {ano_calendario} está disponível. A senha de abertura é composta pelos 4 primeiros dígitos do CPF. Responda OK ao receber.',
  'Oi {primeiro_nome}! Encaminhamos seu Informe de Rendimentos referente a {ano}. Para abrir o arquivo, use os 4 primeiros dígitos do CPF como senha.',
  'Olá {nome}, informe anual de rendimentos ({ano}) em anexo. Senha do PDF: 4 primeiros dígitos do CPF. Em caso de dúvidas, contate o RH.',
  'Bom dia {nome}! Seu informe de rendimentos de {ano_calendario} foi emitido. Utilize os 4 primeiros dígitos do CPF para acessar o documento.',
  'Oi {nome}, tudo bem? Segue seu Informe de Rendimentos do período {ano}. Senha do arquivo: primeiros 4 dígitos do CPF.',
  'Prezado(a) {nome}, disponibilizamos seu Informe de Rendimentos ({ano_calendario}). O documento está protegido com os 4 primeiros números do CPF.',
  'Olá {primeiro_nome}! Enviamos seu Informe de Rendimentos de {ano}. A senha para abrir o PDF são os 4 primeiros dígitos do seu CPF.',
];

const TaxStatements = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [company, setCompany] = useState('');
  const [refYear, setRefYear] = useState(currentYear - 1);
  const [processing, setProcessing] = useState(false);
  const [uploadSummary, setUploadSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [cpfSearch, setCpfSearch] = useState('');
  const [companySearch, setCompanySearch] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'created_at', direction: 'desc' });
  const [selectedIds, setSelectedIds] = useState([]);
  const [sendTemplates, setSendTemplates] = useState(defaultSendTemplates);
  const [sending, setSending] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [processStatus, setProcessStatus] = useState(null);
  const [queueStatus, setQueueStatus] = useState(null);
  const pollingRef = useRef(null);
  const processPollingRef = useRef(null);

  const sentCount = useMemo(() => rows.filter((item) => item.status === 'sent').length, [rows]);

  const filteredRows = useMemo(() => {
    return rows.filter((item) => {
      const matchesSearch =
        !searchTerm ||
        (item.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.unique_id || '').toLowerCase().includes(searchTerm.toLowerCase());

      const cpfDigits = (item.cpf || '').replace(/\D/g, '');
      const searchCpfDigits = (cpfSearch || '').replace(/\D/g, '');
      const matchesCpf = !searchCpfDigits || cpfDigits.includes(searchCpfDigits);

      const matchesCompanySearch =
        !companySearch || (item.company || '').toLowerCase().includes(companySearch.toLowerCase());

      return matchesSearch && matchesCpf && matchesCompanySearch;
    });
  }, [rows, searchTerm, cpfSearch, companySearch]);

  const sortedRows = useMemo(() => {
    if (!sortConfig.key) return filteredRows;

    return [...filteredRows].sort((a, b) => {
      let aValue = a[sortConfig.key];
      let bValue = b[sortConfig.key];

      if (sortConfig.key === 'created_at') {
        aValue = aValue ? new Date(aValue).getTime() : 0;
        bValue = bValue ? new Date(bValue).getTime() : 0;
      } else if (sortConfig.key === 'ref_year') {
        aValue = Number(aValue) || 0;
        bValue = Number(bValue) || 0;
      } else {
        aValue = (aValue || '').toString().toLowerCase();
        bValue = (bValue || '').toString().toLowerCase();
      }

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredRows, sortConfig]);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return <ChevronDownIcon className="h-4 w-4 text-gray-300" />;
    }
    return sortConfig.direction === 'asc' ? (
      <ChevronUpIcon className="h-4 w-4 text-gray-600" />
    ) : (
      <ChevronDownIcon className="h-4 w-4 text-gray-600" />
    );
  };

  const availableCompanies = useMemo(() => {
    const values = new Set(rows.map((item) => item.company).filter(Boolean));
    return Array.from(values).sort();
  }, [rows]);

  const loadStatements = useCallback(async () => {
    try {
      setLoading(true);
      const params = {
        page: 1,
        page_size: 200,
      };
      if (statusFilter) params.status = statusFilter;
      if (companyFilter) params.company = companyFilter;
      if (refYear) params.ref_year = refYear;

      const response = await api.get('/tax-statements', { params });
      setRows(response.data.tax_statements || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Erro ao carregar informes:', error);
      toast.error('Erro ao carregar informes de rendimentos');
    } finally {
      setLoading(false);
    }
  }, [companyFilter, refYear, statusFilter]);

  useEffect(() => {
    loadStatements();
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
      if (processPollingRef.current) {
        clearInterval(processPollingRef.current);
      }
    };
  }, [loadStatements]);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.includes('pdf')) {
      toast.error('Selecione um arquivo PDF');
      return;
    }

    setSelectedFile(file);
  };

  const isSendSelectable = (item) => {
    // Permite reenviar falhas de envio (status failed) desde que haja vínculo com colaborador.
    return !!item?.employee_id && (item.status === 'processed' || item.status === 'failed');
  };

  const pollProcessStatus = async (jobId) => {
    try {
      const response = await api.get(`/tax-statements/process/${jobId}/status`);
      const status = response.data;
      setProcessStatus(status);

      if (status.status === 'completed' || status.status === 'failed') {
        if (processPollingRef.current) {
          clearInterval(processPollingRef.current);
          processPollingRef.current = null;
        }
        setProcessing(false);

        if (status.status === 'completed') {
          setUploadSummary(status.result || null);
          setSelectedFile(null);
          toast.success('Processamento de informes concluído');
          await loadStatements();
        } else {
          toast.error(status.error || 'Falha no processamento dos informes');
        }
      }
    } catch (error) {
      console.error('Erro ao consultar status do processamento IR:', error);
    }
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      toast.error('Selecione um PDF consolidado');
      return;
    }

    try {
      setProcessing(true);
      const formData = new FormData();
      formData.append('file', selectedFile);

      const params = new URLSearchParams();
      if (company) params.append('company', company);
      if (refYear) params.append('ref_year', String(refYear));

      const response = await api.post(`/tax-statements/process?${params.toString()}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000,
      });

      const job = response.data.job;
      setProcessStatus(job || null);
      toast.success('Processamento iniciado em segundo plano');

      if (job?.job_id) {
        if (processPollingRef.current) {
          clearInterval(processPollingRef.current);
        }
        processPollingRef.current = setInterval(() => pollProcessStatus(job.job_id), 2000);
        await pollProcessStatus(job.job_id);
      }
    } catch (error) {
      console.error('Erro ao processar informe:', error);
      setProcessing(false);
      toast.error(error.response?.data?.error || 'Erro ao processar PDF');
    }
  };

  const toggleSelect = (statementId, checked) => {
    setSelectedIds((prev) => {
      if (checked) {
        return [...prev, statementId];
      }
      return prev.filter((id) => id !== statementId);
    });
  };

  const handleSelectReady = () => {
    const readyIds = rows.filter((item) => isSendSelectable(item)).map((item) => item.id);
    setSelectedIds(readyIds);
  };

  const handleClearSelection = () => {
    setSelectedIds([]);
  };

  const updateTemplate = (index, value) => {
    setSendTemplates((prev) => prev.map((item, idx) => (idx === index ? value : item)));
  };

  const resetTemplates = () => {
    setSendTemplates(defaultSendTemplates);
  };

  const pollQueueStatus = async (queueId) => {
    try {
      const response = await api.get(`/tax-statements/send/${queueId}/status`);
      const status = response.data;
      setQueueStatus(status);

      if (status.status === 'completed' || status.status === 'failed') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setSending(false);
        await loadStatements();

        if (status.status === 'completed') {
          toast.success('Fila de envio de informes concluída');
        } else {
          toast.error(status.error || 'Fila de envio falhou');
        }
      }
    } catch (error) {
      console.error('Erro ao consultar status da fila IR:', error);
    }
  };

  const handleSend = async () => {
    if (selectedIds.length === 0) {
      toast.error('Selecione ao menos um informe processado ou com falha de envio');
      return;
    }

    const activeTemplates = sendTemplates.map((item) => item.trim()).filter(Boolean);
    if (activeTemplates.length === 0) {
      toast.error('Preencha ao menos um template de mensagem');
      return;
    }

    try {
      setSending(true);
      const response = await api.post('/tax-statements/send', {
        statement_ids: selectedIds,
        message_template: activeTemplates[0] || null,
        message_templates: activeTemplates,
      });

      const queueId = response.data.queue?.queue_id;
      setQueueStatus(response.data.queue || null);
      toast.success('Fila de envio iniciada');

      if (queueId) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
        }
        pollingRef.current = setInterval(() => pollQueueStatus(queueId), 3000);
        await pollQueueStatus(queueId);
      }
    } catch (error) {
      console.error('Erro ao iniciar envio:', error);
      setSending(false);
      toast.error(error.response?.data?.error || 'Erro ao iniciar envio dos informes');
    }
  };

  const handleExportSentZip = async () => {
    try {
      toast.loading('Gerando ZIP dos informes enviados...', { id: 'tax-statements-export' });

      const params = new URLSearchParams();
      if (companyFilter) params.append('company', companyFilter);
      if (refYear) params.append('ref_year', String(refYear));

      const response = await api.get(`/tax-statements/export/sent?${params.toString()}`, {
        responseType: 'blob',
        timeout: 300000,
      });

      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      const headerName = response.headers['content-disposition'];
      let fileName = `Informes_Enviados_${refYear || 'todos'}.zip`;

      if (headerName) {
        const match = headerName.match(/filename="?([^";]+)"?/i);
        if (match?.[1]) {
          fileName = match[1];
        }
      }

      link.href = url;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success('ZIP exportado com sucesso', { id: 'tax-statements-export' });
    } catch (error) {
      console.error('Erro ao exportar ZIP de informes enviados:', error);
      toast.error(error.response?.data?.error || 'Erro ao exportar ZIP dos informes enviados', {
        id: 'tax-statements-export',
      });
    }
  };

  const handleDeleteByIds = async (ids) => {
    if (!ids || ids.length === 0) {
      toast.error('Selecione ao menos um informe para excluir');
      return;
    }

    const confirmed = window.confirm(`Confirma excluir ${ids.length} informe(s) selecionado(s)?`);
    if (!confirmed) return;

    try {
      setDeleting(true);
      const response = await api.post('/tax-statements/delete', { statement_ids: ids });
      const details = response.data || {};
      toast.success(
        `Excluídos: ${details.deleted_records || 0} registros, ${details.deleted_files || 0} arquivos removidos.`
      );
      setSelectedIds([]);
      await loadStatements();
    } catch (error) {
      console.error('Erro ao excluir informes selecionados:', error);
      toast.error(error.response?.data?.error || 'Erro ao excluir informes selecionados');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteFiltered = async () => {
    const hasAnyFilter = !!(refYear || companyFilter || statusFilter);
    if (!hasAnyFilter) {
      toast.error('Defina ao menos um filtro (ano/empresa/status) antes de excluir em lote');
      return;
    }

    const confirmed = window.confirm(
      `Confirma excluir todos os informes do filtro atual?\nAno: ${refYear || 'todos'} | Empresa: ${companyFilter || 'todas'} | Status: ${statusFilter || 'todos'}`
    );
    if (!confirmed) return;

    try {
      setDeleting(true);
      const payload = {
        ref_year: refYear || null,
        company: companyFilter || null,
        status: statusFilter || null,
      };
      const response = await api.post('/tax-statements/delete', payload);
      const details = response.data || {};
      toast.success(
        `Excluídos: ${details.deleted_records || 0} registros, ${details.deleted_files || 0} arquivos removidos.`
      );
      setSelectedIds([]);
      await loadStatements();
    } catch (error) {
      console.error('Erro ao excluir informes por filtro:', error);
      toast.error(error.response?.data?.error || 'Erro ao excluir informes por filtro');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteSingle = async (row) => {
    if (!row?.id) return;
    const confirmed = window.confirm(`Confirma excluir o informe ${row.unique_id}.pdf?`);
    if (!confirmed) return;
    await handleDeleteByIds([row.id]);
  };

  const getStatusBadge = (status) => {
    const map = {
      processed: { text: 'Processado', cls: 'bg-green-100 text-green-700', icon: CheckCircleIcon },
      sent: { text: 'Enviado', cls: 'bg-blue-100 text-blue-700', icon: PaperAirplaneIcon },
      failed: { text: 'Falhou', cls: 'bg-red-100 text-red-700', icon: XCircleIcon },
      pending: { text: 'Pendente', cls: 'bg-yellow-100 text-yellow-700', icon: ClockIcon },
    };
    const cfg = map[status] || map.pending;
    const Icon = cfg.icon;
    return (
      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${cfg.cls}`}>
        <Icon className="h-3.5 w-3.5" />
        {cfg.text}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Informes de Rendimentos</h1>
          <p className="mt-1 text-sm text-gray-600">
            Processe PDFs consolidados, revise falhas e dispare a fila de envio via WhatsApp.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportSentZip}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <DocumentTextIcon className="h-4 w-4" />
            Exportar ZIP dos enviados
          </button>
          <button
            onClick={loadStatements}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowPathIcon className="h-4 w-4" />
            Atualizar
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <ArrowUpTrayIcon className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">Processar PDF consolidado</h2>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Empresa</label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Ex: AB EMPREENDIMENTOS"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Ano-calendário</label>
              <input
                type="number"
                value={refYear}
                onChange={(e) => setRefYear(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-dashed border-gray-300 p-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
              <div className="text-center">
                <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                <div className="mt-4">
                  <label htmlFor="ir-pdf-upload" className="cursor-pointer">
                    <span className="mt-2 block text-sm font-medium text-gray-900">
                      Selecione o PDF consolidado de informes
                    </span>
                    <span className="mt-1 block text-sm text-gray-500">
                      Apenas arquivos PDF
                    </span>
                  </label>
                  <input
                    id="ir-pdf-upload"
                    name="ir-pdf-upload"
                    type="file"
                    accept=".pdf"
                    className="sr-only"
                    onChange={handleFileChange}
                    disabled={processing}
                  />
                </div>
              </div>
            </div>

            {selectedFile && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center">
                  <CheckCircleIcon className="h-5 w-5 text-green-400" />
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-green-800">Arquivo carregado</h4>
                    <p className="text-sm text-green-700">{selectedFile.name}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleProcess}
              disabled={processing || !selectedFile}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <DocumentTextIcon className="h-4 w-4" />
              {processing ? 'Processando...' : 'Processar informe'}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Resumo do último lote</h2>
          {uploadSummary ? (
            <div className="space-y-3 text-sm text-gray-700">
              <div>Total detectado: <strong>{uploadSummary.chunks_detected}</strong></div>
              <div>Processados com sucesso: <strong>{uploadSummary.processed_success}</strong></div>
              <div>Falhas: <strong>{uploadSummary.processed_failed}</strong></div>
              <div>Taxa de sucesso: <strong>{uploadSummary.success_rate}%</strong></div>
              {uploadSummary.company && <div>Empresa do lote: <strong>{uploadSummary.company}</strong></div>}
              {uploadSummary.mixed_companies && <div className="text-amber-700">Lote misto detectado: {uploadSummary.companies_detected?.join(', ')}</div>}
              <div className="break-all text-xs text-gray-500">CSV sucesso: {uploadSummary.success_csv}</div>
              <div className="break-all text-xs text-gray-500">CSV erros: {uploadSummary.error_csv}</div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Nenhum lote processado nesta sessão.</p>
          )}

          {processStatus && (
            <div className="mt-6 rounded-lg bg-blue-50 p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-900">Processamento em andamento</h3>
              <div className="space-y-1 text-sm text-gray-700">
                <div>Status: <strong>{processStatus.status}</strong></div>
                <div>Mensagem: <strong>{processStatus.message || '-'}</strong></div>
                <div>Total detectado: <strong>{processStatus.total_chunks ?? 0}</strong></div>
                <div>Processados: <strong>{processStatus.processed_chunks ?? 0}</strong></div>
                <div>Sucessos: <strong>{processStatus.successful_chunks ?? 0}</strong></div>
                <div>Falhas: <strong>{processStatus.failed_chunks ?? 0}</strong></div>
                {processStatus.current_chunk ? (
                  <div>Chunk atual: <strong>{processStatus.current_chunk}</strong>{processStatus.current_page_range ? ` (${processStatus.current_page_range})` : ''}</div>
                ) : null}
              </div>
            </div>
          )}

          {queueStatus && (
            <div className="mt-6 rounded-lg bg-gray-50 p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-900">Fila de envio</h3>
              <div className="space-y-1 text-sm text-gray-700">
                <div>Status: <strong>{queueStatus.status}</strong></div>
                <div>Total: <strong>{queueStatus.total_items ?? queueStatus.accepted_items ?? 0}</strong></div>
                <div>Processados: <strong>{queueStatus.processed_items ?? 0}</strong></div>
                <div>Sucessos: <strong>{queueStatus.successful_items ?? 0}</strong></div>
                <div>Falhas: <strong>{queueStatus.failed_items ?? 0}</strong></div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Informes processados</h2>
            <p className="text-sm text-gray-500">{filteredRows.length} de {total} registro(s), {sentCount} enviado(s) no recorte atual</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
              <FunnelIcon className="h-4 w-4 text-gray-500" />
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="bg-transparent outline-none">
                <option value="">Todos status</option>
                <option value="processed">Processado</option>
                <option value="sent">Enviado</option>
                <option value="failed">Falhou</option>
              </select>
            </div>
            <div className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
              <select value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)} className="bg-transparent outline-none">
                <option value="">Todas empresas</option>
                {availableCompanies.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleDeleteFiltered}
              disabled={deleting}
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4" />
              Excluir período/filtro
            </button>
          </div>
        </div>

        <div className="mb-4 grid gap-3 md:grid-cols-3">
          <input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Pesquisar por colaborador ou arquivo"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            value={cpfSearch}
            onChange={(e) => setCpfSearch(e.target.value)}
            placeholder="Pesquisar por CPF"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            value={companySearch}
            onChange={(e) => setCompanySearch(e.target.value)}
            placeholder="Pesquisar por empresa"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="mb-4 grid gap-4 lg:grid-cols-[1fr_auto]">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-700">
                Templates de mensagem (8 variações com placeholders {'{nome}'}, {'{primeiro_nome}'}, {'{ano_calendario}'})
              </p>
              <button
                onClick={resetTemplates}
                type="button"
                className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Restaurar templates padrão
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {sendTemplates.map((template, index) => (
                <textarea
                  key={`ir-template-${index + 1}`}
                  value={template}
                  onChange={(e) => updateTemplate(index, e.target.value)}
                  rows={3}
                  placeholder={`Template ${index + 1}`}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-start gap-2 lg:flex-col">
            <button onClick={handleSelectReady} className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Selecionar prontos/falhos
            </button>
            <button onClick={handleClearSelection} className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Limpar seleção
            </button>
            <button
              onClick={() => handleDeleteByIds(selectedIds)}
              disabled={deleting || selectedIds.length === 0}
              className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4" />
              Excluir selecionados ({selectedIds.length})
            </button>
            <button
              onClick={handleSend}
              disabled={sending || selectedIds.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <PaperAirplaneIcon className="h-4 w-4" />
              {sending ? 'Enviando...' : `Enviar selecionados (${selectedIds.length})`}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Sel.</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  <button type="button" onClick={() => handleSort('unique_id')} className="inline-flex items-center gap-1 hover:text-gray-700">
                    Arquivo {getSortIcon('unique_id')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  <button type="button" onClick={() => handleSort('employee_name')} className="inline-flex items-center gap-1 hover:text-gray-700">
                    Colaborador {getSortIcon('employee_name')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  <button type="button" onClick={() => handleSort('cpf')} className="inline-flex items-center gap-1 hover:text-gray-700">
                    CPF {getSortIcon('cpf')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  <button type="button" onClick={() => handleSort('ref_year')} className="inline-flex items-center gap-1 hover:text-gray-700">
                    Ano {getSortIcon('ref_year')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  <button type="button" onClick={() => handleSort('company')} className="inline-flex items-center gap-1 hover:text-gray-700">
                    Empresa {getSortIcon('company')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  <button type="button" onClick={() => handleSort('status')} className="inline-flex items-center gap-1 hover:text-gray-700">
                    Status {getSortIcon('status')}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-gray-500">Carregando informes...</td>
                </tr>
              ) : sortedRows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-gray-500">Nenhum informe encontrado.</td>
                </tr>
              ) : (
                sortedRows.map((row) => {
                  const selectable = isSendSelectable(row);
                  return (
                    <tr key={row.id}>
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(row.id)}
                          disabled={!selectable}
                          onChange={(e) => toggleSelect(row.id, e.target.checked)}
                        />
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900">{row.unique_id}.pdf</td>
                      <td className="px-4 py-3 text-gray-700">{row.employee_name || 'Não encontrado'}</td>
                      <td className="px-4 py-3 text-gray-700">{row.cpf}</td>
                      <td className="px-4 py-3 text-gray-700">{row.ref_year}</td>
                      <td className="px-4 py-3 text-gray-700">{row.company || '-'}</td>
                      <td className="px-4 py-3">{getStatusBadge(row.status)}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleDeleteSingle(row)}
                          disabled={deleting}
                          className="inline-flex items-center gap-1 rounded-md border border-red-300 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                          Excluir
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TaxStatements;
