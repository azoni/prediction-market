import React from 'react';
import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import LoginPage from './pages/LoginPage';
import MarketsPage from './pages/MarketsPage';
import MarketDetailPage from './pages/MarketDetailPage';
import CreateMarketPage from './pages/CreateMarketPage';
import PortfolioPage from './pages/PortfolioPage';
import LeaderboardPage from './pages/LeaderboardPage';
import AchievementsPage from './pages/AchievementsPage';
import AdminPage from './pages/AdminPage';

// Admin emails - keep in sync with backend/auth.py
const ADMIN_EMAILS = ['charltonuw@gmail.com'];

function Navigation() {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const isActive = (path) => location.pathname.startsWith(path);
  const isAdmin = user && ADMIN_EMAILS.includes(user.email);

  return (
    <nav className="nav">
      <Link to="/markets" className="nav-brand">DuMarket</Link>

      <div className="nav-links">
        <Link to="/markets" className={`nav-link ${isActive('/markets') ? 'active' : ''}`}>Markets</Link>
        {user && (
          <Link to="/portfolio" className={`nav-link ${isActive('/portfolio') ? 'active' : ''}`}>Portfolio</Link>
        )}
        <Link to="/leaderboard" className={`nav-link ${isActive('/leaderboard') ? 'active' : ''}`}>Leaderboard</Link>
        {user && (
          <Link to="/achievements" className={`nav-link ${isActive('/achievements') ? 'active' : ''}`}>Achievements</Link>
        )}
        {isAdmin && (
          <Link to="/admin" className={`nav-link ${isActive('/admin') ? 'active' : ''}`}>🔧</Link>
        )}
      </div>
      <div className="nav-user">
        {user ? (
          <>
            <span className="nav-balance">{user.balance?.toFixed(2)} DC</span>
            <span className="text-muted">{user.display_name}</span>
            <button onClick={signOut} className="btn btn-secondary btn-sm">Sign Out</button>
          </>
        ) : (
          <Link to="/login" className="btn btn-primary btn-sm">Sign In</Link>
        )}
      </div>
    </nav>
  );
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="text-center mt-lg"><span className="spinner"></span></div>;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  return children;
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  const isAdmin = user && ADMIN_EMAILS.includes(user.email);

  if (loading) {
    return <div className="text-center mt-lg"><span className="spinner"></span></div>;
  }

  if (!user || !isAdmin) {
    return <Navigate to="/markets" />;
  }

  return children;
}

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="app-container">
        <div className="text-center mt-lg">
          <span className="spinner"></span>
          <p className="mt-md text-muted">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <Navigation />
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={user ? <Navigate to="/markets" /> : <LoginPage />} />
        <Route path="/markets" element={<MarketsPage />} />
        <Route path="/markets/:marketId" element={<MarketDetailPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />

        {/* Protected routes */}
        <Route path="/markets/new" element={
          <ProtectedRoute><CreateMarketPage /></ProtectedRoute>
        } />
        <Route path="/portfolio" element={
          <ProtectedRoute><PortfolioPage /></ProtectedRoute>
        } />
        <Route path="/achievements" element={
          <ProtectedRoute><AchievementsPage /></ProtectedRoute>
        } />
        
        {/* Admin only */}
        <Route path="/admin" element={
          <AdminRoute><AdminPage /></AdminRoute>
        } />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/markets" />} />
        <Route path="*" element={<Navigate to="/markets" />} />
      </Routes>
    </div>
  );
}

export default App;
