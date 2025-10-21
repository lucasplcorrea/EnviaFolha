import { useAuth } from '../contexts/AuthContext';

// Mapeamento de páginas permitidas por role
const ROLE_PAGES = {
  admin: ['dashboard', 'employees', 'payroll', 'communications', 'reports', 'users', 'settings'],
  manager: ['dashboard', 'employees', 'payroll', 'communications', 'reports', 'settings'],
  operator: ['dashboard', 'payroll', 'communications', 'reports'],
  viewer: ['reports']
};

// Mapeamento de rotas para páginas
const ROUTE_TO_PAGE = {
  '/': 'dashboard',
  '/dashboard': 'dashboard',
  '/employees': 'employees',
  '/payroll': 'payroll',
  '/payroll-processor': 'payroll',
  '/payroll-sender': 'payroll',
  '/payroll-data': 'payroll',
  '/communications': 'communications',
  '/reports': 'reports',
  '/users': 'users',
  '/settings': 'settings',
  '/system-logs': 'settings'  // Logs fazem parte de settings (admin only)
};

export const usePermissions = () => {
  const { user } = useAuth();
  
  // Flag para controlar logs (somente em desenvolvimento)
  const DEBUG_PERMISSIONS = false; // Mude para true se precisar debugar

  const getUserRole = () => {
    if (!user) {
      if (DEBUG_PERMISSIONS) console.log('🔒 Nenhum usuário logado');
      return null;
    }
    
    // Admin sempre tem acesso total
    if (user.is_admin) {
      if (DEBUG_PERMISSIONS) console.log('👑 Usuário admin - acesso total');
      return 'admin';
    }
    
    const role = user.role || user.role_name;
    if (DEBUG_PERMISSIONS) console.log('🔖 Role do usuário:', role);
    return role;
  };

  const getPageFromRoute = (route) => {
    // Tratar rotas dinâmicas (ex: /employees/123 -> employees)
    const pathParts = route.split('/').filter(Boolean);
    const basePath = pathParts[0] ? `/${pathParts[0]}` : '/';
    
    if (DEBUG_PERMISSIONS) console.log('🔍 Extraindo página da rota:', route, '-> basePath:', basePath);
    
    return ROUTE_TO_PAGE[basePath] || ROUTE_TO_PAGE[route] || basePath.replace('/', '');
  };

  const canAccessPage = (pageOrRoute) => {
    const role = getUserRole();
    if (!role) {
      if (DEBUG_PERMISSIONS) console.log('❌ Sem role - acesso negado para:', pageOrRoute);
      return false;
    }

    const page = getPageFromRoute(pageOrRoute);
    const allowedPages = ROLE_PAGES[role] || [];
    
    const hasAccess = allowedPages.includes(page);
    if (DEBUG_PERMISSIONS) {
      console.log(`🔍 Verificando acesso: role=${role}, page=${page}, permitido=${hasAccess}`);
      console.log('📄 Páginas permitidas:', allowedPages);
    }
    
    return hasAccess;
  };

  const canAccessRoute = (route) => {
    return canAccessPage(route);
  };

  const getAllowedPages = () => {
    const role = getUserRole();
    return role ? ROLE_PAGES[role] || [] : [];
  };

  const getFirstAllowedRoute = () => {
    const allowedPages = getAllowedPages();
    
    if (allowedPages.length === 0) {
      if (DEBUG_PERMISSIONS) console.log('⚠️ Nenhuma página permitida - redirecionando para login');
      return '/login';
    }

    // Mapear primeira página permitida para rota
    const pageToRoute = {
      'dashboard': '/',
      'employees': '/employees',
      'payroll': '/payroll',
      'communications': '/communications',
      'reports': '/reports',
      'users': '/users',
      'settings': '/settings'
    };

    const firstPage = allowedPages[0];
    const route = pageToRoute[firstPage] || '/';
    
    if (DEBUG_PERMISSIONS) console.log('🎯 Primeira rota permitida:', route, 'para página:', firstPage);
    return route;
  };

  return {
    getUserRole,
    canAccessPage,
    canAccessRoute,
    getAllowedPages,
    getFirstAllowedRoute,
    hasRole: (roleName) => getUserRole() === roleName,
    isAdmin: () => getUserRole() === 'admin'
  };
};