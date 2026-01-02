from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime,
    ForeignKey, Enum as SQLEnum, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================

class Side(str, Enum):
    YES = "YES"
    NO = "NO"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class MarketStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"


class TransactionType(str, Enum):
    SIGNUP_BONUS = "SIGNUP_BONUS"
    DAILY_REWARD = "DAILY_REWARD"
    TRADE_BUY = "TRADE_BUY"
    TRADE_SELL = "TRADE_SELL"
    MARKET_PAYOUT = "MARKET_PAYOUT"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"


# =============================================================================
# Models
# =============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    display_name = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    balance = Column(Float, default=1000.0, nullable=False)

    # Reward tracking
    last_login_date = Column(DateTime, nullable=True)
    login_streak = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    total_markets_created = Column(Integer, default=0)
    total_correct_predictions = Column(Integer, default=0)
    lifetime_earnings = Column(Float, default=0.0)
    lifetime_pnl = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")
    positions = relationship("Position", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

    __table_args__ = (
        CheckConstraint("balance >= 0", name="non_negative_balance"),
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    icon = Column(String(50), nullable=True)
    reward = Column(Float, default=0.0)
    category = Column(String(50), nullable=True)

    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String, ForeignKey("achievements.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


class Market(Base):
    __tablename__ = "markets"

    id = Column(String, primary_key=True)
    question = Column(String(500), nullable=False)
    description = Column(String(2000), nullable=True)
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(MarketStatus), default=MarketStatus.OPEN)
    resolved_outcome = Column(Boolean, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closes_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="market")
    trades = relationship("Trade", back_populates="market")
    positions = relationship("Position", back_populates="market")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    side = Column(SQLEnum(Side), nullable=False)
    action = Column(SQLEnum(OrderAction), nullable=False)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    filled_quantity = Column(Integer, default=0, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.OPEN)
    is_market_maker = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    market = relationship("Market", back_populates="orders")

    __table_args__ = (
        CheckConstraint(
            "(order_type = 'MARKET') OR (price >= 0.01 AND price <= 0.99)",
            name="valid_limit_price"
        ),
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("filled_quantity <= quantity", name="valid_fill"),
    )

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity


class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    buyer_order_id = Column(String, nullable=True)
    seller_order_id = Column(String, nullable=True)
    side = Column(SQLEnum(Side), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)

    market = relationship("Market", back_populates="trades")


class Position(Base):
    __tablename__ = "positions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    yes_shares = Column(Integer, default=0, nullable=False)
    no_shares = Column(Integer, default=0, nullable=False)
    yes_avg_price = Column(Float, default=0.0, nullable=False)
    no_avg_price = Column(Float, default=0.0, nullable=False)
    yes_cost_basis = Column(Float, default=0.0, nullable=False)
    no_cost_basis = Column(Float, default=0.0, nullable=False)
    realized_pnl = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="positions")
    market = relationship("Market", back_populates="positions")

    __table_args__ = (
        CheckConstraint("yes_shares >= 0", name="non_negative_yes"),
        CheckConstraint("no_shares >= 0", name="non_negative_no"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)
    reference_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
