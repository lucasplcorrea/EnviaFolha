import React, { useState, useEffect } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  ClockIcon,
  DocumentArrowUpIcon,
  CalendarIcon,
  TrashIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

const TimecardUpload = () => {
  const [timecardPeriods, setTimecardPeriods] = useState([]);
  const [processingHistory, setProcessingHistory] = useState([]);
  const [xlsxFile, setXlsxFile] = useState(null);
  const [xlsxYear, setXlsxYear] = useState(new Date().getFullYear());
  const [xlsxMonth, setXlsxMonth] = useState(new Date().getMonth() + 1);
  const [xlsxDryRun, setXlsxDryRun] = useState(true);
  const [xlsxUploading, setXlsxUploading] = useState(false);
  const [xlsxResult, setXlsxResult] = useState(null);
  
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [periodToDelete, setPeriodToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadTimecardPeriods();
    loadProcessingHistory();
  }, []);

  const loadTimecardPeriods = async () => {
    try {
      const response = await api.get('/timecard/periods');
      // A API retorna array diretamente, não objeto com periods
      setTimecardPeriods(Array.isArray(response.data) ? response.data : (response.data.periods || []));
    } catch (error) {
      console.error('Erro ao carregar períodos de cartão ponto:', error);
      toast.error('Erro ao carregar períodos');
    }
  };

  const loadProcessingHistory = async () => {
    try {
      const response = await api.get('/timecard/processing-logs');
      setProcessingHistory(response.data.logs || []);
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
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
      toast.loading('Processando cartão ponto...', { id: 'xlsx-upload' });

      const formData = new FormData();
      formData.append('file', xlsxFile);
      formData.append('year', xlsxYear);
      formData.append('month', xlsxMonth);
      formData.append('dry_run', xlsxDryRun ? 'true' : 'false');

      const response = await api.post('/timecard/upload-xlsx', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const result = response.data;

      if (result.success) {
        toast.success(
          xlsxDryRun ? 'Validação do cartão ponto concluída!' : 'Cartão ponto processado com sucesso!',
          { id: 'xlsx-upload' }
        );
        setXlsxResult(result);
        if (!xlsxDryRun) {
          loadTimecardPeriods();
          loadProcessingHistory(); // Recarregar histórico
          setXlsxFile(null);
        }
      } else {
        toast.error(result.error || 'Erro ao processar cartão ponto', { id: 'xlsx-upload' });
        setXlsxResult(result);
      }
    } catch (error) {
      console.error('Erro ao fazer upload de XLSX:', error);
      toast.error(error.response?.data?.error || 'Erro ao processar cartão ponto', { id: 'xlsx-upload' });
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
      const response = await api.delete(`/timecard/periods/${periodToDelete.id}`);
      
      if (response.data.success) {
        toast.success(`Período "${periodToDelete.period_name}" deletado com sucesso!`);
        setShowDeleteModal(false);
        setPeriodToDelete(null);
        loadTimecardPeriods();
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

  const monthNames = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ];

  // Função para converter horas decimais para formato HH:MM
  const formatHoursMinutes = (decimalHours) => {
    const num = parseFloat(decimalHours);
    if (!num || isNaN(num)) return '00:00';
    const hours = Math.floor(num);
    const minutes = Math.round((num - hours) * 60);
    return `${hours}:${minutes.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center">
          <ClockIcon className="h-8 w-8 mr-3 text-purple-600" />
          Cartão Ponto
        </h1>
        <p className="text-gray-600 mt-1">
          Upload e gerenciamento de horas extras e horas noturnas
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Section */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
            <DocumentArrowUpIcon className="h-6 w-6 mr-2 text-purple-600" />
            Upload de Arquivo XLSX
          </h2>
          
          <div className="space-y-5">
            {/* Competência (Ano/Mês) */}
            <div className="grid grid-cols-2 gap-4">
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
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Mês
                </label>
                <select
                  value={xlsxMonth}
                  onChange={(e) => setXlsxMonth(parseInt(e.target.value))}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {monthNames.map((name, index) => (
                    <option key={index + 1} value={index + 1}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* File Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Arquivo XLSX
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="file"
                  accept=".xlsx,.XLSX"
                  onChange={handleXlsxFileSelect}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                />
              </div>
              {xlsxFile && (
                <p className="mt-2 text-sm text-purple-600">
                  ✓ Arquivo selecionado: {xlsxFile.name} ({(xlsxFile.size / 1024).toFixed(2)} KB)
                </p>
              )}
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={xlsxDryRun}
                onChange={(e) => setXlsxDryRun(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              />
              <span>Somente validar arquivo (dry run, não grava no banco)</span>
            </label>

            {/* Upload Button */}
            <button
              onClick={handleXlsxUpload}
              disabled={!xlsxFile || xlsxUploading}
              className={`w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg font-medium transition-all ${
                !xlsxFile || xlsxUploading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-purple-600 text-white hover:bg-purple-700 shadow-md hover:shadow-lg'
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
                  <span>{xlsxDryRun ? 'Validar Cartão Ponto' : 'Processar Cartão Ponto'}</span>
                </>
              )}
            </button>

            {/* Result Display */}
            {xlsxResult && (
              <div className={`p-4 rounded-lg border ${
                xlsxResult.success 
                  ? 'bg-purple-50 border-purple-200' 
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-start space-x-3">
                  {xlsxResult.success ? (
                    <CheckCircleIcon className="h-6 w-6 text-purple-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <ExclamationTriangleIcon className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <h4 className={`font-medium ${xlsxResult.success ? 'text-purple-900' : 'text-red-900'}`}>
                      {xlsxResult.success ? (xlsxResult.dry_run ? 'Validação Concluída!' : 'Processamento Concluído!') : 'Erro no Processamento'}
                    </h4>
                    {xlsxResult.success && xlsxResult.dry_run && (
                      <p className="mt-1 text-sm text-purple-800">
                        Nenhum dado foi gravado. O arquivo apenas foi validado.
                      </p>
                    )}
                    {xlsxResult.success && (
                      <div className="mt-2 text-sm text-purple-800 space-y-1">
                        <p>• Total de linhas: {xlsxResult.total_rows}</p>
                        <p>• Processadas: {xlsxResult.processed_rows}</p>
                        <p>• Erros: {xlsxResult.error_rows || 0}</p>
                        {xlsxResult.period_name && (
                          <p>• Período: {xlsxResult.period_name}</p>
                        )}
                        {typeof xlsxResult.matched_by_matricula === 'number' && (
                          <p>• Match por matrícula: {xlsxResult.matched_by_matricula}</p>
                        )}
                        {typeof xlsxResult.matched_by_name === 'number' && (
                          <p>• Match por nome: {xlsxResult.matched_by_name}</p>
                        )}
                        {typeof xlsxResult.unmatched_rows === 'number' && (
                          <p>• Sem vínculo direto: {xlsxResult.unmatched_rows}</p>
                        )}
                        {xlsxResult.dry_run && (
                          <>
                            <p>• Criaria novos registros: {xlsxResult.would_create_records || 0}</p>
                            <p>• Atualizaria registros: {xlsxResult.would_update_records || 0}</p>
                            <p>• Período existente: {xlsxResult.period_exists ? 'sim' : 'não'}</p>
                          </>
                        )}
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

        {/* Periods List */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <CalendarIcon className="h-6 w-6 mr-2 text-purple-600" />
            Períodos Cadastrados
          </h2>
          
          <div className="space-y-3">
            {timecardPeriods.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">
                Nenhum período cadastrado
              </p>
            ) : (
              timecardPeriods.map((period) => (
                <div
                  key={period.id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-gray-900 mb-2">
                        {period.period_name}
                      </h3>
                      
                      {/* Resumo */}
                      <p className="text-xs text-gray-600 mb-2">
                        👥 <strong>{period.employee_count}</strong> funcionários
                      </p>
                      
                      {/* Horas Extras Diurnas */}
                      <div className="grid grid-cols-3 gap-2 mb-2">
                        <div className="text-xs text-gray-600">
                          ⏰ HE 50%: <strong>{formatHoursMinutes(period.overtime_50)}</strong>
                        </div>
                        <div className="text-xs text-gray-600">
                          ⏰⏰ HE 100%: <strong>{formatHoursMinutes(period.overtime_100)}</strong>
                        </div>
                        <div className="text-xs text-amber-600 font-medium">
                          Total: <strong>{formatHoursMinutes(period.total_overtime)}</strong>
                        </div>
                      </div>
                      
                      {/* Horas Noturnas */}
                      <div className="grid grid-cols-4 gap-2">
                        <div className="text-xs text-gray-600">
                          🌙 EN 50%: <strong>{formatHoursMinutes(period.night_overtime_50)}</strong>
                        </div>
                        <div className="text-xs text-gray-600">
                          🌙 EN 100%: <strong>{formatHoursMinutes(period.night_overtime_100)}</strong>
                        </div>
                        <div className="text-xs text-gray-600">
                          🌙 Adic.: <strong>{formatHoursMinutes(period.night_hours)}</strong>
                        </div>
                        <div className="text-xs text-indigo-600 font-medium">
                          Total: <strong>{formatHoursMinutes(period.total_night_hours)}</strong>
                        </div>
                      </div>
                      
                      {period.start_date && period.end_date && (
                        <p className="text-xs text-gray-500 mt-2">
                          📅 {new Date(period.start_date).toLocaleDateString('pt-BR')} até{' '}
                          {new Date(period.end_date).toLocaleDateString('pt-BR')}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => confirmDeletePeriod(period)}
                      className="ml-2 text-red-600 hover:text-red-800 transition-colors"
                      title="Deletar período"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              ))
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
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tempo</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processingHistory.length > 0 ? (
                processingHistory.map((log, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {log.created_at ? new Date(log.created_at).toLocaleString('pt-BR') : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 truncate max-w-xs" title={log.filename}>
                      {log.filename || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {log.year}/{log.month}
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

      {/* Delete Confirmation Modal */}
      {showDeleteModal && periodToDelete && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            {/* Backdrop */}
            <div 
              className="fixed inset-0 bg-black opacity-30"
              onClick={() => setShowDeleteModal(false)}
            ></div>
            
            {/* Modal */}
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Confirmar Exclusão
              </h3>
              
              <p className="text-sm text-gray-600 mb-6">
                Tem certeza que deseja deletar o período <strong>{periodToDelete.period_name}</strong>?
                <br /><br />
                Isso irá remover todos os dados de cartão ponto deste período permanentemente.
              </p>
              
              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  disabled={deleting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeletePeriod}
                  disabled={deleting}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {deleting ? 'Deletando...' : 'Deletar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimecardUpload;
