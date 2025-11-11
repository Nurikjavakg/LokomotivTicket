import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar/Sidebar';
import { AppBar } from './components/AppBar/AppBar';
import './App.css';
import { Routes, Route, useLocation } from 'react-router-dom';
import AdminPage from './modules/Admin/AdminPage';
import OperatorPage from './modules/Operator/OperatorPage';
import CashierPage from './modules/Cashier/CashierPage';
import AuthPage from './modules/Auth/AuthPage';

export const App = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen(prev => !prev);

  const location = useLocation();

  const pageTitles = {
    '/': 'Вход',
    '/operator': 'Оператор',
    '/cashier': 'Кассир',
    '/admin': 'Админ',
  };

  const currentTitle = pageTitles[location.pathname] || 'Локомотив';

  return (
    <div className="App">
      <AppBar onMenuClick={toggleSidebar} pageTitle={currentTitle} />
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="content">
        <Routes>
          <Route path="/operator" element={<OperatorPage />} />
          <Route path="/cashier" element={<CashierPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/" element={<AuthPage />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;

