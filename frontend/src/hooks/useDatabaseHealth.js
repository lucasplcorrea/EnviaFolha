import { useState, useEffect, useCallback } from 'react';
import { healthAPI } from '../services/api';
import toast from 'react-hot-toast';

export const useDatabaseHealth = (checkInterval = 30000) => {
  const [databaseStatus, setDatabaseStatus] = useState({
    status: 'checking',
    message: 'Verificando conexão...',
    lastCheck: null,
    isOnline: null
  });

  const checkDatabaseHealth = useCallback(async () => {
    try {
      const response = await healthAPI.quickHealthCheck();
      const { status, message } = response.data;
      
      const newStatus = {
        status,
        message,
        lastCheck: new Date().toISOString(),
        isOnline: status === 'online'
      };
      
      setDatabaseStatus(prevStatus => {
        // Se estava offline e agora está online, mostrar notificação
        if (prevStatus.isOnline === false && newStatus.isOnline === true) {
          toast.success('🟢 Conexão com banco de dados restaurada!');
        }
        // Se estava online e agora está offline, mostrar erro
        else if (prevStatus.isOnline === true && newStatus.isOnline === false) {
          toast.error('🔴 Banco de dados desconectado!');
        }
        
        return newStatus;
      });
      
    } catch (error) {
      const errorStatus = {
        status: 'offline',
        message: error.response?.data?.message || 'Erro de conexão com o servidor',
        lastCheck: new Date().toISOString(),
        isOnline: false
      };
      
      setDatabaseStatus(prevStatus => {
        // Se era a primeira verificação ou estava online antes
        if (prevStatus.isOnline !== false) {
          toast.error('🔴 Não foi possível conectar ao banco de dados!');
        }
        
        return errorStatus;
      });
    }
  }, []);

  useEffect(() => {
    // Verificação inicial
    checkDatabaseHealth();
    
    // Verificações periódicas
    const interval = setInterval(checkDatabaseHealth, checkInterval);
    
    return () => clearInterval(interval);
  }, [checkDatabaseHealth, checkInterval]);

  return {
    databaseStatus,
    refreshDatabaseHealth: checkDatabaseHealth
  };
};