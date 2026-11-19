import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/auth/Login';
import { Register } from './pages/auth/Register';
import { CitizenDashboard } from './pages/citizen/CitizenDashboard';
import { ReportIncident } from './pages/citizen/ReportIncident';
import { ShelterFinder } from './pages/citizen/ShelterFinder';
import { VolunteerDashboard } from './pages/volunteer/VolunteerDashboard';
import { NGODashboard } from './pages/ngo/NGODashboard';
import { CommandCenter } from './pages/admin/CommandCenter';
import { DisasterSimulationView } from './pages/admin/DisasterSimulationView';
import { RecoveryOptimizationView } from './pages/admin/RecoveryOptimizationView';

const queryClient = new QueryClient();

const ProtectedRoute: React.FC<{ children: React.ReactNode; allowedRoles?: string[] }> = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-center text-xs font-mono text-slate-500">Loading DIRS Security Context...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    let fallbackPath = '/citizen';
    if (user.role === 'ADMIN') fallbackPath = '/admin/recovery-optimization';
    else if (user.role === 'VOLUNTEER') fallbackPath = '/volunteer';
    else if (user.role === 'NGO') fallbackPath = '/ngo';
    else if (user.role === 'GOVT') fallbackPath = '/admin';
    return <Navigate to={fallbackPath} replace />;
  }
  return <Layout>{children}</Layout>;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/citizen" element={
              <ProtectedRoute allowedRoles={['CITIZEN', 'GOVT']}>
                <CitizenDashboard />
              </ProtectedRoute>
            } />

            <Route path="/citizen/report" element={
              <ProtectedRoute allowedRoles={['CITIZEN', 'VOLUNTEER', 'GOVT']}>
                <ReportIncident />
              </ProtectedRoute>
            } />

            <Route path="/citizen/shelters" element={
              <ProtectedRoute>
                <ShelterFinder />
              </ProtectedRoute>
            } />

            <Route path="/volunteer" element={
              <ProtectedRoute allowedRoles={['VOLUNTEER', 'GOVT']}>
                <VolunteerDashboard />
              </ProtectedRoute>
            } />

            <Route path="/ngo" element={
              <ProtectedRoute allowedRoles={['NGO', 'GOVT']}>
                <NGODashboard />
              </ProtectedRoute>
            } />

            <Route path="/admin" element={
              <ProtectedRoute allowedRoles={['GOVT']}>
                <CommandCenter />
              </ProtectedRoute>
            } />

            <Route path="/admin/simulation" element={
              <ProtectedRoute allowedRoles={['GOVT']}>
                <DisasterSimulationView />
              </ProtectedRoute>
            } />

            <Route path="/admin/recovery-optimization" element={
              <ProtectedRoute allowedRoles={['GOVT', 'ADMIN']}>
                <RecoveryOptimizationView />
              </ProtectedRoute>
            } />

            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
