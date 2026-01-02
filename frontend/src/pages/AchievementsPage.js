import React, { useState, useEffect } from 'react';
import api from '../services/api';

function AchievementsPage() {
  const [achievements, setAchievements] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [achievementsData, statsData] = await Promise.all([
          api.getAchievements(),
          api.getRewardStats(),
        ]);
        setAchievements(achievementsData);
        setStats(statsData);
      } catch (err) {
        console.error('Failed to load achievements:', err);
      }
      setLoading(false);
    };
    loadData();
  }, []);

  const earnedCount = achievements.filter(a => a.earned).length;
  const totalRewards = achievements.filter(a => a.earned).reduce((sum, a) => sum + a.reward, 0);
  const categories = [...new Set(achievements.map(a => a.category))];

  return (
    <div>
      <h1 className="mb-lg">Achievements</h1>

      {stats && (
        <div className="grid grid-3 mb-lg">
          <div className="card">
            <div className="text-muted mb-sm">Earned</div>
            <div className="text-mono" style={{ fontSize: '1.5rem' }}>
              <span className="text-purple">{earnedCount}</span>
              <span className="text-muted"> / {achievements.length}</span>
            </div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">Login Streak</div>
            <div className="text-mono" style={{ fontSize: '1.5rem', color: 'var(--accent-yellow)' }}>
              🔥 {stats.login_streak} days
            </div>
          </div>
          <div className="card">
            <div className="text-muted mb-sm">From Achievements</div>
            <div className="text-mono" style={{ fontSize: '1.5rem', color: 'var(--accent-green)' }}>
              +{totalRewards.toFixed(0)} DC
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center"><span className="spinner"></span></div>
      ) : (
        <div>
          {categories.map(category => (
            <div key={category} className="mb-lg">
              <h2 className="mb-md" style={{ textTransform: 'capitalize' }}>{category}</h2>
              <div className="grid grid-2">
                {achievements.filter(a => a.category === category).map(achievement => (
                  <div key={achievement.id} className={`achievement ${achievement.earned ? 'earned' : 'locked'}`}>
                    <div className="achievement-icon">{achievement.icon}</div>
                    <div className="achievement-info">
                      <div className="achievement-name">{achievement.name}</div>
                      <div className="achievement-description">{achievement.description}</div>
                    </div>
                    <div className="achievement-reward">+{achievement.reward} DC</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AchievementsPage;
