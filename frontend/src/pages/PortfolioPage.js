import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function PortfolioPage() {
  const { user } = useAuth();
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('positions');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [positionsData, ordersData] = await Promise.all([
          api.getPositions(),
          api.getOrders('OPEN'),
        ]);
        setPositions(positionsData);
        setOrders(ordersData);
      } catch (err) {
        console.error('Failed to load portfolio:', err);
      }
      setLoading(false);
    };
    loadData();
  }, []);

  const handleCancelOrder = async (orderId) => {
    try {
      await api.cancelOrder(orderId);
      setOrders(orders.filter(o => o.id !== orderId));
    } catch (err) {
      alert('Failed to cancel: ' + err.message);
    }
  };

  const totalUnrealized = positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0);
  const totalRealized = positions.reduce((sum, p) => sum + (p.realized_pnl || 0), 0);

  return (
    <div>
      <h1 className="mb-lg">Portfolio</h1>

      <div className="grid grid-3 mb-lg">
        <div className="card">
          <div className="text-muted mb-sm">Balance</div>
          <div className="text-mono" style={{ fontSize: '1.5rem', color: 'var(--accent-cyan)' }}>{user?.balance?.toFixed(2)} DC</div>
        </div>
        <div className="card">
          <div className="text-muted mb-sm">Unrealized P&L</div>
          <div className="text-mono" style={{ fontSize: '1.5rem', color: totalUnrealized >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {totalUnrealized >= 0 ? '+' : ''}{totalUnrealized.toFixed(2)} DC
          </div>
        </div>
        <div className="card">
          <div className="text-muted mb-sm">Realized P&L</div>
          <div className="text-mono" style={{ fontSize: '1.5rem', color: totalRealized >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {totalRealized >= 0 ? '+' : ''}{totalRealized.toFixed(2)} DC
          </div>
        </div>
      </div>

      <div className="flex gap-sm mb-lg">
        <button onClick={() => setActiveTab('positions')} className={`btn ${activeTab === 'positions' ? 'btn-primary' : 'btn-secondary'}`}>
          Positions ({positions.length})
        </button>
        <button onClick={() => setActiveTab('orders')} className={`btn ${activeTab === 'orders' ? 'btn-primary' : 'btn-secondary'}`}>
          Open Orders ({orders.length})
        </button>
      </div>

      {loading ? (
        <div className="text-center"><span className="spinner"></span></div>
      ) : activeTab === 'positions' ? (
        positions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📊</div>
            <p>No positions yet</p>
            <Link to="/markets" className="btn btn-primary mt-md">Browse Markets</Link>
          </div>
        ) : (
          <div>
            {positions.map((position) => (
              <Link key={position.market_id} to={`/markets/${position.market_id}`} style={{ textDecoration: 'none' }}>
                <div className="card mb-md" style={{ cursor: 'pointer' }}>
                  <div className="flex flex-between flex-center">
                    <div>
                      <div className="text-muted mb-sm" style={{ fontSize: '0.875rem' }}>Market: {position.market_id.slice(0, 8)}...</div>
                      <div className="flex gap-md">
                        {position.yes_shares > 0 && <div><span className="text-green">YES</span><span className="text-mono"> {position.yes_shares}</span><span className="text-muted"> @ {(position.yes_avg_price * 100).toFixed(0)}¢</span></div>}
                        {position.no_shares > 0 && <div><span className="text-red">NO</span><span className="text-mono"> {position.no_shares}</span><span className="text-muted"> @ {(position.no_avg_price * 100).toFixed(0)}¢</span></div>}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-mono ${position.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}`}>{position.unrealized_pnl >= 0 ? '+' : ''}{position.unrealized_pnl.toFixed(2)} DC</div>
                      <div className="text-muted" style={{ fontSize: '0.75rem' }}>unrealized</div>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )
      ) : orders.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p>No open orders</p>
        </div>
      ) : (
        <div>
          {orders.map((order) => (
            <div key={order.id} className="card mb-md">
              <div className="flex flex-between flex-center">
                <div>
                  <div className="flex gap-sm flex-center mb-sm">
                    <span className={`market-status ${order.action === 'BUY' ? 'market-status-open' : 'market-status-closed'}`}>{order.action}</span>
                    <span className={order.side === 'YES' ? 'text-green' : 'text-red'}>{order.side}</span>
                  </div>
                  <div className="text-mono">{order.quantity - order.filled_quantity} / {order.quantity} @ {(order.price * 100).toFixed(0)}¢</div>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>Market: {order.market_id.slice(0, 8)}...</div>
                </div>
                <button onClick={() => handleCancelOrder(order.id)} className="btn btn-danger btn-sm">Cancel</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PortfolioPage;
