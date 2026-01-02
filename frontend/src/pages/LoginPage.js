import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

function LoginPage() {
  const { signInWithGoogle, error } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      await signInWithGoogle();
    } catch (err) {
      console.error('Login failed:', err);
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card card">
        <h1 className="login-title">DuMarket</h1>
        <p className="login-subtitle">
          Prediction market for friends. Trade on anything, earn DuCoins, and prove you're the best forecaster.
        </p>

        <button onClick={handleLogin} disabled={loading} className="btn btn-primary btn-lg" style={{ width: '100%' }}>
          {loading ? <><span className="spinner"></span> Signing in...</> : '🚀 Sign in with Google'}
        </button>

        {error && <p className="text-red mt-md">{error}</p>}

        <div className="mt-lg text-muted" style={{ fontSize: '0.875rem' }}>
          <p>✨ 1,000 DuCoins on sign up</p>
          <p>📅 Daily login rewards</p>
          <p>🏆 Achievements & leaderboards</p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
