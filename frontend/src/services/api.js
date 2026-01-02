import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: { 'Content-Type': 'application/json' },
    });
    this.authToken = null;

    this.client.interceptors.request.use((config) => {
      if (this.authToken) {
        config.headers.Authorization = `Bearer ${this.authToken}`;
      }
      return config;
    });
  }

  setAuthToken(token) {
    this.authToken = token;
  }

  // Users
  async registerUser(data) {
    const response = await this.client.post('/users', data);
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/users/me');
    return response.data;
  }

  // Markets
  async getMarkets(status = null) {
    const params = status ? { status } : {};
    const response = await this.client.get('/markets', { params });
    return response.data;
  }

  async getMarket(marketId) {
    const response = await this.client.get(`/markets/${marketId}`);
    return response.data;
  }

  async createMarket(data) {
    const response = await this.client.post('/markets', data);
    return response.data;
  }

  async resolveMarket(marketId, outcome) {
    const response = await this.client.post(`/markets/${marketId}/resolve`, { outcome });
    return response.data;
  }

  // Orders
  async placeOrder(data) {
    const response = await this.client.post('/orders', data);
    return response.data;
  }

  async getOrders(status = null) {
    const params = status ? { status } : {};
    const response = await this.client.get('/orders', { params });
    return response.data;
  }

  async cancelOrder(orderId) {
    const response = await this.client.delete(`/orders/${orderId}`);
    return response.data;
  }

  // Positions
  async getPositions() {
    const response = await this.client.get('/positions');
    return response.data;
  }

  async getPosition(marketId) {
    const response = await this.client.get(`/positions/${marketId}`);
    return response.data;
  }

  // Leaderboard
  async getLeaderboard(limit = 10) {
    const response = await this.client.get('/leaderboard', { params: { limit } });
    return response.data;
  }

  // Rewards
  async claimDailyReward() {
    const response = await this.client.post('/rewards/daily');
    return response.data;
  }

  async getAchievements() {
    const response = await this.client.get('/rewards/achievements');
    return response.data;
  }

  async getMyAchievements() {
    const response = await this.client.get('/rewards/achievements/me');
    return response.data;
  }

  async getRewardStats() {
    const response = await this.client.get('/rewards/stats');
    return response.data;
  }
}

const api = new ApiService();
export default api;
