import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function AdminPage() {
  useAuth(); // Ensures user is logged in
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [markets, setMarkets] = useState([]);
  const [activeTab, setActiveTab] = useState('stats');
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [statsData, usersData, marketsData] = await Promise.all([
        api.client.get('/admin/stats'),
        api.client.get('/admin/users'),
        api.getMarkets(),
      ]);
      setStats(statsData.data);
      setUsers(usersData.data);
      setMarkets(marketsData);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    }
  }, []);

  useEffect(() => {
    const checkAdmin = async () => {
      try {
        await api.client.get('/admin/status');
        setIsAdmin(true);
        loadData();
      } catch (err) {
        setIsAdmin(false);
        setError('You do not have admin privileges.');
      }
      setLoading(false);
    };
    checkAdmin();
  }, [loadData]);

  const handleDeleteMarket = async (marketId, question) => {
    if (!window.confirm(`Delete market "${question}"?\n\nThis will refund all users their cost basis.`)) {
      return;
    }
    try {
      await api.client.delete(`/admin/markets/${marketId}?refund=true`);
      setMarkets(markets.filter(m => m.id !== marketId));
      alert('Market deleted and users refunded.');
    } catch (err) {
      alert('Failed to delete: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleResolveMarket = async (marketId, outcome) => {
    const outcomeText = outcome ? 'YES' : 'NO';
    if (!window.confirm(`Resolve this market as ${outcomeText}?`)) {
      return;
    }
    try {
      await api.client.post(`/admin/markets/${marketId}/resolve`, { outcome });
      loadData();
      alert(`Market resolved as ${outcomeText}.`);
    } catch (err) {
      alert('Failed to resolve: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAdjustBalance = async (userId, displayName) => {
    const amount = prompt(`Adjust balance for ${displayName}:\n\nEnter positive number to add, negative to subtract:`);
    if (!amount) return;

    const reason = prompt('Reason for adjustment (required):');
    if (!reason || reason.length < 3) {
      alert('Reason is required (min 3 characters)');
      return;
    }

    try {
      const result = await api.client.post(`/admin/users/${userId}/adjust-balance`, {
        user_id: userId,
        amount: parseFloat(amount),
        reason,
      });
      alert(`Balance adjusted: ${result.data.old_balance} → ${result.data.new_balance}`);
      loadData();
    } catch (err) {
      alert('Failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return <div className="text-center mt-lg"><span className="spinner"></span></div>;
  }

  if (!isAdmin) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🔒</div>
        <p>Admin Access Required</p>
        <p className="text-muted mt-md">
          {error || 'You need admin privileges to view this page.'}
        </p>
        <p className="text-muted mt-md" style={{ fontSize: '0.875rem' }}>
          To become an admin, add your email to ADMIN_EMAILS in backend/auth.py
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-lg">🔧 Admin Panel</h1>

      {/* Tabs */}
      <div className="flex gap-sm mb-lg">
        {['stats', 'markets', 'users'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Stats Tab */}
      {activeTab === 'stats' && stats && (
        <div className="grid grid-3">
          <div className="card">
            <div className="text-muted mb-sm">Total Users</div>
            <div className="text-mono" style={{ fontSize: '2rem' }}>{stats.total_users}</div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">Total Markets</div>
            <div className="text-mono" style={{ fontSize: '2rem' }}>{stats.total_markets}</div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">Open Markets</div>
            <div className="text-mono" style={{ fontSize: '2rem' }}>{stats.open_markets}</div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">Total Trades</div>
            <div className="text-mono" style={{ fontSize: '2rem' }}>{stats.total_trades}</div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">Total Orders</div>
            <div className="text-mono" style={{ fontSize: '2rem' }}>{stats.total_orders}</div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">Total DuCoins</div>
            <div className="text-mono" style={{ fontSize: '2rem', color: 'var(--accent-green)' }}>
              {stats.total_balance_in_circulation?.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Markets Tab */}
      {activeTab === 'markets' && (
        <div>
          <p className="text-muted mb-md">Manage markets - delete, resolve, or close them.</p>
          {markets.map(market => (
            <div key={market.id} className="card mb-md">
              <div className="flex flex-between flex-center">
                <div style={{ flex: 1 }}>
                  <span className={`market-status market-status-${market.status.toLowerCase()}`}>
                    {market.status}
                  </span>
                  <span className="text-muted" style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>
                    {market.id.slice(0, 8)}...
                  </span>
                  <p className="mt-sm" style={{ fontWeight: 500 }}>{market.question}</p>
                </div>
                <div className="flex gap-sm">
                  {market.status === 'OPEN' && (
                    <>
                      <button
                        onClick={() => handleResolveMarket(market.id, true)}
                        className="btn btn-success btn-sm"
                      >
                        YES
                      </button>
                      <button
                        onClick={() => handleResolveMarket(market.id, false)}
                        className="btn btn-danger btn-sm"
                      >
                        NO
                      </button>
                      <button
                        onClick={() => handleDeleteMarket(market.id, market.question)}
                        className="btn btn-secondary btn-sm"
                      >
                        🗑️
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          <p className="text-muted mb-md">Manage users - view info and adjust balances.</p>
          {users.map(u => (
            <div key={u.id} className="card mb-md">
              <div className="flex flex-between flex-center">
                <div>
                  <div style={{ fontWeight: 500 }}>{u.display_name}</div>
                  <div className="text-muted" style={{ fontSize: '0.875rem' }}>{u.email}</div>
                  <div className="text-mono mt-sm">
                    <span className="text-green">{u.balance?.toFixed(2)} DC</span>
                    <span className="text-muted" style={{ marginLeft: '1rem' }}>
                      {u.total_trades} trades
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleAdjustBalance(u.id, u.display_name)}
                  className="btn btn-secondary btn-sm"
                >
                  Adjust Balance
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AdminPage;
