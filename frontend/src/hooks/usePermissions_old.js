import { useAuth } from '../contexts/AuthContext';

// Mapeamento de rotas e papéis permitidos
const ROUTE_PERMISSIONS = {
  '/': ['admin', 'manager', 'operator', 'viewer'],           // Dashboard
  '/employees': ['admin', 'manager', 'operator', 'viewer'],  // Colaboradores  
  '/payroll-processor': ['admin', 'manager', 'operator'],    // Processar Holerites
  '/payroll-sender': ['admin', 'manager', 'operator'],       // Enviar Holerites
  '/payroll-data': ['admin', 'manager'],                     // Dados de Folha
  '/communications': ['admin', 'manager', 'operator'],       // Comunicados
  '/reports': ['admin', 'manager'],                          // Relatórios
  '/settings': ['admin']                                     // Configurações
};

// Permissões dentro das páginas
const ACTION_PERMISSIONS = {
  // Colaboradores
  'employees.create': ['admin', 'manager'],
  'employees.edit': ['admin', 'manager'], 
  'employees.delete': ['admin', 'manager'],
  'employees.view': ['admin', 'manager', 'operator', 'viewer'],
  
  // Dashboard
  'dashboard.analytics': ['admin', 'manager'],
  'dashboard.basic': ['admin', 'manager', 'operator', 'viewer'],
  
  // Relatórios
  'reports.advanced': ['admin', 'manager'],
  'reports.basic': ['admin', 'manager'],
  
  // Sistema
  'system.settings': ['admin'],
  'system.users': ['admin']
};

export const usePermissions = () => {
  const { user } = useAuth();

  const getUserRole = () => {
    if (!user) {
      console.log('🔒 usePermissions: Usuário não logado');
      return null;
    }
    
    console.log('👤 usePermissions: Usuário logado:', user);
    
    // Admin tem precedência
    if (user.is_admin) {
      console.log('👑 usePermissions: Usuário é admin');
      return 'admin';
    }
    
    // Usar role do usuário ou fallback
    const role = user.role || 'viewer';
    console.log('🎭 usePermissions: Role do usuário:', role);
    return role;
  };

  const canAccessRoute = (route) => {
    const userRole = getUserRole();
    if (!userRole) {
      console.log('❌ usePermissions: Sem role, negando acesso a', route);
      return false;
    }
    
    const allowedRoles = ROUTE_PERMISSIONS[route];
    if (!allowedRoles) {
      console.log('❓ usePermissions: Rota não mapeada:', route);
      return false;
    }
    
    const hasAccess = allowedRoles.includes(userRole);
    console.log(`🚦 usePermissions: ${userRole} tentando acessar ${route} - ${hasAccess ? 'PERMITIDO' : 'NEGADO'}`);
    return hasAccess;
  };

  const canPerformAction = (action) => {
    const userRole = getUserRole();
    if (!userRole) return false;
    
    const allowedRoles = ACTION_PERMISSIONS[action];
    if (!allowedRoles) return false;
    
    return allowedRoles.includes(userRole);
  };

  const getAccessibleRoutes = () => {
    const userRole = getUserRole();
    if (!userRole) return [];
    
    return Object.keys(ROUTE_PERMISSIONS).filter(route => 
      ROUTE_PERMISSIONS[route].includes(userRole)
    );
  };

  return {
    userRole: getUserRole(),
    canAccessRoute,
    canPerformAction, 
    getAccessibleRoutes,
    user
  };
};

export default usePermissions;