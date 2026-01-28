import React, { useState, useEffect } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  DocumentArrowUpIcon,
  FolderOpenIcon,
  PlusIcon,
  ChartBarIcon,
  CogIcon,
  CalendarIcon,
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  TrashIcon
} from '@heroicons/react/24/outline';

const PayrollDataProcessor = () => {
  const [periods, setPeriods] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showCreatePeriod, setShowCreatePeriod] = useState(false);
  const [showCreateTemplate, setShowCreateTemplate] = useState(false);
  const [processingLogs, setProcessingLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('excel'); // 'excel' ou 'csv'
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [periodToDelete, setPeriodToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  
  // Estados para Upload CSV
  const [csvFile, setCsvFile] = useState(null);
  const [csvDivision, setCsvDivision] = useState('0060');
  const [csvAutoCreate, setCsvAutoCreate] = useState(true);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvResult, setCsvResult] = useState(null);
  
  const [newPeriod, setNewPeriod] = useState({
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    period_name: '',
    description: ''
  });

  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
    column_mapping: {
      employee_identifier: '',
      earnings: [],
      deductions: [],
      benefits: []
    },
    skip_rows: 0,
    header_row: 1,
    is_default: false
  });

  useEffect(() => {
    loadPeriods();
    loadTemplates();
    loadProcessingLogs();
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

  const loadTemplates = async () => {
    try {
      const response = await api.get('/payroll/templates');
      setTemplates(response.data.templates || []);
    } catch (error) {
      toast.error('Erro ao carregar templates');
      console.error('Erro ao carregar templates:', error);
    }
  };

  const loadProcessingLogs = async () => {
    // TODO: Implementar endpoint para logs de processamento
    setProcessingLogs([]);
  };

  const confirmDeletePeriod = (period) => {
    setPeriodToDelete(period);
    setShowDeleteModal(true);
  };

  const handleDeletePeriod = async () => {
    if (!periodToDelete) return;

    setDeleting(true);
    try {
      const response = await api.delete(`/payroll/periods/${periodToDelete.id}`);
      
      if (response.data.success) {
        toast.success(`Período "${periodToDelete.period_name}" deletado com sucesso!`);
        setShowDeleteModal(false);
        setPeriodToDelete(null);
        loadPeriods();
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

  const handleCreatePeriod = async (e) => {
    e.preventDefault();
    
    try {
      const response = await api.post('/payroll/periods', newPeriod);
      
      if (response.data.success) {
        toast.success('Período criado com sucesso!');
        setShowCreatePeriod(false);
        setNewPeriod({
          year: new Date().getFullYear(),
          month: new Date().getMonth() + 1,
          period_name: '',
          description: ''
        });
        loadPeriods();
      } else {
        toast.error(response.data.message || 'Erro ao criar período');
      }
    } catch (error) {
      toast.error(error.response?.data?.message || 'Erro ao criar período');
    }
  };

  const handleCreateTemplate = async (e) => {
    e.preventDefault();
    
    try {
      const response = await api.post('/payroll/templates', newTemplate);
      
      if (response.data.success) {
        toast.success('Template criado com sucesso!');
        setShowCreateTemplate(false);
        setNewTemplate({
          name: '',
          description: '',
          column_mapping: {
            employee_identifier: '',
            earnings: [],
            deductions: [],
            benefits: []
          },
          skip_rows: 0,
          header_row: 1,
          is_default: false
        });
        loadTemplates();
      } else {
        toast.error(response.data.message || 'Erro ao criar template');
      }
    } catch (error) {
      toast.error(error.response?.data?.message || 'Erro ao criar template');
    }
  };

  const handleFileUpload = async () => {
    if (!file || !selectedPeriod) {
      toast.error('Selecione um arquivo e um período');
      return;
    }

    setLoading(true);
    
    try {
      // TODO: Implementar upload de arquivo
      toast.success('Funcionalidade de upload será implementada em breve');
    } catch (error) {
      toast.error('Erro ao processar arquivo');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'processing':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      case 'partial':
        return <ExclamationTriangleIcon className="h-5 w-5 text-orange-500" />;
      default:
        return <DocumentTextIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const handleCsvFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv') && !file.name.endsWith('.CSV')) {
      toast.error('Por favor, selecione um arquivo CSV');
      return;
    }

    setCsvFile(file);
    setCsvResult(null);
  };

  const handleCsvUpload = async () => {
    if (!csvFile) {
      toast.error('Selecione um arquivo CSV primeiro');
      return;
    }

    setCsvUploading(true);
    setCsvResult(null);

    try {
      // 1. Upload do arquivo
      const formData = new FormData();
      formData.append('file', csvFile);

      const uploadResponse = await api.post('/uploads/csv', formData, {
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
      });

      const result = processResponse.data;
      setCsvResult(result);

      if (result.success) {
        const stats = result.stats;
        toast.success(
          `✅ Processado! ${stats.processed}/${stats.total_rows} linhas, ${stats.new_employees} novos funcionários`
        );
        loadPeriods(); // Recarregar períodos
      } else {
        toast.error(`❌ Erro: ${result.error}`);
      }
    } catch (error) {
      console.error('Erro no upload CSV:', error);
      toast.error(error.response?.data?.error || 'Erro ao processar CSV');
      setCsvResult({
        success: false,
        error: error.response?.data?.error || error.message,
      });
    } finally {
      setCsvUploading(false);
    }
  };

  const clearCsvFile = () => {
    setCsvFile(null);
    setCsvResult(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <FolderOpenIcon className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Processamento de Dados</h1>
            <p className="text-gray-600">Importe e processe planilhas de folha de pagamento</p>
          </div>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowCreateTemplate(true)}
            className="flex items-center space-x-2 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <CogIcon className="h-5 w-5" />
            <span>Novo Template</span>
          </button>
          <button
            onClick={() => setShowCreatePeriod(true)}
            className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
            <span>Novo Período</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('excel')}
              className={`py-4 px-6 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'excel'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <DocumentTextIcon className="h-5 w-5" />
                <span>Upload Excel (Tradicional)</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('csv')}
              className={`py-4 px-6 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'csv'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <DocumentArrowUpIcon className="h-5 w-5" />
                <span>Upload CSV (Analíticos)</span>
              </div>
            </button>
          </nav>
        </div>
      </div>

      {/* Conteúdo baseado na aba ativa */}
      {activeTab === 'excel' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Section */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Upload de Planilha</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Período</label>
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Selecione um período</option>
                {periods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {period.period_name} ({period.year})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Template (Opcional)</label>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Detecção automática</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Arquivo Excel</label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
                <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                <div className="mt-4">
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <span className="mt-2 block text-sm font-medium text-gray-900">
                      Clique para selecionar um arquivo
                    </span>
                    <span className="mt-1 block text-xs text-gray-500">
                      ou arraste e solte aqui
                    </span>
                  </label>
                  <input
                    id="file-upload"
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="hidden"
                  />
                </div>
                {file && (
                  <div className="mt-2 text-sm text-gray-600">
                    Arquivo selecionado: {file.name}
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={handleFileUpload}
              disabled={loading || !file || !selectedPeriod}
              className="w-full flex items-center justify-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <ClockIcon className="h-5 w-5 animate-spin" />
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <DocumentArrowUpIcon className="h-5 w-5" />
                  <span>Processar Planilha</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Periods List */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Períodos Disponíveis</h2>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {periods.map((period) => (
              <div key={period.id} className="border rounded-lg p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium text-gray-900">{period.period_name}</h3>
                    <p className="text-sm text-gray-500">{period.description}</p>
                    <p className="text-xs text-gray-400">
                      {period.month}/{period.year}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {period.is_closed && (
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                        Fechado
                      </span>
                    )}
                    <button
                      className="text-blue-600 hover:text-blue-900"
                      title="Ver Resumo"
                    >
                      <ChartBarIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => confirmDeletePeriod(period)}
                      className="text-red-600 hover:text-red-900 transition-colors"
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
                <p className="mt-2">Nenhum período criado</p>
                <p className="text-sm">Crie um período para começar</p>
              </div>
            )}
          </div>
        </div>

        {/* Processing Logs */}
        <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Histórico de Processamento</h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Arquivo
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Período
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Processado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processingLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-300" />
                    <p className="mt-2">Nenhum processamento realizado</p>
                  </td>
                </tr>
              ) : (
                processingLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {getStatusIcon(log.status)}
                        <span className="ml-2 text-sm capitalize">{log.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.filename}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.period_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.processed_rows}/{log.total_rows}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(log.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      </div>
      ) : (
        // Aba CSV (Analíticos)
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Instruções */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
              <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600" />
              Instruções - CSV Analíticos
            </h3>
            <div className="space-y-3 text-sm text-gray-600">
              <div>
                <p className="font-medium text-gray-900">1. Formato do Arquivo</p>
                <p>CSV com separador ponto-e-vírgula (;)</p>
                <p>Encoding: Latin-1, UTF-8 ou CP1252</p>
              </div>
              <div>
                <p className="font-medium text-gray-900">2. Colunas Necessárias</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Código Funcionário</li>
                  <li>Nome Colaborador</li>
                  <li>Data Admissão</li>
                </ul>
              </div>
              <div>
                <p className="font-medium text-gray-900">3. Tipos Suportados</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Mensal (padrão)</li>
                  <li>13º Salário</li>
                  <li>Complementar</li>
                  <li>Adiantamento</li>
                </ul>
              </div>
              <div>
                <p className="font-medium text-gray-900">4. Auto-detecção</p>
                <p>O período é criado automaticamente a partir do nome do arquivo (ex: 01-2024.CSV = Janeiro 2024)</p>
              </div>
            </div>
          </div>

          {/* Formulário de Upload CSV */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Configurações</h3>

              <div className="space-y-4">
                {/* Divisão */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Divisão
                  </label>
                  <select
                    value={csvDivision}
                    onChange={(e) => setCsvDivision(e.target.value)}
                    disabled={csvUploading}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="0060">0060 - Empreendimentos</option>
                    <option value="0059">0059 - Infraestrutura</option>
                  </select>
                </div>

                {/* Auto-criar funcionários */}
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="autoCreate"
                    checked={csvAutoCreate}
                    onChange={(e) => setCsvAutoCreate(e.target.checked)}
                    disabled={csvUploading}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="autoCreate" className="ml-2 block text-sm text-gray-700">
                    Criar funcionários automaticamente se não existirem
                  </label>
                </div>
              </div>
            </div>

            {/* Upload de Arquivo CSV */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Selecionar Arquivo CSV
              </h3>

              {!csvFile ? (
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <div className="flex justify-center">
                    <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                      <span>Clique para selecionar um arquivo CSV</span>
                      <input
                        type="file"
                        accept=".csv,.CSV"
                        onChange={handleCsvFileSelect}
                        className="sr-only"
                      />
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">Apenas arquivos CSV</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center">
                      <DocumentArrowUpIcon className="h-8 w-8 text-blue-500 mr-3" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{csvFile.name}</p>
                        <p className="text-xs text-gray-500">
                          {(csvFile.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={clearCsvFile}
                      disabled={csvUploading}
                      className="text-sm text-red-600 hover:text-red-800 disabled:text-gray-400"
                    >
                      Remover
                    </button>
                  </div>

                  <div className="flex justify-end space-x-3">
                    <button
                      onClick={clearCsvFile}
                      disabled={csvUploading}
                      className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={handleCsvUpload}
                      disabled={csvUploading}
                      className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 flex items-center"
                    >
                      {csvUploading ? (
                        <>
                          <ClockIcon className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" />
                          Processando...
                        </>
                      ) : (
                        <>
                          <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                          Processar CSV
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Resultado */}
            {csvResult && (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center mb-4">
                  {csvResult.success ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-500 mr-2" />
                  ) : (
                    <XCircleIcon className="h-6 w-6 text-red-500 mr-2" />
                  )}
                  <h3 className={`text-lg font-medium ${csvResult.success ? 'text-green-900' : 'text-red-900'}`}>
                    {csvResult.success ? 'Processamento Concluído' : 'Erro no Processamento'}
                  </h3>
                </div>

                {csvResult.success ? (
                  <div className="space-y-4">
                    {/* Informações do Período */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <p className="text-sm font-medium text-blue-900">
                        Período: {csvResult.period_name}
                      </p>
                      <p className="text-xs text-blue-700 mt-1">
                        Tipo: {csvResult.file_type} | Divisão: {csvResult.division}
                      </p>
                    </div>

                    {/* Estatísticas */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-2xl font-bold text-gray-900">{csvResult.stats.total_rows}</p>
                        <p className="text-xs text-gray-600">Total</p>
                      </div>
                      <div className="bg-green-50 rounded-lg p-3">
                        <p className="text-2xl font-bold text-green-700">{csvResult.stats.processed}</p>
                        <p className="text-xs text-green-600">Processadas</p>
                      </div>
                      <div className="bg-blue-50 rounded-lg p-3">
                        <p className="text-2xl font-bold text-blue-700">{csvResult.stats.new_employees}</p>
                        <p className="text-xs text-blue-600">Novos</p>
                      </div>
                      <div className="bg-red-50 rounded-lg p-3">
                        <p className="text-2xl font-bold text-red-700">{csvResult.stats.errors}</p>
                        <p className="text-xs text-red-600">Erros</p>
                      </div>
                    </div>

                    <p className="text-xs text-gray-500">
                      Processado em {csvResult.processing_time_seconds?.toFixed(2) || '0.00'}s
                    </p>

                    {/* Erros */}
                    {csvResult.errors && csvResult.errors.length > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-h-40 overflow-y-auto">
                        <p className="text-sm font-medium text-red-900 mb-2">
                          Erros ({csvResult.errors.length}):
                        </p>
                        {csvResult.errors.slice(0, 10).map((error, index) => (
                          <p key={index} className="text-xs text-red-700">
                            Linha {error.row}: {error.error}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-700">{csvResult.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Period Modal */}
      {showCreatePeriod && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Criar Novo Período</h3>
              
              <form onSubmit={handleCreatePeriod} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Ano</label>
                    <input
                      type="number"
                      value={newPeriod.year}
                      onChange={(e) => setNewPeriod({...newPeriod, year: parseInt(e.target.value)})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Mês</label>
                    <select
                      value={newPeriod.month}
                      onChange={(e) => setNewPeriod({...newPeriod, month: parseInt(e.target.value)})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      {Array.from({length: 12}, (_, i) => (
                        <option key={i + 1} value={i + 1}>
                          {new Date(2024, i).toLocaleDateString('pt-BR', { month: 'long' })}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nome do Período</label>
                  <input
                    type="text"
                    value={newPeriod.period_name}
                    onChange={(e) => setNewPeriod({...newPeriod, period_name: e.target.value})}
                    placeholder="Ex: Janeiro 2024, 13º Salário 2024"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Descrição</label>
                  <textarea
                    value={newPeriod.description}
                    onChange={(e) => setNewPeriod({...newPeriod, description: e.target.value})}
                    rows={3}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowCreatePeriod(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Criar Período
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Create Template Modal */}
      {showCreateTemplate && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-4/5 max-w-4xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Criar Novo Template</h3>
              
              <form onSubmit={handleCreateTemplate} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Nome do Template</label>
                    <input
                      type="text"
                      value={newTemplate.name}
                      onChange={(e) => setNewTemplate({...newTemplate, name: e.target.value})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Coluna de Identificação</label>
                    <input
                      type="text"
                      value={newTemplate.column_mapping.employee_identifier}
                      onChange={(e) => setNewTemplate({
                        ...newTemplate, 
                        column_mapping: {
                          ...newTemplate.column_mapping,
                          employee_identifier: e.target.value
                        }
                      })}
                      placeholder="Ex: CPF, Matrícula"
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Descrição</label>
                  <textarea
                    value={newTemplate.description}
                    onChange={(e) => setNewTemplate({...newTemplate, description: e.target.value})}
                    rows={2}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Proventos</label>
                    <textarea
                      placeholder="Salário Base&#10;Horas Extras&#10;Adicional Noturno"
                      onChange={(e) => setNewTemplate({
                        ...newTemplate,
                        column_mapping: {
                          ...newTemplate.column_mapping,
                          earnings: e.target.value.split('\n').filter(line => line.trim())
                        }
                      })}
                      rows={4}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Um por linha</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Descontos</label>
                    <textarea
                      placeholder="INSS&#10;IRRF&#10;Vale Transporte"
                      onChange={(e) => setNewTemplate({
                        ...newTemplate,
                        column_mapping: {
                          ...newTemplate.column_mapping,
                          deductions: e.target.value.split('\n').filter(line => line.trim())
                        }
                      })}
                      rows={4}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Um por linha</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Benefícios</label>
                    <textarea
                      placeholder="Vale Alimentação&#10;Plano de Saúde&#10;Auxílio Creche"
                      onChange={(e) => setNewTemplate({
                        ...newTemplate,
                        column_mapping: {
                          ...newTemplate.column_mapping,
                          benefits: e.target.value.split('\n').filter(line => line.trim())
                        }
                      })}
                      rows={4}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Um por linha</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Pular Linhas</label>
                    <input
                      type="number"
                      value={newTemplate.skip_rows}
                      onChange={(e) => setNewTemplate({...newTemplate, skip_rows: parseInt(e.target.value)})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Linha do Cabeçalho</label>
                    <input
                      type="number"
                      value={newTemplate.header_row}
                      onChange={(e) => setNewTemplate({...newTemplate, header_row: parseInt(e.target.value)})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="flex items-center mt-6">
                    <input
                      type="checkbox"
                      id="is_default"
                      checked={newTemplate.is_default}
                      onChange={(e) => setNewTemplate({...newTemplate, is_default: e.target.checked})}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="is_default" className="ml-2 block text-sm text-gray-900">
                      Template Padrão
                    </label>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowCreateTemplate(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Criar Template
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Confirmação de Deleção */}
      {showDeleteModal && periodToDelete && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div 
              className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
              onClick={() => !deleting && setShowDeleteModal(false)}
            ></div>

            {/* Modal panel */}
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
                        Tem certeza que deseja deletar o período <strong className="text-gray-900">{periodToDelete.period_name}</strong>?
                      </p>
                      <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                        <p className="text-sm text-yellow-800">
                          <strong>⚠️ Atenção:</strong> Esta ação é irreversível e todos os dados de folha de pagamento deste período serão permanentemente removidos.
                        </p>
                      </div>
                      <div className="mt-3 text-xs text-gray-500">
                        <p>Período: {periodToDelete.month}/{periodToDelete.year}</p>
                        {periodToDelete.description && <p>Descrição: {periodToDelete.description}</p>}
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
                      : 'bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500'
                  }`}
                >
                  {deleting ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Deletando...
                    </>
                  ) : (
                    'Deletar Período'
                  )}
                </button>
                <button
                  type="button"
                  disabled={deleting}
                  onClick={() => setShowDeleteModal(false)}
                  className={`mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm ${
                    deleting
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
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