import React, { useState } from 'react';
import { DocumentArrowUpIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const DataImport = () => {
  const { config } = useTheme();
  const navigate = useNavigate();
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showProgressModal, setShowProgressModal] = useState(false);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls') && !file.name.endsWith('.csv')) {
      toast.error('Por favor, selecione um arquivo CSV ou Excel (.xlsx, .xls)');
      return;
    }

    setSelectedFile(file);
    setImportResult(null);
  };

  const handleImport = async () => {
    if (!selectedFile) {
      toast.error('Selecione um arquivo primeiro');
      return;
    }

    setImporting(true);
    setShowProgressModal(true);
    setImportResult(null);
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await api.post('/import/employees', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const result = response.data;
      setImportResult(result);
      
      if (result.success) {
        const created = result.imported_count || 0;
        const updated = result.updated_count || 0;
        const total = created + updated;
        
        // Show detailed success message
        if (created > 0 && updated > 0) {
          toast.success(`✅ Importação concluída! ${created} criados, ${updated} atualizados`);
        } else if (created > 0) {
          toast.success(`✅ ${created} funcionários criados com sucesso!`);
        } else if (updated > 0) {
          toast.success(`✅ ${updated} funcionários atualizados com sucesso!`);
        } else {
          toast.success('✅ Importação concluída!');
        }
        
        // Close progress modal after showing result
        setTimeout(() => {
          setShowProgressModal(false);
        }, 1500);
        
      } else {
        toast.error('Erro na importação. Verifique os detalhes abaixo.');
        setShowProgressModal(false);
      }

    } catch (error) {
      console.error('Erro na importação:', error);
      toast.error(error.response?.data?.detail || 'Erro ao importar arquivo');
      setImportResult({
        success: false,
        error: error.response?.data?.detail || 'Erro desconhecido'
      });
      setShowProgressModal(false);
    } finally {
      setImporting(false);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setImportResult(null);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className={`text-2xl font-semibold ${config.classes.text}`}>
          Importação de Dados
        </h1>
        <p className={`mt-2 text-sm ${config.classes.textSecondary}`}>
          Importe funcionários e dados de RH em massa através de arquivos CSV ou Excel
        </p>
      </div>

      {/* Card de Instruções */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 mb-6 ${config.classes.border}`}>
        <div className="flex items-start">
          <InformationCircleIcon className="h-6 w-6 text-blue-500 mr-3 flex-shrink-0 mt-1" />
          <div>
            <h3 className={`text-lg font-medium ${config.classes.text} mb-2`}>
              Formato do Arquivo
            </h3>
            <p className={`text-sm ${config.classes.textSecondary} mb-3`}>
              O arquivo deve conter as seguintes colunas (em qualquer ordem):
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <h4 className="font-medium text-gray-900 mb-1">Campos Obrigatórios:</h4>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  <li><code className="bg-gray-100 px-1 rounded">unique_id</code> - ID único do funcionário</li>
                  <li><code className="bg-gray-100 px-1 rounded">name</code> ou <code className="bg-gray-100 px-1 rounded">full_name</code> - Nome completo</li>
                  <li><code className="bg-gray-100 px-1 rounded">cpf</code> - CPF (11 dígitos)</li>
                  <li><code className="bg-gray-100 px-1 rounded">phone</code> ou <code className="bg-gray-100 px-1 rounded">phone_number</code> - Telefone</li>
                </ul>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-1">Campos Opcionais:</h4>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  <li><code className="bg-gray-100 px-1 rounded">email</code> - Email</li>
                  <li><code className="bg-gray-100 px-1 rounded">department</code> - Departamento</li>
                  <li><code className="bg-gray-100 px-1 rounded">position</code> - Cargo</li>
                  <li><code className="bg-gray-100 px-1 rounded">birth_date</code> - Data de nascimento (YYYY-MM-DD)</li>
                  <li><code className="bg-gray-100 px-1 rounded">sex</code> - Sexo (M/F)</li>
                  <li><code className="bg-gray-100 px-1 rounded">marital_status</code> - Estado civil</li>
                  <li><code className="bg-gray-100 px-1 rounded">admission_date</code> - Data de admissão (YYYY-MM-DD)</li>
                  <li><code className="bg-gray-100 px-1 rounded">contract_type</code> - Tipo de contrato</li>
                </ul>
              </div>
            </div>

            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800">
                <strong>Importante:</strong> O sistema vai atualizar funcionários existentes (baseado no unique_id) 
                ou criar novos registros automaticamente.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Card de Upload */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>
          Selecionar Arquivo
        </h3>

        {!selectedFile ? (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <div className="flex justify-center">
              <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500">
                <span>Clique para selecionar um arquivo</span>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileSelect}
                  className="sr-only"
                />
              </label>
            </div>
            <p className="text-xs text-gray-500 mt-2">CSV, XLS ou XLSX até 10MB</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                <DocumentArrowUpIcon className="h-8 w-8 text-blue-500 mr-3" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-xs text-gray-500">
                    {(selectedFile.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <button
                onClick={clearFile}
                disabled={importing}
                className="text-sm text-red-600 hover:text-red-800 disabled:text-gray-400"
              >
                Remover
              </button>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={clearFile}
                disabled={importing}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleImport}
                disabled={importing}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {importing ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Importando...
                  </>
                ) : (
                  <>
                    <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                    Importar Arquivo
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Resultado da Importação */}
      {importResult && (
        <div className={`mt-6 ${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
          <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>
            Resultado da Importação
          </h3>
          
          {importResult.success ? (
            <div className="space-y-4">
              <div className="flex items-center text-green-600">
                <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">Importação concluída com sucesso!</span>
              </div>
              
              {/* Summary Statistics */}
              <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-4 border border-green-200">
                <p className="text-sm text-gray-600 mb-3">Resumo da Importação</p>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-3xl font-bold text-green-600">{importResult.imported_count || 0}</p>
                    <p className="text-xs text-gray-600 mt-1">Criados</p>
                  </div>
                  <div className="text-center">
                    <p className="text-3xl font-bold text-blue-600">{importResult.updated_count || 0}</p>
                    <p className="text-xs text-gray-600 mt-1">Atualizados</p>
                  </div>
                  <div className="text-center">
                    <p className="text-3xl font-bold text-purple-600">{(importResult.imported_count || 0) + (importResult.updated_count || 0)}</p>
                    <p className="text-xs text-gray-600 mt-1">Total</p>
                  </div>
                </div>
              </div>
              
              {/* Details Lists */}
              <div className="grid grid-cols-2 gap-4">
                {/* Created Employees */}
                {importResult.created_list && importResult.created_list.length > 0 && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm font-medium text-green-800 mb-2">
                      ✨ Colaboradores Criados ({importResult.created_list.length})
                    </p>
                    <div className="max-h-32 overflow-y-auto">
                      <ul className="text-xs text-green-700 space-y-1">
                        {importResult.created_list.slice(0, 10).map((name, index) => (
                          <li key={index}>• {name}</li>
                        ))}
                        {importResult.created_list.length > 10 && (
                          <li className="text-green-600 italic">... e mais {importResult.created_list.length - 10}</li>
                        )}
                      </ul>
                    </div>
                  </div>
                )}
                
                {/* Updated Employees */}
                {importResult.updated_list && importResult.updated_list.length > 0 && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm font-medium text-blue-800 mb-2">
                      🔄 Colaboradores Atualizados ({importResult.updated_list.length})
                    </p>
                    <div className="max-h-32 overflow-y-auto">
                      <ul className="text-xs text-blue-700 space-y-1">
                        {importResult.updated_list.slice(0, 10).map((name, index) => (
                          <li key={index}>• {name}</li>
                        ))}
                        {importResult.updated_list.length > 10 && (
                          <li className="text-blue-600 italic">... e mais {importResult.updated_list.length - 10}</li>
                        )}
                      </ul>
                    </div>
                  </div>
                )}
              </div>

              {importResult.errors && importResult.errors.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-yellow-800 mb-2">
                    {importResult.errors.length} erro(s) encontrado(s):
                  </p>
                  <div className="max-h-40 overflow-y-auto bg-yellow-50 border border-yellow-200 rounded p-3">
                    <ul className="text-xs text-yellow-800 space-y-1">
                      {importResult.errors.map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center text-red-600">
                <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">Erro na importação</span>
              </div>
              
              <div className="p-4 bg-red-50 border border-red-200 rounded">
                <p className="text-sm text-red-800">{importResult.error || 'Erro desconhecido'}</p>
              </div>
            </div>
          )}
          
          {/* Button to view employees list */}
          {importResult.success && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <button
                onClick={() => {
                  // Trigger cache refresh by adding timestamp
                  navigate('/employees?refresh=' + Date.now());
                }}
                className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                Ver Lista de Colaboradores Atualizada
              </button>
            </div>
          )}
        </div>
      )}

      {/* Progress Modal */}
      {showProgressModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div className="text-center">
              <div className="mb-4">
                <svg className="animate-spin h-12 w-12 text-blue-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Processando Arquivo
              </h3>
              
              <p className="text-sm text-gray-600 mb-1">
                {selectedFile?.name}
              </p>
              
              <p className="text-xs text-gray-500">
                Aguarde enquanto importamos os dados...
              </p>
              
              <div className="mt-4 w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '100%' }}></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataImport;

