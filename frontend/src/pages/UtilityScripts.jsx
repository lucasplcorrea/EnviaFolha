import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import toast from 'react-hot-toast';
import api from '../services/api';

const UtilityScripts = () => {
  const { config } = useTheme();
  const [loadingScripts, setLoadingScripts] = useState({});
  const [scriptResults, setScriptResults] = useState({});

  const scripts = [
    {
      id: 'fix_unique_id_zeros',
      name: 'Corrigir Zeros à Esquerda nas Matrículas',
      icon: '🔧',
      description: 'Adiciona "00" à esquerda das matrículas que começam com 59 ou 60 (formato: 5900123 → 005900123)',
      category: 'Colaboradores',
      action: 'fix',
      confirmMessage: 'Esta operação irá corrigir as matrículas que perderam zeros à esquerda durante importações. Deseja continuar?',
      dangerLevel: 'medium', // low, medium, high
    },
    // Futuros scripts podem ser adicionados aqui
  ];

  const executeScript = async (script) => {
    // Confirmar execução
    if (script.confirmMessage) {
      const confirmed = window.confirm(script.confirmMessage);
      if (!confirmed) {
        return;
      }
    }

    setLoadingScripts(prev => ({ ...prev, [script.id]: true }));
    setScriptResults(prev => ({ ...prev, [script.id]: null }));

    try {
      const response = await api.post(`/scripts/${script.id}`);
      
      setScriptResults(prev => ({ 
        ...prev, 
        [script.id]: {
          success: true,
          data: response.data,
          timestamp: new Date().toLocaleString('pt-BR')
        }
      }));

      toast.success(response.data.message || 'Script executado com sucesso!');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Erro ao executar script';
      
      setScriptResults(prev => ({ 
        ...prev, 
        [script.id]: {
          success: false,
          error: errorMessage,
          timestamp: new Date().toLocaleString('pt-BR')
        }
      }));

      toast.error(errorMessage);
    } finally {
      setLoadingScripts(prev => ({ ...prev, [script.id]: false }));
    }
  };

  const previewScript = async (script) => {
    setLoadingScripts(prev => ({ ...prev, [`${script.id}_preview`]: true }));

    try {
      const response = await api.get(`/scripts/${script.id}/preview`);
      
      setScriptResults(prev => ({ 
        ...prev, 
        [script.id]: {
          success: true,
          preview: true,
          data: response.data,
          timestamp: new Date().toLocaleString('pt-BR')
        }
      }));

      toast.success('Preview carregado com sucesso!');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Erro ao carregar preview';
      toast.error(errorMessage);
    } finally {
      setLoadingScripts(prev => ({ ...prev, [`${script.id}_preview`]: false }));
    }
  };

  const getDangerLevelColor = (level) => {
    switch (level) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getDangerLevelText = (level) => {
    switch (level) {
      case 'low':
        return 'Baixo Risco';
      case 'medium':
        return 'Risco Moderado';
      case 'high':
        return 'Alto Risco';
      default:
        return 'Risco Desconhecido';
    }
  };

  const renderScriptResult = (script) => {
    const result = scriptResults[script.id];
    if (!result) return null;

    return (
      <div className={`mt-4 p-4 rounded-lg border ${
        result.success 
          ? result.preview 
            ? 'bg-blue-50 border-blue-200'
            : 'bg-green-50 border-green-200'
          : 'bg-red-50 border-red-200'
      }`}>
        <div className="flex items-start justify-between mb-2">
          <h4 className={`font-medium ${
            result.success 
              ? result.preview 
                ? 'text-blue-900'
                : 'text-green-900'
              : 'text-red-900'
          }`}>
            {result.preview ? '🔍 Preview' : result.success ? '✅ Sucesso' : '❌ Erro'}
          </h4>
          <span className="text-xs text-gray-500">{result.timestamp}</span>
        </div>

        {result.success ? (
          <div className="space-y-2">
            {result.data.message && (
              <p className="text-sm text-gray-700">{result.data.message}</p>
            )}
            
            {result.data.affected_count !== undefined && (
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium">Registros afetados:</span>
                <span className="px-2 py-1 bg-white rounded border">
                  {result.data.affected_count}
                </span>
              </div>
            )}

            {result.data.preview_items && result.data.preview_items.length > 0 && (
              <div className="mt-3">
                <p className="text-sm font-medium mb-2">Alterações que serão feitas:</p>
                <div className="bg-white rounded border max-h-48 overflow-y-auto">
                  <table className="min-w-full text-xs">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Nome</th>
                        <th className="px-3 py-2 text-left">Matrícula Atual</th>
                        <th className="px-3 py-2 text-left">Matrícula Corrigida</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {result.data.preview_items.map((item, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-3 py-2">{item.full_name}</td>
                          <td className="px-3 py-2 font-mono text-red-600">{item.old_id}</td>
                          <td className="px-3 py-2 font-mono text-green-600">{item.new_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {result.data.details && (
              <div className="mt-2 text-sm text-gray-600">
                <pre className="bg-white p-2 rounded border overflow-x-auto">
                  {JSON.stringify(result.data.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-red-700">{result.error}</p>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">🛠️</span>
          <div>
            <h2 className={`text-xl font-semibold ${config.classes.text}`}>
              Scripts Úteis
            </h2>
            <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
              Ferramentas para manutenção e correção de dados no sistema
            </p>
          </div>
        </div>
      </div>

      {/* Info Card */}
      <div className={`${config.classes.card} shadow rounded-lg p-4 ${config.classes.border} border-l-4 border-blue-500`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">ℹ️</span>
          <div>
            <h3 className={`font-medium ${config.classes.text} mb-1`}>
              Sobre os Scripts
            </h3>
            <p className={`text-sm ${config.classes.textSecondary}`}>
              Estes scripts realizam operações específicas de manutenção no banco de dados. 
              Sempre use a opção "Preview" antes de executar para ver quais alterações serão feitas.
              <strong className="block mt-2">⚠️ Recomendação: Faça backup do banco antes de executar scripts de risco moderado ou alto.</strong>
            </p>
          </div>
        </div>
      </div>

      {/* Scripts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {scripts.map((script) => (
          <div 
            key={script.id}
            className={`${config.classes.card} shadow rounded-lg overflow-hidden ${config.classes.border}`}
          >
            {/* Script Header */}
            <div className="p-6 pb-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{script.icon}</span>
                  <div>
                    <h3 className={`text-lg font-medium ${config.classes.text}`}>
                      {script.name}
                    </h3>
                    <span className="text-xs text-gray-500 uppercase tracking-wide">
                      {script.category}
                    </span>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded border ${getDangerLevelColor(script.dangerLevel)}`}>
                  {getDangerLevelText(script.dangerLevel)}
                </span>
              </div>

              <p className={`text-sm ${config.classes.textSecondary} mb-4`}>
                {script.description}
              </p>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => previewScript(script)}
                  disabled={loadingScripts[`${script.id}_preview`]}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                           disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium
                           flex items-center justify-center gap-2"
                >
                  {loadingScripts[`${script.id}_preview`] ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Carregando...
                    </>
                  ) : (
                    <>
                      🔍 Preview
                    </>
                  )}
                </button>

                <button
                  onClick={() => executeScript(script)}
                  disabled={loadingScripts[script.id]}
                  className={`flex-1 px-4 py-2 rounded-lg transition-colors text-sm font-medium
                           flex items-center justify-center gap-2
                           ${script.dangerLevel === 'high' 
                             ? 'bg-red-600 hover:bg-red-700 text-white' 
                             : 'bg-green-600 hover:bg-green-700 text-white'
                           }
                           disabled:bg-gray-400 disabled:cursor-not-allowed`}
                >
                  {loadingScripts[script.id] ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Executando...
                    </>
                  ) : (
                    <>
                      ⚡ Executar
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Result Display */}
            {scriptResults[script.id] && (
              <div className="px-6 pb-6">
                {renderScriptResult(script)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty State */}
      {scripts.length === 0 && (
        <div className={`${config.classes.card} shadow rounded-lg p-12 text-center ${config.classes.border}`}>
          <span className="text-6xl mb-4 block">📭</span>
          <h3 className={`text-lg font-medium ${config.classes.text} mb-2`}>
            Nenhum script disponível
          </h3>
          <p className={`text-sm ${config.classes.textSecondary}`}>
            Scripts úteis serão exibidos aqui quando disponíveis.
          </p>
        </div>
      )}
    </div>
  );
};

export default UtilityScripts;
