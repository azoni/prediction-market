import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function LeaderboardPage() {
  const { user } = useAuth();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadLeaderboard = async () => {
      try {
        const data = await api.getLeaderboard(50);
        setLeaderboard(data);
      } catch (err) {
        console.error('Failed to load leaderboard:', err);
      }
      setLoading(false);
    };
    loadLeaderboard();
  }, []);

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h1 className="mb-lg">Leaderboard</h1>

      {loading ? (
        <div className="text-center"><span className="spinner"></span></div>
      ) : leaderboard.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏆</div>
          <p>No rankings yet</p>
          <p className="text-muted">Trade on markets to climb the leaderboard!</p>
        </div>
      ) : (
        <div>
          {leaderboard.map((entry) => (
            <div
              key={entry.user_id}
              className={`leaderboard-row ${entry.user_id === user?.id ? 'card' : ''}`}
              style={entry.user_id === user?.id ? { borderColor: 'var(--accent-cyan)' } : {}}
            >
              <div className="leaderboard-rank">
                {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : `#${entry.rank}`}
              </div>
              <div className="leaderboard-name">
                {entry.display_name}
                {entry.user_id === user?.id && <span className="text-cyan"> (you)</span>}
              </div>
              <div className="leaderboard-stats">
                <span className="text-green">{entry.balance.toFixed(0)} DC</span>
                <span className="text-muted" style={{ fontSize: '0.75rem', marginLeft: '0.5rem' }}>
                  {entry.total_trades} trades
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card mt-lg">
        <h3 className="card-title mb-md">How it works</h3>
        <p className="text-muted">
          Rankings are based on realized P&L - profits from markets that have resolved.
          Unrealized gains from open positions don't count until the market resolves.
        </p>
      </div>
    </div>
  );
}

export default LeaderboardPage;
