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
  XCircleIcon
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
    </div>
  );
};

export default PayrollDataProcessor;