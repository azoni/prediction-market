import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function MarketDetailPage() {
  const { marketId } = useParams();
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [market, setMarket] = useState(null);
  const [orderBook, setOrderBook] = useState(null);
  const [recentTrades, setRecentTrades] = useState([]);
  const [position, setPosition] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadMarket = useCallback(async () => {
    try {
      const data = await api.getMarket(marketId);
      setMarket(data.market);
      setOrderBook(data.order_book);
      setRecentTrades(data.recent_trades);
      
      if (user) {
        try {
          const pos = await api.getPosition(marketId);
          setPosition(pos);
        } catch (e) {
          // Ignore position errors
        }
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }, [marketId, user]);

  useEffect(() => {
    loadMarket();
    const interval = setInterval(loadMarket, 10000);
    return () => clearInterval(interval);
  }, [loadMarket]);

  const handleOrderPlaced = () => {
    loadMarket();
    refreshUser();
  };

  const handleResolve = async (outcome) => {
    if (!window.confirm(`Resolve this market as ${outcome ? 'YES' : 'NO'}? This cannot be undone.`)) return;
    try {
      await api.resolveMarket(marketId, outcome);
      loadMarket();
      refreshUser();
    } catch (err) {
      alert('Failed to resolve: ' + err.message);
    }
  };

  if (loading) return <div className="text-center mt-lg"><span className="spinner"></span></div>;
  if (error || !market) return (
    <div className="empty-state">
      <p>Failed to load market</p>
      <button onClick={() => navigate('/markets')} className="btn btn-secondary mt-md">Back to Markets</button>
    </div>
  );

  const isCreator = user && market.creator_id === user.id;
  const canResolve = isCreator && market.status === 'OPEN';

  return (
    <div>
      <div className="flex justify-between items-start mb-lg">
        <div style={{ flex: 1 }}>
          <span className={`market-status market-status-${market.status.toLowerCase()}`}>
            {market.status}
          </span>
          <h1 style={{ marginTop: '0.5rem' }}>{market.question}</h1>
          {market.description && (
            <p className="text-muted mt-sm">{market.description}</p>
          )}
        </div>
        {canResolve && (
          <div className="flex gap-sm" style={{ marginLeft: '1rem' }}>
            <button onClick={() => handleResolve(true)} className="btn btn-success btn-sm">
              Resolve YES
            </button>
            <button onClick={() => handleResolve(false)} className="btn btn-danger btn-sm">
              Resolve NO
            </button>
          </div>
        )}
      </div>

      {market.status === 'RESOLVED' && (
        <div className="card mb-lg" style={{ 
          borderColor: market.resolved_outcome ? 'var(--accent-green)' : 'var(--accent-red)',
          background: market.resolved_outcome ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'
        }}>
          <div className="text-center">
            <div className="text-muted mb-sm">Resolved</div>
            <div style={{ fontSize: '2rem', fontWeight: 700 }} className={market.resolved_outcome ? 'text-green' : 'text-red'}>
              {market.resolved_outcome ? 'YES' : 'NO'}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-2 mb-lg">
        <div className="card">
          <h3 className="card-title mb-md">Order Book</h3>
          <div className="grid grid-2">
            <OrderBookSide title="YES" book={orderBook?.yes} />
            <OrderBookSide title="NO" book={orderBook?.no} />
          </div>
        </div>

        <div className="card">
          <h3 className="card-title mb-md">Place Order</h3>
          {user ? (
            market.status === 'OPEN' ? (
              <OrderForm
                marketId={marketId}
                orderBook={orderBook}
                position={position}
                userBalance={user.balance}
                onOrderPlaced={handleOrderPlaced}
              />
            ) : (
              <p className="text-muted text-center">Market is {market.status.toLowerCase()}</p>
            )
          ) : (
            <div className="text-center">
              <p className="text-muted mb-md">Sign in to place orders</p>
              <button onClick={() => navigate('/login')} className="btn btn-primary">
                Sign In
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3 className="card-title mb-md">Recent Trades</h3>
          {recentTrades.length === 0 ? (
            <p className="text-muted">No trades yet</p>
          ) : (
            <div>
              {recentTrades.slice(0, 10).map((trade) => (
                <div key={trade.id} className="flex justify-between py-sm" style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <span className={trade.side === 'YES' ? 'text-green' : 'text-red'}>
                    {trade.side}
                  </span>
                  <span className="text-mono">
                    {trade.quantity} @ {(trade.price * 100).toFixed(0)}¢
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {user && (
          <div className="card">
            <h3 className="card-title mb-md">Your Position</h3>
            {position && (position.yes_shares > 0 || position.no_shares > 0) ? (
              <div>
                {position.yes_shares > 0 && (
                  <div className="flex justify-between mb-sm">
                    <span><span className="text-green">YES</span> {position.yes_shares} shares</span>
                    <span className="text-muted">Avg: {(position.yes_avg_price * 100).toFixed(0)}¢</span>
                  </div>
                )}
                {position.no_shares > 0 && (
                  <div className="flex justify-between mb-sm">
                    <span><span className="text-red">NO</span> {position.no_shares} shares</span>
                    <span className="text-muted">Avg: {(position.no_avg_price * 100).toFixed(0)}¢</span>
                  </div>
                )}
                <div className="mt-md pt-md" style={{ borderTop: '1px solid var(--border-color)' }}>
                  <span className="text-muted">Unrealized P&L: </span>
                  <span className={position.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}>
                    {position.unrealized_pnl >= 0 ? '+' : ''}{position.unrealized_pnl?.toFixed(2)} DC
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-muted">No position in this market</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function OrderBookSide({ title, book }) {
  const isYes = title === 'YES';

  return (
    <div>
      <div className={`text-mono mb-sm ${isYes ? 'text-green' : 'text-red'}`} style={{ fontWeight: 700 }}>
        {title}
      </div>

      <div className="order-book-side mb-sm">
        <div className="order-book-title">Bids (Buy)</div>
        {book?.bids?.length > 0 ? (
          book.bids.slice(0, 5).map((level, i) => (
            <div key={i} className="order-book-row">
              <span className="text-green">{(level.price * 100).toFixed(0)}¢</span>
              <span className="text-muted">{level.quantity}</span>
            </div>
          ))
        ) : (
          <div className="text-muted text-sm">No bids</div>
        )}
      </div>

      <div className="order-book-side">
        <div className="order-book-title">Asks (Sell)</div>
        {book?.asks?.length > 0 ? (
          book.asks.slice(0, 5).map((level, i) => (
            <div key={i} className="order-book-row">
              <span className="text-red">{(level.price * 100).toFixed(0)}¢</span>
              <span className="text-muted">{level.quantity}</span>
            </div>
          ))
        ) : (
          <div className="text-muted text-sm">No asks</div>
        )}
      </div>
    </div>
  );
}

function OrderForm({ marketId, orderBook, position, userBalance, onOrderPlaced }) {
  const [side, setSide] = useState('YES');
  const [action, setAction] = useState('BUY');
  const [orderType, setOrderType] = useState('MARKET');
  const [quantity, setQuantity] = useState(10);
  const [price, setPrice] = useState(0.5);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const book = side === 'YES' ? orderBook?.yes : orderBook?.no;
  const bestAsk = book?.best_ask;
  const bestBid = book?.best_bid;

  const estimatedPrice = orderType === 'MARKET' 
    ? (action === 'BUY' ? (bestAsk || 0.99) : (bestBid || 0.01))
    : price;
  const estimatedTotal = quantity * estimatedPrice;

  const maxBuyShares = Math.floor(userBalance / (orderType === 'MARKET' ? (bestAsk || 0.99) : price));
  const maxSellShares = side === 'YES' ? (position?.yes_shares || 0) : (position?.no_shares || 0);
  const maxShares = action === 'BUY' ? maxBuyShares : maxSellShares;

  const handleSubmit = async () => {
    setSubmitting(true);
    setResult(null);
    try {
      const res = await api.placeOrder({
        market_id: marketId,
        side,
        action,
        order_type: orderType,
        quantity,
        price: orderType === 'LIMIT' ? price : undefined,
      });
      setResult({
        success: true,
        message: res.status === 'FILLED' ? 'Order filled!' : 
                 res.status === 'PARTIAL' ? 'Partially filled' : 
                 res.status === 'CANCELLED' ? 'No liquidity available' : 'Order placed',
        details: res.filled_quantity > 0 
          ? `Filled: ${res.filled_quantity} @ ${(res.average_price * 100).toFixed(0)}¢`
          : null
      });
      onOrderPlaced();
    } catch (err) {
      setResult({ success: false, message: err.message });
    }
    setSubmitting(false);
  };

  const presetAmounts = [10, 25, 50, 100];

  return (
    <div>
      <div className="grid grid-2 gap-sm mb-md">
        <button
          className={`btn ${side === 'YES' ? 'btn-success' : 'btn-secondary'}`}
          onClick={() => setSide('YES')}
        >
          YES
        </button>
        <button
          className={`btn ${side === 'NO' ? 'btn-danger' : 'btn-secondary'}`}
          onClick={() => setSide('NO')}
        >
          NO
        </button>
      </div>

      <div className="grid grid-2 gap-sm mb-md">
        <button
          className={`btn btn-sm ${action === 'BUY' ? '' : 'btn-secondary'}`}
          onClick={() => setAction('BUY')}
          style={action === 'BUY' ? { background: 'var(--accent-cyan)', color: 'black' } : {}}
        >
          Buy
        </button>
        <button
          className={`btn btn-sm ${action === 'SELL' ? '' : 'btn-secondary'}`}
          onClick={() => setAction('SELL')}
          style={action === 'SELL' ? { background: 'var(--accent-purple)' } : {}}
        >
          Sell
        </button>
      </div>

      <div className="input-group">
        <label className="input-label">Order Type</label>
        <select
          className="input"
          value={orderType}
          onChange={(e) => setOrderType(e.target.value)}
        >
          <option value="MARKET">Market</option>
          <option value="LIMIT">Limit</option>
        </select>
      </div>

      {orderType === 'LIMIT' && (
        <div className="input-group">
          <label className="input-label">Price (¢)</label>
          <input
            type="number"
            className="input"
            min="1"
            max="99"
            value={Math.round(price * 100)}
            onChange={(e) => setPrice(parseInt(e.target.value) / 100)}
          />
        </div>
      )}

      <div className="input-group">
        <label className="input-label">Shares</label>
        <input
          type="number"
          className="input"
          min="1"
          max="10000"
          value={quantity}
          onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
        />
      </div>

      <div className="flex gap-sm mb-md" style={{ flexWrap: 'wrap' }}>
        {presetAmounts.map((amt) => (
          <button
            key={amt}
            className={`btn btn-sm ${quantity === amt ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setQuantity(amt)}
            style={{ minWidth: '50px' }}
          >
            {amt}
          </button>
        ))}
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => setQuantity(Math.max(1, maxShares))}
          disabled={maxShares <= 0}
          style={{ minWidth: '50px' }}
        >
          MAX
        </button>
      </div>

      <div className="mb-md p-sm" style={{ background: 'var(--bg-secondary)', borderRadius: '8px' }}>
        <div className="flex justify-between text-sm">
          <span className="text-muted">Est. Price:</span>
          <span className="text-mono">{(estimatedPrice * 100).toFixed(0)}¢</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted">{action === 'BUY' ? 'Total Cost:' : 'Proceeds:'}</span>
          <span className="text-mono" style={{ fontWeight: 700 }}>
            {estimatedTotal.toFixed(2)} DC
          </span>
        </div>
        {action === 'BUY' && (
          <div className="flex justify-between text-sm">
            <span className="text-muted">Balance After:</span>
            <span className={`text-mono ${userBalance - estimatedTotal < 0 ? 'text-red' : ''}`}>
              {(userBalance - estimatedTotal).toFixed(2)} DC
            </span>
          </div>
        )}
      </div>

      <button
        className={`btn btn-lg w-full ${action === 'BUY' ? 'btn-success' : 'btn-danger'}`}
        onClick={handleSubmit}
        disabled={submitting || quantity <= 0 || (action === 'BUY' && estimatedTotal > userBalance) || (action === 'SELL' && quantity > maxSellShares)}
      >
        {submitting ? 'Placing...' : `${action} ${side}`}
      </button>

      {action === 'BUY' && estimatedTotal > userBalance && (
        <p className="text-red text-sm mt-sm">Insufficient balance</p>
      )}
      {action === 'SELL' && quantity > maxSellShares && (
        <p className="text-red text-sm mt-sm">You only have {maxSellShares} {side} shares</p>
      )}

      {result && (
        <div className={`mt-md ${result.success ? 'text-green' : 'text-red'}`}>
          <div>{result.message}</div>
          {result.details && <div className="text-muted text-sm">{result.details}</div>}
        </div>
      )}
    </div>
  );
}

export default MarketDetailPage;
