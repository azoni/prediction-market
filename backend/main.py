from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from database import init_db, SessionLocal
from services import seed_achievements
from auth import setup_auth

app = FastAPI(
    title="DuMarket",
    description="Prediction market for friends",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://dumarket.netlify.app",
        # Add your Netlify domain when you deploy
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def startup():
    # Initialize Firebase Admin SDK for auth
    setup_auth()
    
    # Initialize database tables
    init_db()
    
    # Seed achievements
    db = SessionLocal()
    try:
        count = seed_achievements(db)
        if count > 0:
            print(f"Seeded {count} achievements")
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "app": "DuMarket"}
