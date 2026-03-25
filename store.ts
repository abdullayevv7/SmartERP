import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import LoginForm from './components/auth/LoginForm';
import ModuleLayout from './components/layout/ModuleLayout';
import { useAuth } from './hooks/useAuth';
import DashboardPage from './pages/DashboardPage';
import FinanceModule from './pages/FinanceModule';
import HRModule from './pages/HRModule';
import InventoryModule from './pages/InventoryModule';
import ProcurementModule from './pages/ProcurementModule';
import ProjectsModule from './pages/ProjectsModule';
import SalesModule from './pages/SalesModule';
import SettingsPage from './pages/SettingsPage';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Loading SmartERP...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <ModuleLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="hr/*" element={<HRModule />} />
        <Route path="finance/*" element={<FinanceModule />} />
        <Route path="inventory/*" element={<InventoryModule />} />
        <Route path="procurement/*" element={<ProcurementModule />} />
        <Route path="sales/*" element={<SalesModule />} />
        <Route path="projects/*" element={<ProjectsModule />} />
        <Route path="settings/*" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
