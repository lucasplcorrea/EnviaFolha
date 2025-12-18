import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  QueueListIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  TrashIcon,
  EyeIcon
} from '@heroicons/react/24/outline';

const QueueManagement = () => {
  const { config } = useTheme();
  const [queues, setQueues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedQueue, setSelectedQueue] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    loadQueues();
    // Atualizar a cada 5 segundos
    const interval = setInterval(loadQueues, 5000);
    return () => clearInterval(interval);
  }, [statusFilter, typeFilter]);

  const loadQueues = async () => {
    try {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (typeFilter !== 'all') params.type = typeFilter;

      const response = await api.get('/queue/list', { params });
      setQueues(response.data.queues || []);
    } catch (error) {
      console.error('Erro ao carregar filas:', error);
    }
  };

  const handleCancelQueue = async (queueId) => {
    if (!window.confirm('Tem certeza que deseja cancelar esta fila de envio?')) {
      return;
    }

    try {
      await api.post(`/queue/${queueId}/cancel`);
      toast.success('Fila cancelada com sucesso');
      loadQueues();
    } catch (error) {
      console.error('Erro ao cancelar fila:', error);
      toast.error('Erro ao cancelar fila');
    }
  };

  const handleViewDetails = async (queueId) => {
    try {
      setLoading(true);
      const response = await api.get(`/queue/${queueId}/details`);
      setSelectedQueue(response.data);
      setShowDetails(true);
    } catch (error) {
      console.error('Erro ao carregar detalhes:', error);
      toast.error('Erro ao carregar detalhes da fila');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { color: 'yellow', text: 'Pendente', icon: ClockIcon },
      processing: { color: 'blue', text: 'Processando', icon: ArrowPathIcon },
      completed: { color: 'green', text: 'Concluído', icon: CheckCircleIcon },
      failed: { color: 'red', text: 'Falhou', icon: XCircleIcon },
      cancelled: { color: 'gray', text: 'Cancelado', icon: ExclamationTriangleIcon }
    };

    const cfg = statusConfig[status] || statusConfig.pending;
    const Icon = cfg.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
        bg-${cfg.color}-100 text-${cfg.color}-800 dark:bg-${cfg.color}-900/30 dark:text-${cfg.color}-400`}>
        <Icon className="h-3 w-3 mr-1" />
        {cfg.text}
      </span>
    );
  };

  const getTypeLabel = (type) => {
    const types = {
      payroll: 'Folha de Pagamento',
      communication: 'Comunicado'
    };
    return types[type] || type;
  };

  return (
    <div className={`min-h-screen ${config.classes.background}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={`text-3xl font-bold ${config.classes.text}`}>
                <QueueListIcon className="h-8 w-8 inline mr-2" />
                Gerenciamento de Filas
              </h1>
              <p className={`mt-2 text-sm ${config.classes.textSecondary}`}>
                Monitore e gerencie todas as filas de envio em tempo real
              </p>
            </div>
            <button
              onClick={loadQueues}
              className={`px-4 py-2 rounded-lg ${config.classes.button} transition-colors`}
            >
              <ArrowPathIcon className="h-5 w-5 inline mr-2" />
              Atualizar
            </button>
          </div>
        </div>

        {/* Filtros */}
        <div className={`${config.classes.card} rounded-lg shadow p-4 mb-6 ${config.classes.border}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={`block text-sm font-medium ${config.classes.text} mb-2`}>
                Status:
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className={`w-full px-3 py-2 rounded-lg ${config.classes.input} ${config.classes.border}`}
              >
                <option value="all">Todos</option>
                <option value="pending">Pendente</option>
                <option value="processing">Processando</option>
                <option value="completed">Concluído</option>
                <option value="failed">Falhou</option>
                <option value="cancelled">Cancelado</option>
              </select>
            </div>
            <div>
              <label className={`block text-sm font-medium ${config.classes.text} mb-2`}>
                Tipo:
              </label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className={`w-full px-3 py-2 rounded-lg ${config.classes.input} ${config.classes.border}`}
              >
                <option value="all">Todos</option>
                <option value="payroll">Folha de Pagamento</option>
                <option value="communication">Comunicado</option>
              </select>
            </div>
          </div>
        </div>

        {/* Lista de Filas */}
        <div className="space-y-4">
          {queues.length === 0 ? (
            <div className={`${config.classes.card} rounded-lg shadow p-12 text-center ${config.classes.border}`}>
              <QueueListIcon className={`mx-auto h-12 w-12 ${config.classes.textSecondary}`} />
              <h3 className={`mt-2 text-sm font-medium ${config.classes.text}`}>
                Nenhuma fila encontrada
              </h3>
              <p className={`mt-1 text-sm ${config.classes.textSecondary}`}>
                As filas de envio aparecerão aqui quando forem criadas.
              </p>
            </div>
          ) : (
            queues.map((queue) => (
              <div
                key={queue.queue_id}
                className={`${config.classes.card} rounded-lg shadow p-6 ${config.classes.border} 
                  ${queue.is_active ? 'ring-2 ring-blue-500' : ''}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className={`text-lg font-semibold ${config.classes.text}`}>
                        {queue.description || 'Sem descrição'}
                      </h3>
                      {getStatusBadge(queue.status)}
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm">
                      <span className={config.classes.textSecondary}>
                        <strong>Tipo:</strong> {getTypeLabel(queue.queue_type)}
                      </span>
                      {queue.file_name && (
                        <span className={config.classes.textSecondary}>
                          <strong>Arquivo:</strong> {queue.file_name}
                        </span>
                      )}
                      {queue.computer_name && (
                        <span className={config.classes.textSecondary}>
                          <strong>Computador:</strong> {queue.computer_name}
                        </span>
                      )}
                      <span className={config.classes.textSecondary}>
                        <strong>Iniciado:</strong>{' '}
                        {new Date(queue.started_at).toLocaleString('pt-BR')}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleViewDetails(queue.queue_id)}
                      className={`px-3 py-1 rounded ${config.classes.buttonSecondary}`}
                      title="Ver Detalhes"
                    >
                      <EyeIcon className="h-5 w-5" />
                    </button>
                    {queue.is_active && (
                      <button
                        onClick={() => handleCancelQueue(queue.queue_id)}
                        className="px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
                        title="Cancelar"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Barra de Progresso */}
                <div className="mb-3">
                  <div className="flex justify-between text-sm mb-1">
                    <span className={config.classes.textSecondary}>Progresso</span>
                    <span className={config.classes.text}>
                      {queue.processed_items} / {queue.total_items} ({queue.progress_percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        queue.status === 'completed' ? 'bg-green-500' :
                        queue.status === 'failed' ? 'bg-red-500' :
                        queue.status === 'cancelled' ? 'bg-gray-500' :
                        'bg-blue-500'
                      }`}
                      style={{ width: `${queue.progress_percentage}%` }}
                    ></div>
                  </div>
                </div>

                {/* Estatísticas */}
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-green-600">{queue.successful_items}</p>
                    <p className={`text-xs ${config.classes.textSecondary}`}>Sucesso</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-red-600">{queue.failed_items}</p>
                    <p className={`text-xs ${config.classes.textSecondary}`}>Falhas</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-blue-600">{queue.success_rate}%</p>
                    <p className={`text-xs ${config.classes.textSecondary}`}>Taxa de Sucesso</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Modal de Detalhes */}
        {showDetails && selectedQueue && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className={`${config.classes.card} rounded-lg max-w-4xl w-full max-h-[80vh] overflow-auto`}>
              <div className="p-6">
                <div className="flex justify-between items-start mb-6">
                  <h2 className={`text-2xl font-bold ${config.classes.text}`}>
                    Detalhes da Fila
                  </h2>
                  <button
                    onClick={() => setShowDetails(false)}
                    className={`text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200`}
                  >
                    <XCircleIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Detalhes dos Itens */}
                <div className="space-y-2">
                  <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
                    Itens ({selectedQueue.items?.length || 0})
                  </h3>
                  {selectedQueue.items?.map((item, index) => (
                    <div
                      key={item.id}
                      className={`p-3 rounded ${config.classes.cardHover} ${config.classes.border}`}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <p className={`font-medium ${config.classes.text}`}>
                            {item.employee_name || 'Nome não disponível'}
                          </p>
                          <p className={`text-sm ${config.classes.textSecondary}`}>
                            {item.phone_number}
                          </p>
                        </div>
                        <div className="text-right">
                          {getStatusBadge(item.status)}
                          {item.error_message && (
                            <p className="text-xs text-red-600 mt-1">
                              {item.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QueueManagement;
