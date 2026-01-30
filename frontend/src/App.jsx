import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Employees from './pages/Employees.jsx';
import PayrollProcessor from './pages/PayrollProcessor.jsx';
import PayrollSender from './pages/PayrollSender.jsx';
import CommunicationSender from './pages/CommunicationSender.jsx';
import Settings from './pages/Settings.jsx';
import Reports from './pages/Reports.jsx';
import Users from './pages/Users.jsx';
import PayrollDataProcessor from './pages/PayrollDataProcessor.jsx';
import DataImport from './pages/DataImport.jsx';
import EmployeeDetail from './pages/EmployeeDetail.jsx';
import SystemLogs from './pages/SystemLogs.jsx';
import Endomarketing from './pages/Endomarketing.jsx';
import RHIndicators from './pages/RHIndicators.jsx';
import QueueManagement from './pages/QueueManagement.jsx';

// Indicadores Refatorados
import {
  IndicatorsLayout,
  Overview as IndicatorsOverview,
  Headcount,
  Turnover,
  Demographics,
  Tenure,
  Leaves,
  Payroll as PayrollIndicators
} from './pages/indicators';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const AuthProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="spinner"></div>
      </div>
    );
  }
  
  return user ? children : <Navigate to="/login" />;
};

function AppContent() {
  const { user } = useAuth();
  
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/login" 
            element={user ? <Navigate to="/" /> : <Login />} 
          />
          <Route
            path="/*"
            element={
              <AuthProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                    <Route path="employees/:id" element={<ProtectedRoute><EmployeeDetail /></ProtectedRoute>} />
                    <Route path="employees" element={<ProtectedRoute><Employees /></ProtectedRoute>} />
                    {/* Rota removida: importação agora é feita em /employees */}
                    <Route path="payroll-processor" element={<ProtectedRoute><PayrollProcessor /></ProtectedRoute>} />
                    <Route path="payroll-sender" element={<ProtectedRoute><PayrollSender /></ProtectedRoute>} />
                    <Route path="payroll" element={<ProtectedRoute><PayrollSender /></ProtectedRoute>} />
                    <Route path="communications" element={<ProtectedRoute><CommunicationSender /></ProtectedRoute>} />
                    <Route path="endomarketing" element={<ProtectedRoute><Endomarketing /></ProtectedRoute>} />
                    <Route path="rh-indicators" element={<ProtectedRoute><RHIndicators /></ProtectedRoute>} />
                    {/* Novos Indicadores Refatorados */}
                    <Route path="indicators" element={<ProtectedRoute><IndicatorsLayout /></ProtectedRoute>}>
                      <Route index element={<IndicatorsOverview />} />
                      <Route path="overview" element={<IndicatorsOverview />} />
                      <Route path="headcount" element={<Headcount />} />
                      <Route path="turnover" element={<Turnover />} />
                      <Route path="demographics" element={<Demographics />} />
                      <Route path="tenure" element={<Tenure />} />
                      <Route path="leaves" element={<Leaves />} />
                      <Route path="payroll" element={<PayrollIndicators />} />
                    </Route>
                    <Route path="queue-management" element={<ProtectedRoute><QueueManagement /></ProtectedRoute>} />
                    <Route path="reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
                    <Route path="users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
                    <Route path="settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                    <Route path="system-logs" element={<ProtectedRoute><SystemLogs /></ProtectedRoute>} />
                    <Route path="payroll-data" element={<ProtectedRoute><PayrollDataProcessor /></ProtectedRoute>} />
                  </Routes>
                </Layout>
              </AuthProtectedRoute>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
            }}
          />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
