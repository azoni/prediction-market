# =============================================================================
# FriendMarket Data Models
# =============================================================================
# These models represent the core entities in a prediction market:
# - Users who trade
# - Markets (questions to predict)
# - Orders (bids and asks in the order book)
# - Trades (executed transactions between orders)
# - Positions (user holdings in each market)
# =============================================================================

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, 
    ForeignKey, Enum as SQLEnum, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# =============================================================================
# Enums - The building blocks of order book terminology
# =============================================================================

class Side(str, Enum):
    """
    Which outcome the user is trading.
    
    In prediction markets, every question has two outcomes:
    - YES: The event happens
    - NO: The event doesn't happen
    
    Prices for YES and NO should sum to ~$1.00 (enforced by arbitrage)
    Example: "Will it rain tomorrow?" YES=$0.70, NO=$0.30
    """
    YES = "YES"
    NO = "NO"


class OrderType(str, Enum):
    """
    How the order should execute.
    
    LIMIT: Execute only at my price or better. Rests in book if no match.
           "I'll buy YES at $0.45 or less"
    
    MARKET: Execute immediately at best available price.
            "I want YES right now, whatever the price"
    """
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderAction(str, Enum):
    """
    Whether the user is buying or selling shares.
    
    BUY: Acquire shares (costs money, gives you position)
    SELL: Dispose of shares (gives money, reduces position)
    """
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """
    Lifecycle of an order.
    
    OPEN: Resting in the order book, waiting to be filled
    PARTIAL: Some quantity filled, rest still resting
    FILLED: Completely executed, no quantity remaining
    CANCELLED: User cancelled before full fill
    """
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class MarketStatus(str, Enum):
    """
    Lifecycle of a market.
    
    OPEN: Trading is active
    CLOSED: Trading stopped, awaiting resolution
    RESOLVED: Outcome determined, positions settled
    """
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"


# =============================================================================
# User Model
# =============================================================================

class User(Base):
    """
    A participant in the prediction market.
    
    Users have:
    - Balance: FriendCoins available to trade
    - Positions: Holdings in various markets
    - Orders: Active and historical orders
    
    Authentication handled by Firebase, we just store the uid.
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # Firebase UID
    display_name = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    
    # Balance in FriendCoins (virtual currency)
    # New users start with a stake to get trading
    balance = Column(Float, default=1000.0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    positions = relationship("Position", back_populates="user")
    
    # Prevent negative balance at database level
    __table_args__ = (
        CheckConstraint("balance >= 0", name="non_negative_balance"),
    )


# =============================================================================
# Market Model
# =============================================================================

class Market(Base):
    """
    A prediction market - a question with YES/NO outcome.
    
    Examples:
    - "Will the Lakers win tonight?"
    - "Will it snow in December?"
    - "Will Alex finish his project by Friday?"
    
    The market has an order book where users trade YES and NO shares.
    Each share pays out $1.00 if correct, $0.00 if wrong.
    
    Price Discovery:
    If YES trades at $0.65, the market collectively believes 
    there's a 65% chance the event happens.
    """
    __tablename__ = "markets"
    
    id = Column(String, primary_key=True)  # UUID
    
    # The question being predicted
    question = Column(String(500), nullable=False)
    
    # Optional details/rules for resolution
    description = Column(String(2000), nullable=True)
    
    # Who created this market
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    status = Column(SQLEnum(MarketStatus), default=MarketStatus.OPEN)
    
    # Resolution details (filled when market resolves)
    # True = YES wins, False = NO wins, None = not yet resolved
    resolved_outcome = Column(Boolean, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # When trading closes (optional - can also manually close)
    closes_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="market")
    trades = relationship("Trade", back_populates="market")
    positions = relationship("Position", back_populates="market")


# =============================================================================
# Order Model
# =============================================================================

class Order(Base):
    """
    A bid or ask in the order book.
    
    Anatomy of an order:
    - Side: YES or NO (which outcome)
    - Action: BUY or SELL
    - Price: $0.01 to $0.99 (limit orders only)
    - Quantity: How many shares
    
    Example: "BUY 10 YES at $0.45"
    Meaning: "I'll pay up to $0.45 each for 10 YES shares"
    
    Price-Time Priority:
    Orders are matched best-price-first, then earliest-first.
    A $0.50 bid beats a $0.45 bid. If both are $0.50, whoever
    placed their order first gets filled first.
    """
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True)  # UUID
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    
    side = Column(SQLEnum(Side), nullable=False)  # YES or NO
    action = Column(SQLEnum(OrderAction), nullable=False)  # BUY or SELL
    order_type = Column(SQLEnum(OrderType), nullable=False)  # LIMIT or MARKET
    
    # Price per share (0.01 to 0.99)
    # NULL for market orders (they take whatever price is available)
    price = Column(Float, nullable=True)
    
    # Original quantity requested
    quantity = Column(Integer, nullable=False)
    
    # How many shares have been filled so far
    filled_quantity = Column(Integer, default=0, nullable=False)
    
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.OPEN)
    
    # Is this order from the market maker bot?
    # Helps distinguish system liquidity from real users
    is_market_maker = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    market = relationship("Market", back_populates="orders")
    
    # Constraints
    __table_args__ = (
        # Price must be between $0.01 and $0.99 for limit orders
        CheckConstraint(
            "(order_type = 'MARKET') OR (price >= 0.01 AND price <= 0.99)",
            name="valid_limit_price"
        ),
        # Quantity must be positive
        CheckConstraint("quantity > 0", name="positive_quantity"),
        # Can't fill more than ordered
        CheckConstraint("filled_quantity <= quantity", name="valid_fill"),
    )
    
    @property
    def remaining_quantity(self) -> int:
        """Shares still waiting to be filled."""
        return self.quantity - self.filled_quantity


# =============================================================================
# Trade Model
# =============================================================================

class Trade(Base):
    """
    An executed transaction - when two orders match.
    
    Every trade has:
    - A buyer and a seller
    - A price (where they met)
    - A quantity (shares exchanged)
    
    Trades are the source of truth for:
    - Price history (charts, last trade price)
    - Volume statistics
    - Position changes
    
    Note: buyer_order and seller_order might include the market maker.
    """
    __tablename__ = "trades"
    
    id = Column(String, primary_key=True)  # UUID
    
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    
    # The two orders that matched
    buyer_order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    seller_order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    
    # Which outcome was traded
    side = Column(SQLEnum(Side), nullable=False)  # YES or NO
    
    # Execution details
    price = Column(Float, nullable=False)  # Price per share
    quantity = Column(Integer, nullable=False)  # Shares exchanged
    
    # Total value = price * quantity
    # Stored for convenience in calculating volume
    total = Column(Float, nullable=False)
    
    executed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    market = relationship("Market", back_populates="trades")


# =============================================================================
# Position Model
# =============================================================================

class Position(Base):
    """
    A user's holdings in a specific market.
    
    Each user can hold:
    - YES shares: Pay $1 if YES wins, $0 if NO wins
    - NO shares: Pay $1 if NO wins, $0 if YES wins
    
    You can hold both YES and NO (though it's usually not optimal).
    
    P&L Calculation:
    - Cost basis: What you paid for your shares (avg price * quantity)
    - Current value: Current price * quantity
    - Unrealized P&L: Current value - cost basis
    - Realized P&L: Calculated when you sell or market resolves
    
    Example:
    You bought 100 YES at $0.40 (cost: $40)
    YES now trades at $0.60 (value: $60)
    Unrealized P&L: +$20
    """
    __tablename__ = "positions"
    
    id = Column(String, primary_key=True)  # UUID
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    
    # Share holdings (can be 0 if fully sold)
    yes_shares = Column(Integer, default=0, nullable=False)
    no_shares = Column(Integer, default=0, nullable=False)
    
    # Average price paid per share (for P&L calculation)
    # Updates with each purchase using weighted average
    yes_avg_price = Column(Float, default=0.0, nullable=False)
    no_avg_price = Column(Float, default=0.0, nullable=False)
    
    # Total cost basis (what you've spent)
    yes_cost_basis = Column(Float, default=0.0, nullable=False)
    no_cost_basis = Column(Float, default=0.0, nullable=False)
    
    # Realized P&L from closed trades in this market
    realized_pnl = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    market = relationship("Market", back_populates="positions")
    
    # Constraints
    __table_args__ = (
        # Can't have negative shares
        CheckConstraint("yes_shares >= 0", name="non_negative_yes"),
        CheckConstraint("no_shares >= 0", name="non_negative_no"),
    )


# =============================================================================
# Summary
# =============================================================================
# 
# Data flow when a trade happens:
# 
# 1. User submits Order (BUY YES at $0.50)
# 2. Matching engine finds opposing Order (SELL YES at $0.50)
# 3. Trade record created (price=$0.50, quantity=matched amount)
# 4. Both Orders updated (filled_quantity increases, status may change)
# 5. Both users' Positions updated (shares added/removed, avg price recalculated)
# 6. Both users' balances updated (buyer pays, seller receives)
#
# When market resolves:
# 1. Market status -> RESOLVED, resolved_outcome set
# 2. All open Orders cancelled
# 3. Winning shares pay out $1.00 each
# 4. Losing shares pay out $0.00
# 5. User balances credited, realized_pnl updated
# =============================================================================