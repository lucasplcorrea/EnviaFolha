import React from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import { usePermissions } from '../hooks/usePermissions';

const ProtectedRoute = ({ children }) => {
  const location = useLocation();
  const { canAccessRoute, userRole } = usePermissions();
  
  const hasAccess = canAccessRoute(location.pathname);
  
  if (!hasAccess) {
    // Redirecionar para dashboard se não tiver acesso
    return <Navigate to="/" replace />;
  }
  
  return children;
};

// Componente para bloquear acesso baseado em ação específica
export const ProtectedAction = ({ action, children, fallback = null }) => {
  const { canPerformAction } = usePermissions();
  
  if (!canPerformAction(action)) {
    return fallback;
  }
  
  return children;
};

// Componente para mostrar/esconder elementos baseado no papel
export const RoleBasedComponent = ({ allowedRoles, children, fallback = null }) => {
  const { userRole } = usePermissions();
  
  if (!allowedRoles.includes(userRole)) {
    return fallback;
  }
  
  return children;
};

export default ProtectedRoute;