import React, { useState, useEffect } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  DocumentArrowUpIcon,
  FolderOpenIcon,
  CalendarIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  TrashIcon,
  BuildingOfficeIcon,
  UserPlusIcon,
  GiftIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import TimecardUpload from './TimecardUpload';

const PayrollDataProcessor = () => {
  const [activeTab, setActiveTab] = useState('payroll'); // 'payroll', 'benefits' ou 'timecard'
  
  // Estados para CSVs de folha
  const [periods, setPeriods] = useState([]);
  const [csvFiles, setCsvFiles] = useState([]);
  const [csvDivision, setCsvDivision] = useState('0060');
  const [csvAutoCreate, setCsvAutoCreate] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvResult, setCsvResult] = useState(null);
  const [processingHistory, setProcessingHistory] = useState([]);
  
  // Estados para benefícios
  const [benefitsPeriods, setBenefitsPeriods] = useState([]);
  const [benefitsProcessingHistory, setBenefitsProcessingHistory] = useState([]);
  const [xlsxFile, setXlsxFile] = useState(null);
  const [xlsxYear, setXlsxYear] = useState(new Date().getFullYear());
  const [xlsxMonth, setXlsxMonth] = useState(new Date().getMonth() + 1);
  const [xlsxCompany, setXlsxCompany] = useState('0060');
  const [benefitsMergeMode, setBenefitsMergeMode] = useState('sum');
  const [benefitsSourceLabel, setBenefitsSourceLabel] = useState('');
  const [xlsxUploading, setXlsxUploading] = useState(false);
  const [xlsxResult, setXlsxResult] = useState(null);
  
  // Estados para modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [periodToDelete, setPeriodToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deletingBenefitsLogId, setDeletingBenefitsLogId] = useState(null);

  useEffect(() => {
    loadPeriods();
    loadProcessingHistory();
    loadBenefitsPeriods();
    loadBenefitsProcessingHistory();
  }, []);

  const loadPeriods = async () => {
    try {
      const response = await api.get('/payroll/periods');
      setPeriods(response.data.periods || []);
    } catch (error) {
      toast.error('Erro ao carregar períodos');
      console.error('Erro ao carregar períodos:', error);
    }
  };

  const loadBenefitsPeriods = async () => {
    try {
      const response = await api.get('/benefits/periods');
      setBenefitsPeriods(response.data.periods || []);
    } catch (error) {
      console.error('Erro ao carregar períodos de benefícios:', error);
    }
  };

  const loadProcessingHistory = async () => {
    try {
      const response = await api.get('/payroll/processing-history');
      if (response.data.success) {
        setProcessingHistory(response.data.history || []);
      }
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
    }
  };

  const loadBenefitsProcessingHistory = async () => {
    try {
      const response = await api.get('/benefits/processing-logs');
      setBenefitsProcessingHistory(response.data.logs || []);
    } catch (error) {
      console.error('Erro ao carregar histórico de benefícios:', error);
    }
  };

  const confirmDeletePeriod = (period) => {
    setPeriodToDelete({ ...period, type: 'payroll' });
    setShowDeleteModal(true);
  };

  const handleDeletePeriod = async () => {
    if (!periodToDelete) return;

    setDeleting(true);
    try {
      // Determinar endpoint baseado no tipo
      const endpoint = periodToDelete.type === 'benefits' 
        ? `/benefits/periods/${periodToDelete.id}`
        : `/payroll/periods/${periodToDelete.id}`;
      
      const response = await api.delete(endpoint);
      
      if (response.data.success) {
        toast.success(`Período "${periodToDelete.period_name}" deletado com sucesso!`);
        setShowDeleteModal(false);
        setPeriodToDelete(null);
        
        // Recarregar lista apropriada
        if (periodToDelete.type === 'benefits') {
          loadBenefitsPeriods();
        } else {
          loadPeriods();
        }
      } else {
        toast.error(response.data.error || 'Erro ao deletar período');
      }
    } catch (error) {
      console.error('Erro ao deletar período:', error);
      toast.error(error.response?.data?.error || 'Erro ao deletar período');
    } finally {
      setDeleting(false);
    }
  };

  const handleCsvFileSelect = (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const invalidFiles = files.filter(f => !f.name.endsWith('.csv') && !f.name.endsWith('.CSV'));
    if (invalidFiles.length > 0) {
      toast.error('Por favor, selecione apenas arquivos CSV');
      return;
    }

    setCsvFiles(files);
    setCsvResult(null);
  };

  const handleCsvUpload = async () => {
    if (csvFiles.length === 0) {
      toast.error('Selecione pelo menos um arquivo CSV');
      return;
    }

    setCsvUploading(true);
    setCsvResult(null);

    const results = [];
    let successCount = 0;
    let errorCount = 0;

    try {
      for (let i = 0; i < csvFiles.length; i++) {
        const file = csvFiles[i];
        toast.loading(`Processando ${i + 1}/${csvFiles.length}: ${file.name}...`, { id: `upload-${i}` });

        try {
          // 1. Upload do arquivo
          const formData = new FormData();
          formData.append('file', file);

          const uploadResponse = await api.post('/files/upload', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });

          const filePath = uploadResponse.data.file_path;

          // 2. Processar o CSV
          const processResponse = await api.post('/payroll/upload-csv', {
            file_path: filePath,
            division_code: csvDivision,
            auto_create_employees: csvAutoCreate,
            period_id: selectedPeriod || null,
          });

          const result = processResponse.data;
          results.push({ file: file.name, ...result });

          if (result.success) {
            successCount++;
            toast.success(`✅ ${file.name} processado!`, { id: `upload-${i}` });
          } else {
            errorCount++;
            toast.error(`❌ ${file.name}: ${result.error}`, { id: `upload-${i}` });
          }
        } catch (error) {
          errorCount++;
          toast.error(`❌ ${file.name}: ${error.response?.data?.error || error.message}`, { id: `upload-${i}` });
          results.push({ 
            file: file.name, 
            success: false, 
            error: error.response?.data?.error || error.message 
          });
        }
      }

      // Resumo final
      setCsvResult({
        success: successCount > 0,
        summary: `${successCount} arquivo(s) processado(s) com sucesso, ${errorCount} erro(s)`,
        results: results
      });

      if (successCount > 0) {
        loadPeriods();
        loadProcessingHistory();
        setCsvFiles([]);
      }
    } finally {
      setCsvUploading(false);
    }
  };

  // ========================================
  // FUNÇÕES DE BENEFÍCIOS
  // ========================================
  
  const handleXlsxFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const fileName = file.name.toLowerCase();
    const allowedExtensions = ['.xlsx', '.xlsm', '.xltx', '.xltm', '.csv', '.txt'];
    const isValidFile = allowedExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValidFile) {
      toast.error('Selecione um arquivo CSV ou XLSX');
      return;
    }

    setXlsxFile(file);
    setXlsxResult(null);
  };

  const handleXlsxUpload = async () => {
    if (!xlsxFile) {
      toast.error('Selecione um arquivo CSV ou XLSX');
      return;
    }

    setXlsxUploading(true);
    setXlsxResult(null);

    try {
      toast.loading('Processando arquivo de benefícios...', { id: 'xlsx-upload' });

      const formData = new FormData();
      formData.append('file', xlsxFile);
      formData.append('year', xlsxYear);
      formData.append('month', xlsxMonth);
      formData.append('company', xlsxCompany);
      formData.append('merge_mode', benefitsMergeMode);
      formData.append('source_label', benefitsSourceLabel);

      const response = await api.post('/benefits/upload-xlsx', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const result = response.data;

      if (result.success) {
        toast.success('Benefícios processados com sucesso!', { id: 'xlsx-upload' });
        setXlsxResult(result);
        loadBenefitsPeriods();
        loadBenefitsProcessingHistory();
        setXlsxFile(null);
        setBenefitsSourceLabel('');
      } else {
        toast.error(result.error || 'Erro ao processar benefícios', { id: 'xlsx-upload' });
        setXlsxResult(result);
      }
    } catch (error) {
      console.error('Erro ao fazer upload de XLSX:', error);
      toast.error(error.response?.data?.error || 'Erro ao processar benefícios', { id: 'xlsx-upload' });
      setXlsxResult({ 
        success: false, 
        error: error.response?.data?.error || error.message 
      });
    } finally {
      setXlsxUploading(false);
    }
  };

  const confirmDeleteBenefitsPeriod = (period) => {
    setPeriodToDelete({ ...period, type: 'benefits' });
    setShowDeleteModal(true);
  };

  const handleDeleteBenefitsPeriod = async () => {
    if (!periodToDelete || periodToDelete.type !== 'benefits') return;

    setDeleting(true);
    try {
      const response = await api.delete(`/benefits/periods/${periodToDelete.id}`);
      
      if (response.data.success) {
        toast.success(`Período de benefícios "${periodToDelete.period_name}" deletado!`);
        setShowDeleteModal(false);
        setPeriodToDelete(null);
        loadBenefitsPeriods();
      } else {
        toast.error(response.data.error || 'Erro ao deletar período');
      }
    } catch (error) {
      console.error('Erro ao deletar período de benefícios:', error);
      toast.error(error.response?.data?.error || 'Erro ao deletar período');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteBenefitsUploadLog = async (log) => {
    if (!log || !log.id) return;

    const label = log.filename || `ID ${log.id}`;
    const confirmed = window.confirm(
      `Deseja remover somente este upload de benefícios?\n\nArquivo: ${label}\nPeríodo: ${log.period_name || `${String(log.month).padStart(2, '0')}/${log.year}`}\n\nA ação vai desfazer os valores deste upload e manter os demais.`
    );

    if (!confirmed) return;

    try {
      setDeletingBenefitsLogId(log.id);
      const response = await api.delete(`/benefits/processing-logs/${log.id}`);

      if (response.data?.success) {
        toast.success(response.data.message || 'Upload removido com sucesso');
        loadBenefitsPeriods();
        loadBenefitsProcessingHistory();
      } else {
        toast.error(response.data?.error || 'Não foi possível remover este upload');
      }
    } catch (error) {
      console.error('Erro ao remover upload de benefícios:', error);
      toast.error(error.response?.data?.error || 'Erro ao remover upload de benefícios');
    } finally {
      setDeletingBenefitsLogId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <FolderOpenIcon className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Processamento de Dados RH</h1>
            <p className="text-gray-600">Importe arquivos de folha de pagamento e benefícios</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('payroll')}
            className={`${
              activeTab === 'payroll'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors`}
          >
            <DocumentArrowUpIcon className="h-5 w-5" />
            <span>Folha de Pagamento (CSV)</span>
          </button>
          <button
            onClick={() => setActiveTab('benefits')}
            className={`${
              activeTab === 'benefits'
                ? 'border-green-500 text-green-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors`}
          >
            <GiftIcon className="h-5 w-5" />
            <span>Benefícios iFood (CSV/XLSX)</span>
          </button>
          <button
            onClick={() => setActiveTab('timecard')}
            className={`${
              activeTab === 'timecard'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors`}
          >
            <ClockIcon className="h-5 w-5" />
            <span>Cartão Ponto (XLSX)</span>
          </button>
        </nav>
      </div>

      {/* Tab Content - Payroll */}
      {activeTab === 'payroll' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Upload Section */}
            <div className="lg:col-span-2 bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Upload de Arquivo CSV</h2>
          
              <div className="space-y-5">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Arquivo CSV
              </label>
              <div className="flex items-center space-x-3">
                <input
                  type="file"
                  accept=".csv,.CSV"
                  multiple
                  onChange={handleCsvFileSelect}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {csvFiles.length > 0 && (
                  <button
                    onClick={() => {
                      setCsvFiles([]);
                      setCsvResult(null);
                    }}
                    className="text-red-600 hover:text-red-800"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                )}
              </div>
              {csvFiles.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-sm font-medium text-green-600">
                    ✓ {csvFiles.length} arquivo(s) selecionado(s):
                  </p>
                  <ul className="text-sm text-gray-600 ml-4">
                    {csvFiles.map((f, idx) => (
                      <li key={idx}>• {f.name} ({(f.size / 1024).toFixed(2)} KB)</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Period Selection (Optional) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Período (Opcional)
              </label>
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Detectar automaticamente pelo nome do arquivo</option>
                {periods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {period.period_name} ({period.year})
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Se não especificado, o período será criado/detectado pelo nome do arquivo
              </p>
            </div>

            {/* Division/Company Code */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <BuildingOfficeIcon className="inline h-4 w-4 mr-1" />
                Empresa
              </label>
              <select
                value={csvDivision}
                onChange={(e) => setCsvDivision(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="0060">0060 - Empreendimentos</option>
                <option value="0059">0059 - Infraestrutura</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Selecione a empresa para processar os dados
              </p>
            </div>

            {/* Auto Create Employees */}
            <div className="flex items-start space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <input
                type="checkbox"
                id="autoCreate"
                checked={csvAutoCreate}
                onChange={(e) => setCsvAutoCreate(e.target.checked)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <label htmlFor="autoCreate" className="font-medium text-gray-900 cursor-pointer flex items-center">
                  <UserPlusIcon className="h-4 w-4 mr-1.5 text-blue-600" />
                  Criar colaboradores automaticamente
                </label>
                <p className="text-sm text-gray-600 mt-1">
                  Se ativado, colaboradores que não existirem no sistema serão criados automaticamente durante o processamento
                </p>
              </div>
            </div>

            {/* Upload Button */}
            <button
              onClick={handleCsvUpload}
              disabled={csvFiles.length === 0 || csvUploading}
              className={`w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg font-medium transition-all ${
                csvFiles.length === 0 || csvUploading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg'
              }`}
            >
              {csvUploading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <DocumentArrowUpIcon className="h-5 w-5" />
                  <span>Processar {csvFiles.length} CSV{csvFiles.length > 1 ? 's' : ''}</span>
                </>
              )}
            </button>

            {/* Result Display */}
            {csvResult && (
              <div className={`p-4 rounded-lg border ${
                csvResult.success 
                  ? 'bg-green-50 border-green-200' 
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-start space-x-3">
                  {csvResult.success ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircleIcon className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <h4 className={`font-medium ${csvResult.success ? 'text-green-900' : 'text-red-900'}`}>
                      {csvResult.success ? 'Processamento Concluído!' : 'Erro no Processamento'}
                    </h4>
                    
                    {/* Resumo geral para múltiplos arquivos */}
                    {csvResult.summary && (
                      <p className="mt-2 text-sm font-medium">{csvResult.summary}</p>
                    )}
                    
                    {/* Detalhes de cada arquivo */}
                    {csvResult.results && csvResult.results.length > 0 && (
                      <div className="mt-3 space-y-2 max-h-60 overflow-y-auto">
                        {csvResult.results.map((result, idx) => (
                          <div key={idx} className={`text-sm p-2 rounded ${
                            result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            <p className="font-medium">{result.file}</p>
                            {result.success && result.stats && (
                              <p className="text-xs mt-1">
                                {result.stats.processed}/{result.stats.total_rows} linhas, {result.stats.new_employees} novos
                              </p>
                            )}
                            {result.error && (
                              <p className="text-xs mt-1">{result.error}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Resultado único (retrocompatibilidade) */}
                    {csvResult.stats && !csvResult.results && (
                      <div className="mt-2 text-sm text-green-800 space-y-1">
                        <p>• Total de linhas: {csvResult.stats.total_rows}</p>
                        <p>• Processadas: {csvResult.stats.processed}</p>
                        <p>• Novos funcionários: {csvResult.stats.new_employees}</p>
                        {csvResult.stats.period_name && (
                          <p>• Período: {csvResult.stats.period_name}</p>
                        )}
                      </div>
                    )}
                    {csvResult.error && !csvResult.results && (
                      <p className="mt-2 text-sm text-red-800">{csvResult.error}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Periods List */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Períodos Cadastrados</h2>
          
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {periods.map((period) => (
              <div key={period.id} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900 text-sm">{period.period_name}</h3>
                      {/* Badge da empresa */}
                      {period.company_name && (
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                          period.company === '0060' 
                            ? 'bg-blue-100 text-blue-800' 
                            : 'bg-purple-100 text-purple-800'
                        }`}>
                          {period.company_name}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {period.month}/{period.year}
                    </p>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    {period.is_closed && (
                      <span className="inline-flex px-2 py-0.5 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                        Fechado
                      </span>
                    )}
                    <button
                      onClick={() => confirmDeletePeriod(period)}
                      className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="Deletar Período"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
            
            {periods.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <CalendarIcon className="mx-auto h-12 w-12 text-gray-300" />
                <p className="mt-2 text-sm">Nenhum período encontrado</p>
                <p className="text-xs">Faça upload de um CSV para criar</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Processing History */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Histórico de Processamento</h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data/Hora</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Arquivo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Período</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Registros</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuário</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processingHistory.length > 0 ? (
                processingHistory.map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString('pt-BR') : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.filename}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.period_name || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {item.processed_rows || 0}/{item.total_rows || 0}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        item.status === 'completed' 
                          ? 'bg-green-100 text-green-800' 
                          : item.status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {item.status === 'completed' ? '✓ Concluído' : item.status === 'failed' ? '✗ Erro' : item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.user || 'Sistema'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                    <p className="text-sm">Nenhum histórico de processamento disponível</p>
                    <p className="text-xs mt-1">Os uploads aparecerão aqui após serem processados</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
        </div>
      )}

      {/* Tab Content - Benefits */}
      {activeTab === 'benefits' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Upload Section */}
            <div className="lg:col-span-2 bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                <GiftIcon className="h-6 w-6 mr-2 text-green-600" />
                Upload de Benefícios iFood
              </h2>
              
              <div className="space-y-5">
                <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  Carregamento alvo: <strong>{xlsxCompany === '0060' ? 'Empreendimentos (0060)' : 'Infraestrutura (0059)'}</strong> em <strong>{String(xlsxMonth).padStart(2, '0')}/{xlsxYear}</strong>
                </div>

                {/* Company Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <BuildingOfficeIcon className="inline h-4 w-4 mr-1" />
                    Empresa
                  </label>
                  <select
                    value={xlsxCompany}
                    onChange={(e) => setXlsxCompany(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="0060">0060 - Empreendimentos</option>
                    <option value="0059">0059 - Infraestrutura</option>
                  </select>
                </div>

                {/* Month and Year Selection */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Mês
                    </label>
                    <select
                      value={xlsxMonth}
                      onChange={(e) => setXlsxMonth(parseInt(e.target.value))}
                      className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-green-500"
                    >
                      {[...Array(12)].map((_, i) => (
                        <option key={i + 1} value={i + 1}>
                          {new Date(2000, i).toLocaleDateString('pt-BR', { month: 'long' })}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Ano
                    </label>
                    <input
                      type="number"
                      value={xlsxYear}
                      onChange={(e) => setXlsxYear(parseInt(e.target.value))}
                      min="2020"
                      max="2035"
                      className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tipo de consolidação
                    </label>
                    <select
                      value={benefitsMergeMode}
                      onChange={(e) => setBenefitsMergeMode(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-green-500"
                    >
                      <option value="sum">Somar com o já carregado (complementar)</option>
                      <option value="replace">Substituir valores do mês/empresa</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Identificação do lote (opcional)
                    </label>
                    <input
                      type="text"
                      value={benefitsSourceLabel}
                      onChange={(e) => setBenefitsSourceLabel(e.target.value)}
                      placeholder="Ex: Complementar Abril - Loja A"
                      className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                </div>

                {/* File Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Arquivo CSV ou XLSX
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="file"
                      accept=".xlsx,.xlsm,.xltx,.xltm,.csv,.txt"
                      onChange={handleXlsxFileSelect}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
                    />
                    {xlsxFile && (
                      <button
                        onClick={() => {
                          setXlsxFile(null);
                          setXlsxResult(null);
                        }}
                        className="text-red-600 hover:text-red-800"
                      >
                        <XCircleIcon className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                  {xlsxFile && (
                    <p className="mt-2 text-sm text-green-600">
                      ✓ Arquivo selecionado: {xlsxFile.name} ({(xlsxFile.size / 1024).toFixed(2)} KB)
                    </p>
                  )}
                </div>

                {/* Upload Button */}
                <button
                  onClick={handleXlsxUpload}
                  disabled={!xlsxFile || xlsxUploading}
                  className={`w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg font-medium transition-all ${
                    !xlsxFile || xlsxUploading
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
                  }`}
                >
                  {xlsxUploading ? (
                    <>
                      <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Processando...</span>
                    </>
                  ) : (
                    <>
                      <DocumentArrowUpIcon className="h-5 w-5" />
                      <span>Processar Benefícios</span>
                    </>
                  )}
                </button>

                {/* Result Display */}
                {xlsxResult && (
                  <div className={`p-4 rounded-lg border ${
                    xlsxResult.success 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="flex items-start space-x-3">
                      {xlsxResult.success ? (
                        <CheckCircleIcon className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircleIcon className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <h4 className={`font-medium ${xlsxResult.success ? 'text-green-900' : 'text-red-900'}`}>
                          {xlsxResult.success ? 'Processamento Concluído!' : 'Erro no Processamento'}
                        </h4>
                        {xlsxResult.success && (
                          <div className="mt-2 text-sm text-green-800 space-y-1">
                            <p>• Total de linhas: {xlsxResult.total_rows}</p>
                            <p>• Processadas: {xlsxResult.processed_rows}</p>
                            <p>• Erros: {xlsxResult.error_rows || 0}</p>
                            {xlsxResult.period_name && (
                              <p>• Período: {xlsxResult.period_name}</p>
                            )}
                            <p>• Empresa: {xlsxResult.company === '0060' ? 'Empreendimentos (0060)' : 'Infraestrutura (0059)'}</p>
                            <p>• Match por CPF: {xlsxResult.matched_by_cpf || 0}</p>
                            <p>• Match por Nome: {xlsxResult.matched_by_name || 0}</p>
                          </div>
                        )}
                        {xlsxResult.error && (
                          <p className="mt-2 text-sm text-red-800">{xlsxResult.error}</p>
                        )}
                        {xlsxResult.warnings && xlsxResult.warnings.length > 0 && (
                          <div className="mt-3 p-2 bg-yellow-50 rounded text-xs text-yellow-800 max-h-40 overflow-y-auto">
                            <p className="font-medium mb-1">Avisos:</p>
                            {xlsxResult.warnings.map((warn, idx) => (
                              <p key={idx}>• {warn}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Benefits Periods List */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Períodos de Benefícios</h2>
              
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {benefitsPeriods.map((period) => (
                  <div key={period.id} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-gray-900 text-sm">{period.period_name}</h3>
                          {period.company_name && (
                            <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                              period.company === '0060' 
                                ? 'bg-blue-100 text-blue-800' 
                                : 'bg-purple-100 text-purple-800'
                            }`}>
                              {period.company_name}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {period.month}/{period.year} • {period.total_records || 0} registro(s)
                        </p>
                      </div>
                      <button
                        onClick={() => confirmDeleteBenefitsPeriod(period)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Deletar Período"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
                
                {benefitsPeriods.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <GiftIcon className="mx-auto h-12 w-12 text-gray-300" />
                    <p className="mt-2 text-sm">Nenhum período de benefícios encontrado</p>
                    <p className="text-xs">Faça upload de um XLSX para criar</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Benefits Processing History */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Histórico de Processamento</h2>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data/Hora</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Arquivo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Período</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Empresa</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Modo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Registros</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tempo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {benefitsProcessingHistory.length > 0 ? (
                    benefitsProcessingHistory.map((log, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {log.created_at ? new Date(log.created_at).toLocaleString('pt-BR') : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 truncate max-w-xs" title={log.filename}>
                          {log.filename || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {log.period_name || `${String(log.month).padStart(2, '0')}/${log.year}`}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {log.company_name || log.company || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {log.processing_summary?.merge_mode === 'replace' ? 'Substituir' : 'Somar'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {log.processed_rows || 0}/{log.total_rows || 0}
                          {log.error_rows > 0 && <span className="text-red-600 ml-1">({log.error_rows} erros)</span>}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            log.status === 'completed' 
                              ? 'bg-green-100 text-green-800' 
                              : log.status === 'failed'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {log.status === 'completed' ? '✓ Concluído' : log.status === 'failed' ? '✗ Erro' : log.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {log.processing_time ? `${parseFloat(log.processing_time).toFixed(2)}s` : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          <button
                            onClick={() => handleDeleteBenefitsUploadLog(log)}
                            disabled={deletingBenefitsLogId === log.id || !log.can_delete}
                            title={
                              log.can_delete
                                ? `Remover somente este upload (modo: ${log.delete_mode === 'rollback' ? 'reversão' : 'simples'})`
                                : (log.rollback_reason || 'Este upload não pode ser removido individualmente')
                            }
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border text-xs font-medium ${
                              log.can_delete
                                ? 'text-red-700 border-red-300 hover:bg-red-50'
                                : 'text-gray-400 border-gray-200 cursor-not-allowed'
                            }`}
                          >
                            <TrashIcon className="h-3.5 w-3.5" />
                            {deletingBenefitsLogId === log.id ? 'Removendo...' : 'Remover upload'}
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="9" className="px-4 py-8 text-center text-gray-500">
                        <p className="text-sm">Nenhum histórico de processamento disponível</p>
                        <p className="text-xs mt-1">Os uploads aparecerão aqui após serem processados</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab Content - Timecard */}
      {activeTab === 'timecard' && (
        <TimecardUpload />
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && periodToDelete && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div 
              className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
              onClick={() => !deleting && setShowDeleteModal(false)}
            ></div>

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                    <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Deletar Período
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Tem certeza que deseja deletar o período <strong className="text-gray-900">{periodToDelete.period_name}</strong>
                        {periodToDelete.company_name && (
                          <span className={`ml-2 inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                            periodToDelete.company === '0060' 
                              ? 'bg-blue-100 text-blue-800' 
                              : 'bg-purple-100 text-purple-800'
                          }`}>
                            {periodToDelete.company_name}
                          </span>
                        )}?
                      </p>
                      <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                        <p className="text-sm text-yellow-800">
                          <strong>⚠️ Atenção:</strong> Esta ação é irreversível e todos os dados de folha de pagamento deste período serão permanentemente removidos.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  disabled={deleting}
                  onClick={handleDeletePeriod}
                  className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white sm:ml-3 sm:w-auto sm:text-sm ${
                    deleting
                      ? 'bg-red-400 cursor-not-allowed'
                      : 'bg-red-600 hover:bg-red-700'
                  }`}
                >
                  {deleting ? 'Deletando...' : 'Deletar Período'}
                </button>
                <button
                  type="button"
                  disabled={deleting}
                  onClick={() => setShowDeleteModal(false)}
                  className={`mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm ${
                    deleting ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'
                  }`}
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PayrollDataProcessor;
