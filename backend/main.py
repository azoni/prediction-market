from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine, SessionLocal
from models import Base, User, Order, OrderStatus
from api import router
from api.routes import matching_engine
from market_maker import MarketMakerBot

app = FastAPI(title="DuMarket API", version="1.0.0")

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://dumarket.netlify.app",
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
    
    db = SessionLocal()
    try:
        # Create market maker bot user if it doesn't exist
        bot_user = db.query(User).filter(User.id == MarketMakerBot.USER_ID).first()
        if not bot_user:
            bot_user = User(
                id=MarketMakerBot.USER_ID,
                display_name="Market Maker",
                email=None,
                balance=0.0,
            )
            db.add(bot_user)
            db.commit()
            print(f"Created market maker bot user: {MarketMakerBot.USER_ID}")
        
        # Rebuild order book from open orders in database
        open_orders = db.query(Order).filter(
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL])
        ).all()
        
        rebuilt_count = 0
        for order in open_orders:
            remaining_qty = order.quantity - order.filled_quantity
            if remaining_qty > 0 and order.price is not None:
                try:
                    matching_engine.process_order(
                        market_id=order.market_id,
                        order_id=order.id,
                        user_id=order.user_id,
                        side=order.side.value,
                        action=order.action.value,
                        order_type="LIMIT",
                        quantity=remaining_qty,
                        price=order.price,
                        is_market_maker=order.is_market_maker,
                    )
                    rebuilt_count += 1
                except Exception as e:
                    print(f"Failed to rebuild order {order.id}: {e}")
        
        print(f"Rebuilt {rebuilt_count} orders into order book")
        
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "healthy"}