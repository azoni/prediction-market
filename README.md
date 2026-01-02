# DuMarket

A prediction market platform for friends. Create markets, trade YES/NO shares, and see who's the best forecaster.

## Quick Start (Local Development)

### Step 1: Set up Firebase (Required for Auth)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project (or use existing)
3. Go to **Authentication** → **Sign-in method** → Enable **Google**
4. Go to **Project Settings** → **Your apps** → Click **Web** icon
5. Register your app and copy the config values

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server (uses SQLite locally)
uvicorn main:app --reload --port 8000
```

Backend will be running at `http://localhost:8000`

### Step 3: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_FIREBASE_API_KEY=your-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
REACT_APP_FIREBASE_APP_ID=your-app-id
EOF

# Run the dev server
npm start
```

Frontend will be running at `http://localhost:3000`

### Step 4: Test It!

1. Open `http://localhost:3000`
2. Click "Sign in with Google"
3. Create a market
4. Place some trades!

---

## Project Structure

```
dumarket/
├── .gitignore
├── README.md
│
├── backend/
│   ├── requirements.txt      # Python dependencies
│   ├── main.py               # FastAPI entry point
│   ├── database.py           # DB connection
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py         # SQLAlchemy models
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── order_book.py     # Order book data structures
│   │   └── matcher.py        # Matching engine
│   │
│   ├── market_maker/
│   │   ├── __init__.py
│   │   └── bot.py            # Automated market maker
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── positions.py      # Position tracking
│   │   ├── settlement.py     # Market resolution
│   │   └── rewards.py        # Daily bonus & achievements
│   │
│   └── api/
│       ├── __init__.py
│       └── routes.py         # All API endpoints
│
└── frontend/
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── index.js
        ├── index.css          # Cyberpunk theme
        ├── App.js
        ├── firebase.js
        ├── context/
        │   └── AuthContext.js
        ├── services/
        │   └── api.js
        └── pages/
            ├── LoginPage.js
            ├── MarketsPage.js
            ├── MarketDetailPage.js
            ├── CreateMarketPage.js
            ├── PortfolioPage.js
            ├── LeaderboardPage.js
            └── AchievementsPage.js
```

---

## Features

- **Create Markets** - Ask any yes/no question
- **Trade** - Buy/sell shares with limit or market orders
- **Order Book** - Real order book with price-time priority
- **Market Maker Bot** - Always provides liquidity
- **Daily Rewards** - 50+ DuCoins per day with streak bonuses
- **Achievements** - Earn rewards for milestones
- **Leaderboard** - Compete with friends

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users` | POST | Register user |
| `/api/users/me` | GET | Current user info |
| `/api/markets` | GET | List markets |
| `/api/markets` | POST | Create market |
| `/api/markets/{id}` | GET | Market detail + order book |
| `/api/markets/{id}/resolve` | POST | Resolve market |
| `/api/orders` | POST | Place order |
| `/api/orders` | GET | User's orders |
| `/api/orders/{id}` | DELETE | Cancel order |
| `/api/positions` | GET | User positions |
| `/api/leaderboard` | GET | Top traders |
| `/api/rewards/daily` | POST | Claim daily bonus |
| `/api/rewards/achievements` | GET | All achievements |

---

## Deployment

**Backend (Render):**
1. Create Web Service from GitHub repo
2. Set root directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `DATABASE_URL` (from Render PostgreSQL)

**Frontend (Netlify):**
1. Connect GitHub repo
2. Set base directory: `frontend`
3. Build command: `npm run build`
4. Publish directory: `frontend/build`
5. Add environment variables (Firebase config + API URL)

---

## License

MIT
