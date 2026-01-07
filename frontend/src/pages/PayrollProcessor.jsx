import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  DocumentArrowUpIcon, 
  CogIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ArrowRightIcon,
  FolderIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';

const PayrollProcessor = () => {
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState(null);
  const [availablePeriods, setAvailablePeriods] = useState([]);
  const [periodsExpanded, setPeriodsExpanded] = useState(false);
  
  // Novos campos para o novo formato
  const [payrollType, setPayrollType] = useState('11'); // Mensal por padrão
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

  // Carregar períodos disponíveis ao montar componente
  useEffect(() => {
    loadAvailablePeriods();
  }, []);

  const loadAvailablePeriods = async () => {
    try {
      const response = await api.get('/payrolls/periods');
      setAvailablePeriods(response.data.periods || []);
    } catch (error) {
      console.error('Erro ao carregar períodos:', error);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.includes('pdf')) {
      toast.error('Apenas arquivos PDF são aceitos');
      return;
    }

    if (file.size > 60 * 1024 * 1024) { // 60MB
      toast.error('Arquivo muito grande. Máximo 25MB');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadedFile(response.data);
      toast.success('PDF de holerites carregado com sucesso!');
    } catch (error) {
      console.error('Erro no upload:', error);
      toast.error('Erro ao fazer upload do arquivo');
    } finally {
      setUploading(false);
    }
  };

  const handleProcessPayrolls = async () => {
    if (!uploadedFile) {
      toast.error('Faça upload do PDF primeiro');
      return;
    }

    if (!payrollType || !month || !year) {
      toast.error('Selecione o tipo, mês e ano do holerite');
      return;
    }

    setProcessing(true);
    setProcessResult(null);

    try {
      const response = await api.post('/payrolls/process', {
        uploadedFile,
        payrollType,
        month: parseInt(month),
        year: parseInt(year)
      });

      console.log('📦 Resposta do processamento:', response.data);
      setProcessResult(response.data);
      toast.success(`PDF processado! ${response.data.processed_count} holerites segmentados.`);
    } catch (error) {
      console.error('Erro no processamento:', error);
      toast.error(error.response?.data?.detail || 'Erro ao processar PDF');
    } finally {
      setProcessing(false);
    }
  };

  const handleDownloadZip = async (periodType = null, periodMonth = null, periodYear = null) => {
    try {
      setProcessing(true);
      toast.loading('Gerando ZIP...');

      // Usar período fornecido ou usar seleção atual
      const type = periodType || payrollType;
      const m = periodMonth || parseInt(month);
      const y = periodYear || parseInt(year);

      const response = await api.post('/payrolls/export-batch', {
        payrollType: type,
        month: m,
        year: y
      }, {
        responseType: 'blob'
      });

      // Criar URL do blob e fazer download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Extrair nome do arquivo do header ou criar um padrão
      const contentDisposition = response.headers['content-disposition'];
      let filename = `Holerites_${type}_${String(m).padStart(2, '0')}_${y}.zip`;
      
      if (contentDisposition) {
        // Regex corrigido: captura apenas o nome sem aspas
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=["']?([^"';\n]+)["']?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].trim();
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.dismiss();
      toast.success('ZIP baixado com sucesso!');
    } catch (error) {
      console.error('Erro ao baixar ZIP:', error);
      toast.dismiss();
      toast.error('Erro ao gerar ZIP para download');
    } finally {
      setProcessing(false);
    }
  };

  const goToSender = () => {
    // Navegar para a tela de envio de holerites
    navigate('/payroll-sender');
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">Processamento de Holerites</h1>
      </div>
      {/* Períodos Disponíveis para Download - Compacto */}
      {availablePeriods.length > 0 && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <button
            onClick={() => setPeriodsExpanded(!periodsExpanded)}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center">
              <FolderIcon className="h-5 w-5 text-blue-500 mr-3" />
              <h2 className="text-lg font-medium text-gray-900">
                Períodos Processados ({availablePeriods.length})
              </h2>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  loadAvailablePeriods();
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                🔄 Atualizar
              </button>
              <svg
                className={`h-5 w-5 text-gray-400 transition-transform ${periodsExpanded ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          {periodsExpanded && (
            <div className="border-t border-gray-200 p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {availablePeriods.map((period, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 hover:shadow-sm transition-all">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium text-gray-900 truncate">{period.folder}</h3>
                    </div>
                    <p className="text-xs text-gray-500 mb-3">
                      {period.file_count} arquivo{period.file_count !== 1 ? 's' : ''}
                    </p>
                    <button
                      onClick={() => handleDownloadZip(period.payroll_type, period.month, period.year)}
                      disabled={processing}
                      className="w-full inline-flex items-center justify-center px-2 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ArrowDownTrayIcon className="h-3.5 w-3.5 mr-1" />
                      Baixar
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {/* Instruções */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <DocumentTextIcon className="h-5 w-5 text-blue-400" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              Como funciona o processamento
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <ol className="list-decimal list-inside space-y-1">
                <li>Selecione o tipo de holerite (Mensal, 13º, etc)</li>
                <li>Defina o mês e ano de competência</li>
                <li>Faça upload do PDF com todos os holerites do período</li>
                <li>O sistema segmentará e renomeará no formato: EN_MATRÍCULA_TIPO_MÊS_ANO.pdf</li>
                <li>Cada holerite será protegido com senha (primeiros 4 dígitos do CPF)</li>
                <li>Os arquivos serão organizados por tipo e período para exportação</li>
              </ol>
            </div>
          </div>
        </div>
      </div>

      {/* Configuração do Período */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          📅 Configuração do Período e Tipo
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Tipo de Holerite */}
          <div>
            <label htmlFor="payroll-type" className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de Holerite *
            </label>
            <select
              id="payroll-type"
              value={payrollType}
              onChange={(e) => setPayrollType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="11">11 - Mensal</option>
              <option value="31">31 - Adiantamento 13º</option>
              <option value="32">32 - 13º Integral</option>
              <option value="91">91 - Adiantamento Salarial</option>
            </select>
          </div>

          {/* Mês */}
          <div>
            <label htmlFor="month" className="block text-sm font-medium text-gray-700 mb-2">
              Mês de Competência *
            </label>
            <select
              id="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="1">Janeiro</option>
              <option value="2">Fevereiro</option>
              <option value="3">Março</option>
              <option value="4">Abril</option>
              <option value="5">Maio</option>
              <option value="6">Junho</option>
              <option value="7">Julho</option>
              <option value="8">Agosto</option>
              <option value="9">Setembro</option>
              <option value="10">Outubro</option>
              <option value="11">Novembro</option>
              <option value="12">Dezembro</option>
            </select>
          </div>

          {/* Ano */}
          <div>
            <label htmlFor="year" className="block text-sm font-medium text-gray-700 mb-2">
              Ano de Competência *
            </label>
            <input
              type="number"
              id="year"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              min="2020"
              max="2030"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Info sobre o formato */}
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-700">
            <strong>Formato de exportação:</strong> EN_MATRÍCULA_TIPO_MÊS_ANO.pdf
          </p>
          <p className="text-xs text-blue-600 mt-1">
            Exemplo: EN_6000169_{payrollType}_{String(month).padStart(2, '0')}_{year}.pdf
          </p>
        </div>
      </div>

      {/* Upload de PDF */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          📋 Upload do PDF de Holerites
        </h2>

        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
          <div className="text-center">
            <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
            <div className="mt-4">
              <label htmlFor="pdf-upload" className="cursor-pointer">
                <span className="mt-2 block text-sm font-medium text-gray-900">
                  Selecione o PDF com todos os holerites
                </span>
                <span className="mt-1 block text-sm text-gray-500">
                  Máximo 25MB • Apenas arquivos PDF
                </span>
              </label>
              <input
                id="pdf-upload"
                name="pdf-upload"
                type="file"
                accept=".pdf"
                className="sr-only"
                onChange={handleFileUpload}
                disabled={uploading}
              />
            </div>
          </div>
        </div>

        {uploading && (
          <div className="mt-4 text-center">
            <div className="inline-flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <span className="ml-2 text-sm text-gray-600">Fazendo upload...</span>
            </div>
          </div>
        )}

        {uploadedFile && (
          <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center">
              <CheckCircleIcon className="h-5 w-5 text-green-400" />
              <div className="ml-3">
                <h4 className="text-sm font-medium text-green-800">Arquivo carregado</h4>
                <p className="text-sm text-green-700">
                  {uploadedFile.original_name} ({(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Processamento */}
      {uploadedFile && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            ⚙️ Processamento e Segmentação
          </h2>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-2">
                Clique para processar o PDF e segmentar os holerites por funcionário
              </p>
              <p className="text-xs text-gray-500">
                Este processo pode levar alguns minutos dependendo do tamanho do arquivo
              </p>
            </div>
            <button
              onClick={handleProcessPayrolls}
              disabled={processing}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {processing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Processando...
                </>
              ) : (
                <>
                  <CogIcon className="h-4 w-4 mr-2" />
                  Processar Holerites
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Resultado do processamento */}
      {processResult && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            ✅ Resultado do Processamento
          </h2>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
            <div className="flex items-center">
              <CheckCircleIcon className="h-5 w-5 text-green-400" />
              <div className="ml-3">
                <h4 className="text-sm font-medium text-green-800">
                  Processamento concluído com sucesso!
                </h4>
                <p className="text-sm text-green-700">
                  {processResult.processed_count} holerites foram segmentados e estão prontos para envio
                </p>
              </div>
            </div>
          </div>

          {/* Lista de arquivos processados */}
          {processResult.files && processResult.files.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-900">Arquivos processados:</h3>
              <div className="max-h-40 overflow-y-auto">
                {processResult.files.map((file, index) => (
                  <div key={index} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-md">
                    <div className="flex items-center">
                      <DocumentTextIcon className="h-4 w-4 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-900">{file.filename}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-500">ID: {file.unique_id}</span>
                      {file.password_protected && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          🔒 Protegido
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Botões de ação */}
          <div className="mt-6 flex justify-between items-center">
            <div className="text-sm text-gray-600">
              📁 Pasta: <span className="font-medium">{processResult.export_info?.folder || 'N/A'}</span>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleDownloadZip}
                disabled={processing}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                📦 Baixar ZIP ({processResult.processed_count} arquivos)
              </button>
              <button
                onClick={goToSender}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
              >
                Ir para Envio de Holerites
                <ArrowRightIcon className="h-4 w-4 ml-2" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Informações adicionais */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">
              Importante
            </h3>
            <div className="mt-2 text-sm text-yellow-700">
              <ul className="list-disc list-inside space-y-1">
                <li>Certifique-se de que o PDF contém todos os holerites do período</li>
                <li>O sistema busca automaticamente pelo CPF para gerar as senhas</li>
                <li>Funcionários sem CPF identificável não terão senha no PDF</li>
                <li>Após o processamento, você pode selecionar quais funcionários receberão os holerites</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PayrollProcessor;