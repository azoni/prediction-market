import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';

function MarketsPage() {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('OPEN');
  const navigate = useNavigate();

  useEffect(() => {
    loadMarkets();
  }, [filter]);

  const loadMarkets = async () => {
    setLoading(true);
    try {
      const data = await api.getMarkets(filter || null);
      setMarkets(data);
    } catch (err) {
      console.error('Failed to load markets:', err);
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="flex flex-between flex-center mb-lg">
        <h1>Markets</h1>
        <Link to="/markets/new" className="btn btn-primary">+ Create Market</Link>
      </div>

      <div className="flex gap-sm mb-lg">
        {['OPEN', 'CLOSED', 'RESOLVED', ''].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`btn btn-sm ${filter === status ? 'btn-primary' : 'btn-secondary'}`}
          >
            {status || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center"><span className="spinner"></span></div>
      ) : markets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <p>No markets found</p>
          <Link to="/markets/new" className="btn btn-primary mt-md">Create the first one</Link>
        </div>
      ) : (
        <div className="grid grid-2">
          {markets.map((market) => (
            <MarketCard key={market.id} market={market} onClick={() => navigate(`/markets/${market.id}`)} />
          ))}
        </div>
      )}
    </div>
  );
}

function MarketCard({ market, onClick }) {
  const yesPrice = market.yes_ask || market.yes_bid || 0.50;
  const noPrice = market.no_ask || market.no_bid || 0.50;

  return (
    <div className="card market-card" onClick={onClick}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <span className={`market-status market-status-${market.status.toLowerCase()}`}>{market.status}</span>
        {market.resolved_outcome !== null && (
          <span className={market.resolved_outcome ? 'text-green' : 'text-red'}>
            {market.resolved_outcome ? 'YES' : 'NO'} Won
          </span>
        )}
      </div>
      <p className="market-question">{market.question}</p>
      <div className="market-prices">
        <div className="market-price">
          <div className="market-price-label">YES</div>
          <div className="market-price-value market-price-yes">{(yesPrice * 100).toFixed(0)}¢</div>
        </div>
        <div className="market-price">
          <div className="market-price-label">NO</div>
          <div className="market-price-value market-price-no">{(noPrice * 100).toFixed(0)}¢</div>
        </div>
      </div>
    </div>
  );
}

export default MarketsPage;
