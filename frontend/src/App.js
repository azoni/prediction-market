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

function App() {
  const { user, loading, signOut } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="login-page">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!user && location.pathname !== '/login') {
    return <Navigate to="/login" replace />;
  }

  if (user && location.pathname === '/login') {
    return <Navigate to="/markets" replace />;
  }

  return (
    <div className="app-container">
      {user && <Navigation user={user} onSignOut={signOut} />}

      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/markets" element={<MarketsPage />} />
        <Route path="/markets/new" element={<CreateMarketPage />} />
        <Route path="/markets/:marketId" element={<MarketDetailPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/achievements" element={<AchievementsPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/" element={<Navigate to="/markets" replace />} />
      </Routes>
    </div>
  );
}

function Navigation({ user, onSignOut }) {
  const location = useLocation();
  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <nav className="nav">
      <Link to="/markets" className="nav-brand">DuMarket</Link>

      <div className="nav-links">
        <Link to="/markets" className={`nav-link ${isActive('/markets') ? 'active' : ''}`}>Markets</Link>
        <Link to="/portfolio" className={`nav-link ${isActive('/portfolio') ? 'active' : ''}`}>Portfolio</Link>
        <Link to="/leaderboard" className={`nav-link ${isActive('/leaderboard') ? 'active' : ''}`}>Leaderboard</Link>
        <Link to="/achievements" className={`nav-link ${isActive('/achievements') ? 'active' : ''}`}>Achievements</Link>
        <Link to="/admin" className={`nav-link ${isActive('/admin') ? 'active' : ''}`}>🔧</Link>
      </div>

      <div className="nav-user">
        <span className="nav-balance">{user.balance?.toFixed(2)} DC</span>
        <span className="text-muted">{user.display_name}</span>
        <button onClick={onSignOut} className="btn btn-secondary btn-sm">Sign Out</button>
      </div>
    </nav>
  );
}

export default App;
