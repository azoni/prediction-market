import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

function CreateMarketPage() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await api.createMarket({ question, description: description || null });
      if (result.achievements_earned?.length > 0) {
        console.log('Achievements earned:', result.achievements_earned);
      }
      navigate(`/markets/${result.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h1 className="mb-lg">Create Market</h1>

      <form onSubmit={handleSubmit} className="card">
        <div className="input-group">
          <label className="input-label">Question *</label>
          <input
            type="text"
            className="input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Will it rain tomorrow?"
            minLength={10}
            maxLength={500}
            required
          />
          <div className="text-muted mt-sm" style={{ fontSize: '0.75rem' }}>
            Ask a yes/no question. Be specific about how it will be resolved.
          </div>
        </div>

        <div className="input-group">
          <label className="input-label">Description / Resolution Criteria</label>
          <textarea
            className="input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="This market resolves YES if... NO if..."
            rows={4}
            maxLength={2000}
          />
        </div>

        {error && <div className="text-red mb-md">{error}</div>}

        <div className="flex gap-md">
          <button type="button" onClick={() => navigate('/markets')} className="btn btn-secondary">Cancel</button>
          <button type="submit" disabled={loading || question.length < 10} className="btn btn-primary" style={{ flex: 1 }}>
            {loading ? <span className="spinner"></span> : 'Create Market'}
          </button>
        </div>
      </form>

      <div className="card mt-lg">
        <h3 className="card-title mb-md">Tips for good markets</h3>
        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)' }}>
          <li>Be specific about what counts as YES vs NO</li>
          <li>Set a clear timeframe ("by end of 2024")</li>
          <li>Questions about your friend group are fun!</li>
          <li>Avoid ambiguous outcomes</li>
        </ul>
      </div>
    </div>
  );
}

export default CreateMarketPage;
