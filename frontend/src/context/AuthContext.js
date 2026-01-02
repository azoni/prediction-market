import React, { createContext, useContext, useState, useEffect } from 'react';
import { signInWithPopup, signOut as firebaseSignOut, onAuthStateChanged } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          // Get Firebase ID token for secure API requests
          const token = await firebaseUser.getIdToken();
          api.setAuthToken(token);

          // Register/get user from our backend
          const userData = await api.registerUser({
            firebase_uid: firebaseUser.uid,
            display_name: firebaseUser.displayName || 'Anonymous',
            email: firebaseUser.email,
          });

          // Try to claim daily reward
          try {
            const dailyReward = await api.claimDailyReward();
            if (!dailyReward.already_claimed) {
              console.log('Daily reward claimed:', dailyReward.total_reward);
            }
            const freshUser = await api.getCurrentUser();
            setUser(freshUser);
          } catch (err) {
            console.error('Failed to claim daily reward:', err);
            setUser(userData);
          }
        } catch (err) {
          console.error('Failed to register user:', err);
          setError(err.message);
          setUser(null);
        }
      } else {
        api.setAuthToken(null);
        setUser(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Refresh the token periodically (Firebase tokens expire after 1 hour)
  useEffect(() => {
    if (!user) return;
    
    const refreshToken = async () => {
      try {
        const firebaseUser = auth.currentUser;
        if (firebaseUser) {
          const token = await firebaseUser.getIdToken(true); // force refresh
          api.setAuthToken(token);
        }
      } catch (err) {
        console.error('Token refresh failed:', err);
      }
    };

    // Refresh token every 50 minutes (tokens expire at 60 min)
    const interval = setInterval(refreshToken, 50 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user]);

  const signInWithGoogle = async () => {
    setError(null);
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const signOut = async () => {
    try {
      await firebaseSignOut(auth);
      setUser(null);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const refreshUser = async () => {
    try {
      const userData = await api.getCurrentUser();
      setUser(userData);
    } catch (err) {
      console.error('Failed to refresh user:', err);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, signInWithGoogle, signOut, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
