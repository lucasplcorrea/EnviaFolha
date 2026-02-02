import React, { useState, useEffect } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  GiftIcon,
  BuildingOfficeIcon,
  DocumentArrowUpIcon,
  CalendarIcon,
  TrashIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

const BenefitsUpload = () => {
  const [benefitsPeriods, setBenefitsPeriods] = useState([]);
  const [xlsxFile, setXlsxFile] = useState(null);
  const [xlsxYear, setXlsxYear] = useState(new Date().getFullYear());
  const [xlsxMonth, setXlsxMonth] = useState(new Date().getMonth() + 1);
  const [xlsxCompany, setXlsxCompany] = useState('0060');
  const [xlsxUploading, setXlsxUploading] = useState(false);
  const [xlsxResult, setXlsxResult] = useState(null);
  
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [periodToDelete, setPeriodToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadBenefitsPeriods();
  }, []);

  const loadBenefitsPeriods = async () => {
    try {
      const response = await api.get('/benefits/periods');
      setBenefitsPeriods(response.data.periods || []);
    } catch (error) {
      console.error('Erro ao carregar períodos de benefícios:', error);
      toast.error('Erro ao carregar períodos');
    }
  };

  const handleXlsxFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.XLSX')) {
      toast.error('Por favor, selecione apenas arquivos XLSX');
      return;
    }

    setXlsxFile(file);
    setXlsxResult(null);
  };

  const handleXlsxUpload = async () => {
    if (!xlsxFile) {
      toast.error('Selecione um arquivo XLSX');
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
        setXlsxFile(null);
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

  const confirmDeletePeriod = (period) => {
    setPeriodToDelete(period);
    setShowDeleteModal(true);
  };

  const handleDeletePeriod = async () => {
    if (!periodToDelete) return;

    setDeleting(true);
    try {
      const response = await api.delete(`/benefits/periods/${periodToDelete.id}`);
      
      if (response.data.success) {
        toast.success(`Período "${periodToDelete.period_name}" deletado com sucesso!`);
        setShowDeleteModal(false);
        setPeriodToDelete(null);
        loadBenefitsPeriods();
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center">
          <GiftIcon className="h-8 w-8 mr-3 text-green-600" />
          Benefícios iFood
        </h1>
        <p className="text-gray-600 mt-1">
          Upload e gerenciamento de benefícios (Vale Refeição, Alimentação, Mobilidade e Livre)
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Section */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
            <DocumentArrowUpIcon className="h-6 w-6 mr-2 text-green-600" />
            Upload de Arquivo XLSX
          </h2>
          
          <div className="space-y-5">
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
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-green-500"
                  min="2020"
                  max="2030"
                />
              </div>
            </div>

            {/* File Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Arquivo XLSX
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-green-500 transition-colors">
                <input
                  type="file"
                  onChange={handleXlsxFileSelect}
                  accept=".xlsx"
                  className="hidden"
                  id="xlsx-file-input"
                />
                <label htmlFor="xlsx-file-input" className="cursor-pointer">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    {xlsxFile ? xlsxFile.name : 'Clique para selecionar um arquivo XLSX'}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    Colunas: CPF, Refeicao, Alimentacao, Mobilidade, Livre
                  </p>
                </label>
              </div>
            </div>

            {/* Upload Button */}
            <button
              onClick={handleXlsxUpload}
              disabled={!xlsxFile || xlsxUploading}
              className="w-full flex items-center justify-center px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {xlsxUploading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processando...
                </>
              ) : (
                <>
                  <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                  Processar Benefícios
                </>
              )}
            </button>

            {/* Upload Result */}
            {xlsxResult && (
              <div className={`mt-4 p-4 rounded-lg border ${
                xlsxResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-start">
                  {xlsxResult.success ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-600 mr-3 flex-shrink-0" />
                  ) : (
                    <ExclamationTriangleIcon className="h-5 w-5 text-red-600 mr-3 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <h4 className={`font-semibold ${
                      xlsxResult.success ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {xlsxResult.success ? 'Processamento concluído!' : 'Erro no processamento'}
                    </h4>
                    
                    {xlsxResult.success && (
                      <div className="mt-2 text-sm text-green-800 space-y-1">
                        <p>• Período: {xlsxResult.period_name}</p>
                        <p>• Total de linhas: {xlsxResult.total_rows}</p>
                        <p>• Processadas: {xlsxResult.processed_rows}</p>
                        {xlsxResult.error_rows > 0 && (
                          <p className="text-red-600">• Erros: {xlsxResult.error_rows}</p>
                        )}
                        <p>• Tempo: {xlsxResult.processing_time?.toFixed(2)}s</p>
                      </div>
                    )}
                    
                    {xlsxResult.warnings && xlsxResult.warnings.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium text-yellow-800">Avisos:</p>
                        <ul className="mt-1 text-xs text-yellow-700 space-y-1 max-h-32 overflow-y-auto">
                          {xlsxResult.warnings.map((warning, idx) => (
                            <li key={idx}>• {warning}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {xlsxResult.errors && xlsxResult.errors.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium text-red-800">Erros:</p>
                        <ul className="mt-1 text-xs text-red-700 space-y-1 max-h-32 overflow-y-auto">
                          {xlsxResult.errors.map((error, idx) => (
                            <li key={idx}>• {error}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {xlsxResult.error && !xlsxResult.errors && (
                      <p className="mt-2 text-sm text-red-800">{xlsxResult.error}</p>
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
            {benefitsPeriods.map((period) => (
              <div key={period.id} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900 text-sm">{period.period_name}</h3>
                      <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                        period.company === '0060' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {period.company_name}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {period.total_records} registro(s)
                    </p>
                  </div>
                  <button
                    onClick={() => confirmDeletePeriod(period)}
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
                <CalendarIcon className="mx-auto h-12 w-12 text-gray-300" />
                <p className="mt-2 text-sm">Nenhum período encontrado</p>
                <p className="text-xs">Faça upload de um XLSX para criar</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                <TrashIcon className="h-6 w-6 text-red-600" />
              </div>
              <h3 className="text-lg leading-6 font-medium text-gray-900 mt-4">
                Deletar Período de Benefícios
              </h3>
              <div className="mt-2 px-7 py-3">
                <p className="text-sm text-gray-500">
                  Tem certeza que deseja deletar o período <strong>{periodToDelete?.period_name}</strong>?
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  Todos os registros de benefícios deste período serão permanentemente removidos.
                </p>
              </div>
              <div className="flex gap-3 px-4 py-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  disabled={deleting}
                  className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeletePeriod}
                  disabled={deleting}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center justify-center"
                >
                  {deleting ? (
                    <>
                      <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Deletando...
                    </>
                  ) : (
                    'Deletar'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BenefitsUpload;
