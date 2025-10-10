import React from 'react';
import { useDatabaseHealth } from '../hooks/useDatabaseHealth';

const DatabaseStatusIndicator = ({ className = '' }) => {
  const { databaseStatus, refreshDatabaseHealth } = useDatabaseHealth();
  
  const getStatusColor = () => {
    switch (databaseStatus.status) {
      case 'online':
        return 'text-green-600 bg-green-100';
      case 'offline':
        return 'text-red-600 bg-red-100';
      case 'checking':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = () => {
    switch (databaseStatus.status) {
      case 'online':
        return '🟢';
      case 'offline':
        return '🔴';
      case 'checking':
        return '🟡';
      default:
        return '⚪';
    }
  };

  const formatLastCheck = () => {
    if (!databaseStatus.lastCheck) return '';
    
    const lastCheck = new Date(databaseStatus.lastCheck);
    const now = new Date();
    const diffInSeconds = Math.floor((now - lastCheck) / 1000);
    
    if (diffInSeconds < 60) {
      return `há ${diffInSeconds}s`;
    } else if (diffInSeconds < 3600) {
      return `há ${Math.floor(diffInSeconds / 60)}m`;
    } else {
      return lastCheck.toLocaleTimeString();
    }
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()} ${className}`}>
      <span>{getStatusIcon()}</span>
      <span>Banco: {databaseStatus.status === 'online' ? 'Online' : 
                      databaseStatus.status === 'offline' ? 'Offline' : 
                      'Verificando...'}</span>
      
      {databaseStatus.lastCheck && (
        <span className="text-xs opacity-75">
          {formatLastCheck()}
        </span>
      )}
      
      {databaseStatus.status === 'offline' && (
        <button
          onClick={refreshDatabaseHealth}
          className="ml-1 text-xs underline hover:no-underline"
          title="Tentar reconectar"
        >
          Reconectar
        </button>
      )}
    </div>
  );
};

export default DatabaseStatusIndicator;