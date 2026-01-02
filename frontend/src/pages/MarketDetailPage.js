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
      const pos = await api.getPosition(marketId);
      setPosition(pos);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }, [marketId]);

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
    if (!window.confirm(`Resolve this market as ${outcome ? 'YES' : 'NO'}?`)) return;
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

  const isCreator = market.creator_id === user?.id;
  const canResolve = isCreator && market.status === 'OPEN';

  return (
    <div>
      <div className="mb-lg">
        <div className="flex flex-between flex-center mb-sm">
          <span className={`market-status market-status-${market.status.toLowerCase()}`}>{market.status}</span>
          {canResolve && (
            <div className="flex gap-sm">
              <button onClick={() => handleResolve(true)} className="btn btn-success btn-sm">Resolve YES</button>
              <button onClick={() => handleResolve(false)} className="btn btn-danger btn-sm">Resolve NO</button>
            </div>
          )}
        </div>
        <h1 style={{ fontSize: '1.5rem' }}>{market.question}</h1>
        {market.description && <p className="text-muted mt-sm">{market.description}</p>}
      </div>

      <div className="grid grid-2">
        <div>
          <OrderBookDisplay orderBook={orderBook} />
          <div className="card mt-lg">
            <h3 className="card-title mb-md">Recent Trades</h3>
            {recentTrades.length === 0 ? <p className="text-muted">No trades yet</p> : (
              <div>
                {recentTrades.slice(0, 10).map((trade) => (
                  <div key={trade.id} className="order-book-row">
                    <span className={trade.side === 'YES' ? 'text-green' : 'text-red'}>{trade.side}</span>
                    <span>{trade.quantity} @ {(trade.price * 100).toFixed(0)}¢</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div>
          {market.status === 'OPEN' ? (
            <OrderForm marketId={marketId} orderBook={orderBook} onOrderPlaced={handleOrderPlaced} />
          ) : (
            <div className="card">
              <p className="text-muted text-center">
                {market.status === 'RESOLVED' ? `Market resolved: ${market.resolved_outcome ? 'YES' : 'NO'} won` : 'Market is closed for trading'}
              </p>
            </div>
          )}

          <div className="card mt-lg">
            <h3 className="card-title mb-md">Your Position</h3>
            {position && (position.yes_shares > 0 || position.no_shares > 0) ? (
              <div>
                {position.yes_shares > 0 && (
                  <div className="position-card">
                    <div><span className="text-green">YES</span><span className="text-mono"> {position.yes_shares} shares</span></div>
                    <div><span className="text-muted">Avg: </span><span className="text-mono">{(position.yes_avg_price * 100).toFixed(0)}¢</span></div>
                  </div>
                )}
                {position.no_shares > 0 && (
                  <div className="position-card">
                    <div><span className="text-red">NO</span><span className="text-mono"> {position.no_shares} shares</span></div>
                    <div><span className="text-muted">Avg: </span><span className="text-mono">{(position.no_avg_price * 100).toFixed(0)}¢</span></div>
                  </div>
                )}
                <div className="mt-md">
                  <span className="text-muted">Unrealized P&L: </span>
                  <span className={`text-mono ${position.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                    {position.unrealized_pnl >= 0 ? '+' : ''}{position.unrealized_pnl.toFixed(2)} DC
                  </span>
                </div>
              </div>
            ) : <p className="text-muted">No position in this market</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function OrderBookDisplay({ orderBook }) {
  if (!orderBook) return null;
  const yesBook = orderBook.yes || {};
  const noBook = orderBook.no || {};

  return (
    <div className="card">
      <h3 className="card-title mb-md">Order Book</h3>
      <div className="grid grid-2 gap-md">
        <div>
          <h4 className="text-green text-mono mb-sm">YES</h4>
          <div className="order-book-side">
            <div className="order-book-title">Bids (Buy)</div>
            {(yesBook.bids || []).slice(0, 5).map((level, i) => (
              <div key={i} className="order-book-row order-book-bid"><span>{(level.price * 100).toFixed(0)}¢</span><span>{level.quantity}</span></div>
            ))}
            {(!yesBook.bids || yesBook.bids.length === 0) && <div className="text-muted">No bids</div>}
          </div>
          <div className="order-book-side mt-sm">
            <div className="order-book-title">Asks (Sell)</div>
            {(yesBook.asks || []).slice(0, 5).map((level, i) => (
              <div key={i} className="order-book-row order-book-ask"><span>{(level.price * 100).toFixed(0)}¢</span><span>{level.quantity}</span></div>
            ))}
            {(!yesBook.asks || yesBook.asks.length === 0) && <div className="text-muted">No asks</div>}
          </div>
        </div>
        <div>
          <h4 className="text-red text-mono mb-sm">NO</h4>
          <div className="order-book-side">
            <div className="order-book-title">Bids (Buy)</div>
            {(noBook.bids || []).slice(0, 5).map((level, i) => (
              <div key={i} className="order-book-row order-book-bid"><span>{(level.price * 100).toFixed(0)}¢</span><span>{level.quantity}</span></div>
            ))}
            {(!noBook.bids || noBook.bids.length === 0) && <div className="text-muted">No bids</div>}
          </div>
          <div className="order-book-side mt-sm">
            <div className="order-book-title">Asks (Sell)</div>
            {(noBook.asks || []).slice(0, 5).map((level, i) => (
              <div key={i} className="order-book-row order-book-ask"><span>{(level.price * 100).toFixed(0)}¢</span><span>{level.quantity}</span></div>
            ))}
            {(!noBook.asks || noBook.asks.length === 0) && <div className="text-muted">No asks</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

function OrderForm({ marketId, orderBook, onOrderPlaced }) {
  const [side, setSide] = useState('YES');
  const [action, setAction] = useState('BUY');
  const [orderType, setOrderType] = useState('LIMIT');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (orderBook) {
      const book = side === 'YES' ? orderBook.yes : orderBook.no;
      if (action === 'BUY' && book?.best_ask) setPrice((book.best_ask * 100).toFixed(0));
      else if (action === 'SELL' && book?.best_bid) setPrice((book.best_bid * 100).toFixed(0));
    }
  }, [side, action, orderBook]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const response = await api.placeOrder({
        market_id: marketId,
        side,
        action,
        order_type: orderType,
        quantity: parseInt(quantity),
        price: orderType === 'LIMIT' ? parseFloat(price) / 100 : null,
      });
      setResult({ success: true, message: `Order ${response.filled_quantity > 0 ? 'filled' : 'placed'}!`, details: response });
      setQuantity('');
      onOrderPlaced();
    } catch (err) {
      setResult({ success: false, message: err.response?.data?.detail || err.message });
    }
    setLoading(false);
  };

  const estimatedCost = quantity && price ? (parseInt(quantity) * parseFloat(price) / 100).toFixed(2) : '0.00';

  return (
    <form className="order-form" onSubmit={handleSubmit}>
      <h3 className="card-title mb-md">Place Order</h3>

      <div className="order-form-side">
        <button type="button" className={`order-form-side-btn yes ${side === 'YES' ? 'selected' : ''}`} onClick={() => setSide('YES')}>YES</button>
        <button type="button" className={`order-form-side-btn no ${side === 'NO' ? 'selected' : ''}`} onClick={() => setSide('NO')}>NO</button>
      </div>

      <div className="order-form-tabs">
        <button type="button" className={`order-form-tab ${action === 'BUY' ? 'active' : ''}`} onClick={() => setAction('BUY')}>Buy</button>
        <button type="button" className={`order-form-tab ${action === 'SELL' ? 'active' : ''}`} onClick={() => setAction('SELL')}>Sell</button>
      </div>

      <div className="input-group">
        <label className="input-label">Order Type</label>
        <select className="input" value={orderType} onChange={(e) => setOrderType(e.target.value)}>
          <option value="LIMIT">Limit</option>
          <option value="MARKET">Market</option>
        </select>
      </div>

      <div className="input-group">
        <label className="input-label">Shares</label>
        <input type="number" className="input" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="100" min="1" required />
      </div>

      {orderType === 'LIMIT' && (
        <div className="input-group">
          <label className="input-label">Price (¢)</label>
          <input type="number" className="input" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="50" min="1" max="99" required />
        </div>
      )}

      {orderType === 'LIMIT' && <div className="mb-md text-muted">Estimated {action === 'BUY' ? 'cost' : 'proceeds'}: {estimatedCost} DC</div>}

      <button type="submit" disabled={loading} className={`btn ${action === 'BUY' ? 'btn-success' : 'btn-danger'}`} style={{ width: '100%' }}>
        {loading ? <span className="spinner"></span> : `${action} ${side}`}
      </button>

      {result && (
        <div className={`mt-md ${result.success ? 'text-green' : 'text-red'}`}>
          {result.message}
          {result.details && result.details.filled_quantity > 0 && (
            <div className="text-muted mt-sm">Filled: {result.details.filled_quantity} @ {result.details.average_price ? (result.details.average_price * 100).toFixed(0) + '¢' : 'market'}</div>
          )}
        </div>
      )}
    </form>
  );
}

export default MarketDetailPage;
