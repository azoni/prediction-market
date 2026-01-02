from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine, SessionLocal
from models import Base, User
from api import router
from market_maker import MarketMakerBot

app = FastAPI(title="DuMarket API", version="1.0.0")

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://dumarket.netlify.app",
    # Add your Netlify preview URLs if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def on_startup():
    """Initialize database tables and seed data on startup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create market maker bot user if it doesn't exist
    db = SessionLocal()
    try:
        bot_user = db.query(User).filter(User.id == MarketMakerBot.USER_ID).first()
        if not bot_user:
            bot_user = User(
                id=MarketMakerBot.USER_ID,
                display_name="Market Maker",
                email=None,
                balance=0.0,  # Bot doesn't need balance
            )
            db.add(bot_user)
            db.commit()
            print(f"Created market maker bot user: {MarketMakerBot.USER_ID}")
        else:
            print(f"Market maker bot user already exists: {MarketMakerBot.USER_ID}")
    finally:
        db.close()
    
    # Initialize auth system
    from auth import init_auth
    init_auth()


@app.get("/health")
def health_check():
    return {"status": "healthy"}