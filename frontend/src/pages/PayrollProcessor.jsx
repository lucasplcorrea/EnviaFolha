import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  DocumentArrowUpIcon, 
  CogIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';

const PayrollProcessor = () => {
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState(null);

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

    setProcessing(true);
    setProcessResult(null);

    try {
      const response = await api.post('/payrolls/process', {
        uploadedFile
      });

      setProcessResult(response.data);
      toast.success(`PDF processado! ${response.data.processed_count} holerites segmentados.`);
    } catch (error) {
      console.error('Erro no processamento:', error);
      toast.error(error.response?.data?.detail || 'Erro ao processar PDF');
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
                <li>Faça upload do PDF com todos os holerites do mês</li>
                <li>O sistema irá segmentar automaticamente por funcionário</li>
                <li>Cada holerite será protegido com senha (primeiros 4 dígitos do CPF)</li>
                <li>Os arquivos processados ficarão prontos para envio via WhatsApp</li>
              </ol>
            </div>
          </div>
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

          {/* Botão para ir para envio */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={goToSender}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
            >
              Ir para Envio de Holerites
              <ArrowRightIcon className="h-4 w-4 ml-2" />
            </button>
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