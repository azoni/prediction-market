import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function PortfolioPage() {
  const { user } = useAuth();
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('positions');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [positionsData, ordersData, transactionsData] = await Promise.all([
          api.getPositions(),
          api.getOrders('OPEN'),
          api.getTransactions(50),
        ]);
        setPositions(positionsData);
        setOrders(ordersData);
        setTransactions(transactionsData);
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
          <div className="text-mono text-green" style={{ fontSize: '1.5rem' }}>
            {user?.balance?.toFixed(2)} DC
          </div>
        </div>
        <div className="card">
          <div className="text-muted mb-sm">Unrealized P&L</div>
          <div className={`text-mono ${totalUnrealized >= 0 ? 'text-green' : 'text-red'}`} style={{ fontSize: '1.5rem' }}>
            {totalUnrealized >= 0 ? '+' : ''}{totalUnrealized.toFixed(2)} DC
          </div>
        </div>
        <div className="card">
          <div className="text-muted mb-sm">Realized P&L</div>
          <div className={`text-mono ${totalRealized >= 0 ? 'text-green' : 'text-red'}`} style={{ fontSize: '1.5rem' }}>
            {totalRealized >= 0 ? '+' : ''}{totalRealized.toFixed(2)} DC
          </div>
        </div>
      </div>

      <div className="flex gap-sm mb-md">
        <button
          className={`btn btn-sm ${activeTab === 'positions' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('positions')}
        >
          Positions ({positions.length})
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'orders' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('orders')}
        >
          Open Orders ({orders.length})
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'transactions' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('transactions')}
        >
          Transactions
        </button>
      </div>

      {loading ? (
        <div className="text-center"><span className="spinner"></span></div>
      ) : (
        <div className="card">
          {activeTab === 'positions' && (
            positions.length === 0 ? (
              <div className="text-center py-lg">
                <p className="text-muted mb-md">No open positions</p>
                <Link to="/markets" className="btn btn-primary">Browse Markets</Link>
              </div>
            ) : (
              <div>
                {positions.map((pos) => (
                  <Link
                    key={pos.market_id}
                    to={`/markets/${pos.market_id}`}
                    className="flex justify-between items-center py-md"
                    style={{ borderBottom: '1px solid var(--border-color)', textDecoration: 'none', color: 'inherit' }}
                  >
                    <div>
                      <div style={{ fontWeight: 500 }}>{pos.question}</div>
                      <div className="text-sm text-muted mt-xs">
                        {pos.yes_shares > 0 && <span className="text-green mr-sm">YES: {pos.yes_shares}</span>}
                        {pos.no_shares > 0 && <span className="text-red">NO: {pos.no_shares}</span>}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={pos.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl?.toFixed(2)} DC
                      </div>
                      <div className="text-sm text-muted">unrealized</div>
                    </div>
                  </Link>
                ))}
              </div>
            )
          )}

          {activeTab === 'orders' && (
            orders.length === 0 ? (
              <p className="text-muted text-center py-lg">No open orders</p>
            ) : (
              <div>
                {orders.map((order) => (
                  <div
                    key={order.id}
                    className="flex justify-between items-center py-md"
                    style={{ borderBottom: '1px solid var(--border-color)' }}
                  >
                    <div>
                      <span className={`mr-sm ${order.side === 'YES' ? 'text-green' : 'text-red'}`}>
                        {order.side}
                      </span>
                      <span className="text-muted">{order.action}</span>
                      <span className="ml-sm">{order.quantity - order.filled_quantity} @ {(order.price * 100).toFixed(0)}¢</span>
                    </div>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleCancelOrder(order.id)}
                    >
                      Cancel
                    </button>
                  </div>
                ))}
              </div>
            )
          )}

          {activeTab === 'transactions' && (
            transactions.length === 0 ? (
              <p className="text-muted text-center py-lg">No transactions yet</p>
            ) : (
              <div>
                {transactions.map((tx) => (
                  <div
                    key={tx.id}
                    className="flex justify-between items-center py-md"
                    style={{ borderBottom: '1px solid var(--border-color)' }}
                  >
                    <div>
                      <div style={{ fontWeight: 500 }}>{tx.description}</div>
                      <div className="text-sm text-muted">
                        {new Date(tx.created_at).toLocaleDateString()} {new Date(tx.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-mono ${tx.amount >= 0 ? 'text-green' : 'text-red'}`} style={{ fontWeight: 600 }}>
                        {tx.amount >= 0 ? '+' : ''}{tx.amount.toFixed(2)} DC
                      </div>
                      <div className="text-sm text-muted">
                        Bal: {tx.balance_after.toFixed(2)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}

export default PortfolioPage;
