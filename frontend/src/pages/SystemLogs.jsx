import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import api from '../services/api';

const SystemLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    level: '',
    category: '',
    limit: 100,
    offset: 0
  });

  const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
  const LOG_CATEGORIES = [
    'SYSTEM', 'AUTH', 'EMPLOYEE', 'IMPORT', 
    'PAYROLL', 'COMMUNICATION', 'WHATSAPP', 'DATABASE', 'API'
  ];

  const LEVEL_COLORS = {
    'DEBUG': 'bg-gray-100 text-gray-800',
    'INFO': 'bg-blue-100 text-blue-800',
    'WARNING': 'bg-yellow-100 text-yellow-800',
    'ERROR': 'bg-red-100 text-red-800',
    'CRITICAL': 'bg-purple-100 text-purple-800'
  };

  const CATEGORY_COLORS = {
    'SYSTEM': 'bg-slate-100 text-slate-700',
    'AUTH': 'bg-indigo-100 text-indigo-700',
    'EMPLOYEE': 'bg-cyan-100 text-cyan-700',
    'IMPORT': 'bg-teal-100 text-teal-700',
    'PAYROLL': 'bg-emerald-100 text-emerald-700',
    'COMMUNICATION': 'bg-sky-100 text-sky-700',
    'WHATSAPP': 'bg-green-100 text-green-700',
    'DATABASE': 'bg-violet-100 text-violet-700',
    'API': 'bg-fuchsia-100 text-fuchsia-700'
  };

  useEffect(() => {
    fetchLogs();
  }, [filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.level) params.append('level', filters.level);
      if (filters.category) params.append('category', filters.category);
      params.append('limit', filters.limit);
      params.append('offset', filters.offset);

      const response = await api.get(`/system/logs?${params.toString()}`);
      setLogs(response.data.logs || []);
    } catch (error) {
      console.error('Erro ao buscar logs:', error);
      toast.error('Erro ao carregar logs do sistema');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value,
      offset: 0 // Reset pagination when filter changes
    }));
  };

  const clearFilters = () => {
    setFilters({
      level: '',
      category: '',
      limit: 100,
      offset: 0
    });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDetails = (details) => {
    if (!details) return null;
    try {
      const parsed = typeof details === 'string' ? JSON.parse(details) : details;
      return (
        <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
          {JSON.stringify(parsed, null, 2)}
        </pre>
      );
    } catch {
      return <p className="mt-2 text-sm text-gray-600">{details}</p>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Logs do Sistema</h1>
          <p className="text-gray-600">Visualize e filtre os registros de atividade do sistema</p>
        </div>
        <button
          onClick={() => fetchLogs()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          🔄 Atualizar
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nível
            </label>
            <select
              value={filters.level}
              onChange={(e) => handleFilterChange('level', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todos</option>
              {LOG_LEVELS.map(level => (
                <option key={level} value={level}>{level}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Categoria
            </label>
            <select
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todas</option>
              {LOG_CATEGORIES.map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Registros por página
            </label>
            <select
              value={filters.limit}
              onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={clearFilters}
              className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Limpar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Logs List */}
      <div className="bg-white rounded-lg shadow-md">
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Carregando logs...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg">Nenhum log encontrado</p>
            <p className="text-sm mt-2">Tente ajustar os filtros ou aguarde novas atividades</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Data/Hora
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nível
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Categoria
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Mensagem
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usuário
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${LEVEL_COLORS[log.level] || 'bg-gray-100 text-gray-800'}`}>
                        {log.level}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${CATEGORY_COLORS[log.category] || 'bg-gray-100 text-gray-700'}`}>
                        {log.category}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div>
                        <p>{log.message}</p>
                        {log.details && formatDetails(log.details)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.username || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination Info */}
      {!loading && logs.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600">
              Mostrando {filters.offset + 1} a {filters.offset + logs.length} de muitos registros
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => handleFilterChange('offset', Math.max(0, filters.offset - filters.limit))}
                disabled={filters.offset === 0}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ← Anterior
              </button>
              <button
                onClick={() => handleFilterChange('offset', filters.offset + filters.limit)}
                disabled={logs.length < filters.limit}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Próxima →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemLogs;
