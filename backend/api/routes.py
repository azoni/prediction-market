from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, Market, Order, Trade, Position,
    Side, OrderType, OrderAction, OrderStatus, MarketStatus
)
from engine import MatchingEngine, TradeResult
from market_maker import MarketMakerBot, MarketMakerConfig
from services import (
    process_trade_for_positions,
    get_user_positions,
    resolve_market,
    get_leaderboard,
    process_daily_login,
    check_trading_achievements,
    check_market_creation_achievements,
    get_user_achievements,
    get_all_achievements,
    cancel_market_orders,
)
from auth import get_current_user, get_current_admin, is_admin, verify_firebase_token

router = APIRouter()

# Shared instances
matching_engine = MatchingEngine()
market_maker = MarketMakerBot(MarketMakerConfig(spread=0.06, base_size=100, max_inventory=1000))


# =============================================================================
# Request/Response Models
# =============================================================================

class UserCreate(BaseModel):
    firebase_uid: str
    display_name: str
    email: Optional[str] = None


class MarketCreate(BaseModel):
    question: str = Field(..., min_length=10, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    closes_at: Optional[datetime] = None


class MarketUpdate(BaseModel):
    """For admin edits to markets."""
    question: Optional[str] = Field(None, min_length=10, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    closes_at: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(OPEN|CLOSED)$")


class OrderCreate(BaseModel):
    market_id: str
    side: str = Field(..., pattern="^(YES|NO)$")
    action: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field(..., pattern="^(LIMIT|MARKET)$")
    quantity: int = Field(..., gt=0, le=10000)
    price: Optional[float] = Field(None, ge=0.01, le=0.99)


class ResolveRequest(BaseModel):
    outcome: bool


class AdminBalanceAdjust(BaseModel):
    """For admin balance adjustments."""
    user_id: str
    amount: float = Field(..., ge=-100000, le=100000)
    reason: str = Field(..., min_length=3, max_length=200)


# Note: get_current_user is now imported from auth.py
# It properly verifies Firebase tokens in production


# =============================================================================
# User Endpoints
# =============================================================================

@router.post("/users")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.id == user_data.firebase_uid).first()
    if existing:
        return {
            "id": existing.id,
            "display_name": existing.display_name,
            "email": existing.email,
            "balance": existing.balance,
        }

    user = User(
        id=user_data.firebase_uid,
        display_name=user_data.display_name,
        email=user_data.email,
        balance=1000.0,
    )
    db.add(user)
    db.commit()

    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "balance": user.balance,
    }


@router.get("/users/me")
def get_current_user_info(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "balance": user.balance,
        "login_streak": user.login_streak,
        "total_trades": user.total_trades,
    }


# =============================================================================
# Market Endpoints
# =============================================================================

@router.get("/markets")
def list_markets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Market)
    if status:
        query = query.filter(Market.status == MarketStatus(status))
    markets = query.order_by(Market.created_at.desc()).limit(50).all()

    results = []
    for market in markets:
        snapshot = matching_engine.get_book_snapshot(market.id)
        results.append({
            "id": market.id,
            "question": market.question,
            "status": market.status.value,
            "created_at": market.created_at,
            "yes_price": snapshot["yes"]["best_bid"],
            "no_price": snapshot["no"]["best_bid"],
            "resolved_outcome": market.resolved_outcome,
        })

    return results


@router.post("/markets")
def create_market(
    market_data: MarketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    market_id = str(uuid4())

    market = Market(
        id=market_id,
        question=market_data.question,
        description=market_data.description,
        creator_id=user.id,
        status=MarketStatus.OPEN,
        closes_at=market_data.closes_at,
    )
    db.add(market)

    user.total_markets_created += 1
    achievements = check_market_creation_achievements(db, user)

    db.commit()

    # Initialize market maker quotes and save to database
    _initialize_market_maker_orders(market_id, db)

    return {
        "id": market_id,
        "message": "Market created",
        "achievements_earned": achievements,
    }


@router.get("/markets/{market_id}")
def get_market(market_id: str, db: Session = Depends(get_db)):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Ensure market maker has liquidity on this market
    if market.status == MarketStatus.OPEN:
        _refresh_market_maker_quotes(market_id, db)

    book_snapshot = matching_engine.get_book_snapshot(market_id)

    recent_trades = db.query(Trade).filter(
        Trade.market_id == market_id
    ).order_by(Trade.executed_at.desc()).limit(20).all()

    return {
        "market": {
            "id": market.id,
            "question": market.question,
            "description": market.description,
            "creator_id": market.creator_id,
            "status": market.status.value,
            "resolved_outcome": market.resolved_outcome,
            "resolved_at": market.resolved_at,
            "closes_at": market.closes_at,
            "created_at": market.created_at,
        },
        "order_book": book_snapshot,
        "recent_trades": [
            {
                "id": t.id,
                "side": t.side.value,
                "price": t.price,
                "quantity": t.quantity,
                "executed_at": t.executed_at,
            }
            for t in recent_trades
        ],
    }


@router.post("/markets/{market_id}/resolve")
def resolve_market_endpoint(
    market_id: str,
    resolve_data: ResolveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    if market.creator_id != user.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="Only creator can resolve")

    if market.status == MarketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Market already resolved")

    summary = resolve_market(db, market_id, resolve_data.outcome)
    db.commit()

    return {
        "message": "Market resolved",
        "outcome": summary.outcome,
        "total_payout": summary.total_payout,
        "positions_settled": summary.positions_settled,
    }


# =============================================================================
# Order Endpoints
# =============================================================================

@router.post("/orders")
def place_order(
    order_data: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    market = db.query(Market).filter(Market.id == order_data.market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if market.status != MarketStatus.OPEN:
        raise HTTPException(status_code=400, detail="Market not open for trading")

    if order_data.order_type == "LIMIT" and order_data.price is None:
        raise HTTPException(status_code=400, detail="Limit orders require price")

    if order_data.action == "BUY":
        max_cost = order_data.quantity * (order_data.price or 0.99)
        if user.balance < max_cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Need ${max_cost:.2f}, have ${user.balance:.2f}"
            )
    else:
        position = db.query(Position).filter(
            Position.user_id == user.id,
            Position.market_id == order_data.market_id
        ).first()

        if order_data.side == "YES":
            shares = position.yes_shares if position else 0
        else:
            shares = position.no_shares if position else 0

        if shares < order_data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient shares. Have {shares}, need {order_data.quantity}"
            )

    order_id = str(uuid4())
    order = Order(
        id=order_id,
        user_id=user.id,
        market_id=order_data.market_id,
        side=Side(order_data.side),
        action=OrderAction(order_data.action),
        order_type=OrderType(order_data.order_type),
        price=order_data.price,
        quantity=order_data.quantity,
        filled_quantity=0,
        status=OrderStatus.OPEN,
    )
    db.add(order)
    db.flush()  # Get the order ID into the database before matching

    result = matching_engine.process_order(
        market_id=order_data.market_id,
        order_id=order_id,
        user_id=user.id,
        side=order_data.side,
        action=order_data.action,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price,
    )

    for trade_result in result.trades:
        _process_trade(db, trade_result, user)

    achievements_earned = []
    if result.trades:
        user.total_trades += len(result.trades)
        achievements_earned = check_trading_achievements(db, user)

    order.filled_quantity = result.filled_quantity
    if result.fully_filled:
        order.status = OrderStatus.FILLED
    elif result.filled_quantity > 0:
        order.status = OrderStatus.PARTIAL
    elif order_data.order_type == "MARKET":
        # Market orders that don't fill should be cancelled, not left open
        order.status = OrderStatus.CANCELLED

    db.commit()

    return {
        "order_id": order_id,
        "status": order.status.value,
        "filled_quantity": result.filled_quantity,
        "remaining_quantity": result.remaining_quantity,
        "trades": len(result.trades),
        "average_price": result.average_price,
        "achievements_earned": achievements_earned,
    }


@router.delete("/orders/{order_id}")
def cancel_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status not in [OrderStatus.OPEN, OrderStatus.PARTIAL]:
        raise HTTPException(status_code=400, detail="Order not cancellable")

    # Try to remove from in-memory order book (may not exist if server restarted)
    if order.price is not None:
        matching_engine.cancel_order(
            market_id=order.market_id,
            order_id=order_id,
            side=order.side.value,
            action=order.action.value,
            price=order.price,
        )

    # Always update database status
    order.status = OrderStatus.CANCELLED
    db.commit()
    return {"message": "Order cancelled"}


@router.get("/orders")
def get_user_orders(
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Order).filter(Order.user_id == user.id)
    if status:
        query = query.filter(Order.status == OrderStatus(status))
    orders = query.order_by(Order.created_at.desc()).limit(100).all()

    return [
        {
            "id": o.id,
            "market_id": o.market_id,
            "side": o.side.value,
            "action": o.action.value,
            "order_type": o.order_type.value,
            "price": o.price,
            "quantity": o.quantity,
            "filled_quantity": o.filled_quantity,
            "status": o.status.value,
            "created_at": o.created_at,
        }
        for o in orders
    ]


# =============================================================================
# Position Endpoints
# =============================================================================

@router.get("/positions")
def get_positions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def price_getter(market_id: str):
        snapshot = matching_engine.get_book_snapshot(market_id)
        yes_price = snapshot["yes"]["best_bid"] or 0.5
        no_price = snapshot["no"]["best_bid"] or 0.5
        return yes_price, no_price

    positions = get_user_positions(db, user.id, price_getter)

    results = []
    for pos in positions:
        market = db.query(Market).filter(Market.id == pos.market_id).first()
        results.append({
            "market_id": pos.market_id,
            "question": market.question if market else "Unknown",
            "market_status": market.status.value if market else "UNKNOWN",
            "yes_shares": pos.yes_shares,
            "no_shares": pos.no_shares,
            "yes_avg_price": pos.yes_avg_price,
            "no_avg_price": pos.no_avg_price,
            "yes_current_value": pos.yes_current_value,
            "no_current_value": pos.no_current_value,
            "unrealized_pnl": pos.unrealized_pnl,
            "realized_pnl": pos.realized_pnl,
        })

    return results


@router.get("/positions/{market_id}")
def get_position(
    market_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    position = db.query(Position).filter(
        Position.user_id == user.id,
        Position.market_id == market_id
    ).first()

    if not position:
        return {
            "market_id": market_id,
            "yes_shares": 0,
            "no_shares": 0,
            "yes_avg_price": 0,
            "no_avg_price": 0,
            "unrealized_pnl": 0,
            "realized_pnl": 0,
        }

    snapshot = matching_engine.get_book_snapshot(market_id)
    yes_price = snapshot["yes"]["best_bid"] or 0.5
    no_price = snapshot["no"]["best_bid"] or 0.5

    yes_value = position.yes_shares * yes_price
    no_value = position.no_shares * no_price
    total_cost = position.yes_cost_basis + position.no_cost_basis
    unrealized = (yes_value + no_value) - total_cost

    return {
        "market_id": market_id,
        "yes_shares": position.yes_shares,
        "no_shares": position.no_shares,
        "yes_avg_price": position.yes_avg_price,
        "no_avg_price": position.no_avg_price,
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": position.realized_pnl,
    }


# =============================================================================
# Leaderboard
# =============================================================================

@router.get("/leaderboard")
def leaderboard(limit: int = 50, db: Session = Depends(get_db)):
    return get_leaderboard(db, limit)


# =============================================================================
# Rewards Endpoints
# =============================================================================

@router.post("/rewards/daily")
def claim_daily_reward(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = process_daily_login(db, user)
    db.commit()

    return {
        "already_claimed": result.already_claimed,
        "base_reward": result.base_reward,
        "streak_bonus": result.streak_bonus,
        "total_reward": result.total_reward,
        "login_streak": result.new_streak,
        "new_balance": result.new_balance,
        "achievements_earned": result.achievements_earned,
    }


@router.get("/rewards/achievements")
def list_achievements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_all_achievements(db, user.id)


@router.get("/rewards/achievements/me")
def get_my_achievements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_achievements(db, user.id)


@router.get("/rewards/stats")
def get_reward_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    all_achievements = get_all_achievements(db, user.id)
    earned_achievements = [a for a in all_achievements if a["earned"]]

    return {
        "balance": user.balance,
        "login_streak": user.login_streak,
        "total_trades": user.total_trades,
        "total_markets_created": user.total_markets_created,
        "total_correct_predictions": user.total_correct_predictions,
        "achievements_earned": len(earned_achievements),
        "achievements_total": len(all_achievements),
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _process_trade(db: Session, trade_result: TradeResult, current_user: User):
    """Process a trade result: save trade, update positions, update balances."""
    trade = Trade(
        id=trade_result.trade_id,
        market_id=trade_result.market_id,
        buyer_order_id=trade_result.buyer_order_id,
        seller_order_id=trade_result.seller_order_id,
        side=Side(trade_result.side),
        price=trade_result.price,
        quantity=trade_result.quantity,
        total=trade_result.total,
        executed_at=trade_result.executed_at,
    )
    db.add(trade)

    # Update positions (this function skips market maker internally)
    process_trade_for_positions(
        db, trade, trade_result.buyer_user_id, trade_result.seller_user_id
    )

    # Update buyer balance (deduct cost) - skip market maker
    if trade_result.buyer_user_id != MarketMakerBot.USER_ID:
        buyer = db.query(User).filter(User.id == trade_result.buyer_user_id).first()
        if buyer:
            buyer.balance = round(buyer.balance - trade_result.total, 4)

    # Update seller balance (add proceeds) - skip market maker
    if trade_result.seller_user_id != MarketMakerBot.USER_ID:
        seller = db.query(User).filter(User.id == trade_result.seller_user_id).first()
        if seller:
            seller.balance = round(seller.balance + trade_result.total, 4)

    # Notify market maker of trades it was involved in
    if trade_result.buyer_user_id == MarketMakerBot.USER_ID:
        market_maker.on_trade(
            trade_result.market_id, trade_result.side, "BUY", trade_result.quantity
        )
    if trade_result.seller_user_id == MarketMakerBot.USER_ID:
        market_maker.on_trade(
            trade_result.market_id, trade_result.side, "SELL", trade_result.quantity
        )


def _initialize_market_maker_orders(market_id: str, db: Session):
    """Create initial market maker orders for a new market and save to database."""
    for side in ["YES", "NO"]:
        orders = market_maker.generate_orders(market_id, side)
        for order_params in orders:
            # Save order to database first
            order = Order(
                id=order_params["order_id"],
                user_id=MarketMakerBot.USER_ID,
                market_id=order_params["market_id"],
                side=Side(order_params["side"]),
                action=OrderAction(order_params["action"]),
                order_type=OrderType(order_params["order_type"]),
                price=order_params["price"],
                quantity=order_params["quantity"],
                filled_quantity=0,
                status=OrderStatus.OPEN,
                is_market_maker=True,
            )
            db.add(order)
            
            # Then add to matching engine
            matching_engine.process_order(**order_params)
    
    db.commit()


def _refresh_market_maker_quotes(market_id: str, db: Session):
    """Refresh market maker quotes if spread is too wide."""
    snapshot = matching_engine.get_book_snapshot(market_id)
    
    for side in ["YES", "NO"]:
        book = snapshot["yes"] if side == "YES" else snapshot["no"]
        
        # Add liquidity if spread is too wide or no orders exist
        if book["spread"] is None or book["spread"] > 0.10:
            orders = market_maker.generate_orders(market_id, side)
            for order_params in orders:
                # Check if this order already exists
                existing = db.query(Order).filter(
                    Order.id == order_params["order_id"]
                ).first()
                
                if not existing:
                    # Save order to database first
                    order = Order(
                        id=order_params["order_id"],
                        user_id=MarketMakerBot.USER_ID,
                        market_id=order_params["market_id"],
                        side=Side(order_params["side"]),
                        action=OrderAction(order_params["action"]),
                        order_type=OrderType(order_params["order_type"]),
                        price=order_params["price"],
                        quantity=order_params["quantity"],
                        filled_quantity=0,
                        status=OrderStatus.OPEN,
                        is_market_maker=True,
                    )
                    db.add(order)
                    
                    # Then add to matching engine
                    matching_engine.process_order(**order_params)
            
            db.commit()


# =============================================================================
# Admin Endpoints
# =============================================================================
# These require admin privileges. Add your email to ADMIN_EMAILS in auth.py

@router.get("/admin/status")
def admin_status(admin: User = Depends(get_current_admin)):
    """Check if current user has admin privileges."""
    return {
        "is_admin": True,
        "user_id": admin.id,
        "email": admin.email,
    }


@router.get("/admin/users")
def admin_list_users(
    limit: int = 50,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    return [
        {
            "id": u.id,
            "display_name": u.display_name,
            "email": u.email,
            "balance": u.balance,
            "total_trades": u.total_trades,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/admin/users/{user_id}/adjust-balance")
def admin_adjust_balance(
    user_id: str,
    adjustment: AdminBalanceAdjust,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Adjust a user's balance (admin only).
    
    Use positive amounts to add funds, negative to remove.
    Requires a reason for audit trail.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_balance = target_user.balance
    new_balance = old_balance + adjustment.amount
    
    if new_balance < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot set negative balance. Current: {old_balance}, adjustment: {adjustment.amount}"
        )
    
    target_user.balance = round(new_balance, 2)
    db.commit()
    
    # In production, you'd log this to an audit table
    print(f"ADMIN BALANCE ADJUSTMENT: {admin.email} adjusted {target_user.display_name}'s balance "
          f"from {old_balance} to {new_balance}. Reason: {adjustment.reason}")
    
    return {
        "user_id": user_id,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "adjustment": adjustment.amount,
        "reason": adjustment.reason,
        "adjusted_by": admin.email,
    }


@router.put("/admin/markets/{market_id}")
def admin_update_market(
    market_id: str,
    update: MarketUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a market's details (admin only)."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    if market.status == MarketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Cannot edit resolved market")
    
    if update.question is not None:
        market.question = update.question
    if update.description is not None:
        market.description = update.description
    if update.closes_at is not None:
        market.closes_at = update.closes_at
    if update.status is not None:
        market.status = MarketStatus(update.status)
    
    db.commit()
    
    return {
        "message": "Market updated",
        "market_id": market_id,
    }


@router.delete("/admin/markets/{market_id}")
def admin_delete_market(
    market_id: str,
    refund: bool = True,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a market (admin only).
    
    By default, refunds all users their cost basis for positions in this market.
    Set refund=false to delete without refunding (use carefully).
    """
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    if market.status == MarketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Cannot delete resolved market")
    
    # Cancel all open orders
    cancelled_orders = cancel_market_orders(db, market_id)
    
    # Refund positions if requested
    refund_total = 0.0
    users_refunded = 0
    
    if refund:
        positions = db.query(Position).filter(Position.market_id == market_id).all()
        for position in positions:
            # Refund cost basis
            refund_amount = position.yes_cost_basis + position.no_cost_basis
            if refund_amount > 0:
                user = db.query(User).filter(User.id == position.user_id).first()
                if user:
                    user.balance = round(user.balance + refund_amount, 2)
                    refund_total += refund_amount
                    users_refunded += 1
            
            # Clear position
            position.yes_shares = 0
            position.no_shares = 0
            position.yes_cost_basis = 0
            position.no_cost_basis = 0
    
    # Mark market as closed (we keep the data for history)
    market.status = MarketStatus.CLOSED
    market.description = f"[DELETED BY ADMIN] {market.description or ''}"
    
    db.commit()
    
    # Remove from matching engine
    if market_id in matching_engine.books:
        del matching_engine.books[market_id]
    
    return {
        "message": "Market deleted",
        "market_id": market_id,
        "orders_cancelled": cancelled_orders,
        "users_refunded": users_refunded,
        "total_refunded": refund_total,
    }


@router.post("/admin/markets/{market_id}/resolve")
def admin_resolve_market(
    market_id: str,
    resolve_data: ResolveRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Resolve any market (admin only).
    
    Unlike the regular resolve endpoint, admins can resolve any market,
    not just ones they created.
    """
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    
    if market.status == MarketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Market already resolved")
    
    summary = resolve_market(db, market_id, resolve_data.outcome)
    db.commit()
    
    return {
        "message": "Market resolved by admin",
        "outcome": summary.outcome,
        "total_payout": summary.total_payout,
        "positions_settled": summary.positions_settled,
    }


@router.get("/admin/stats")
def admin_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get platform statistics (admin only)."""
    total_users = db.query(User).count()
    total_markets = db.query(Market).count()
    open_markets = db.query(Market).filter(Market.status == MarketStatus.OPEN).count()
    total_trades = db.query(Trade).count()
    total_orders = db.query(Order).count()
    
    # Sum of all user balances
    from sqlalchemy import func
    total_balance = db.query(func.sum(User.balance)).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_markets": total_markets,
        "open_markets": open_markets,
        "total_trades": total_trades,
        "total_orders": total_orders,
        "total_balance_in_circulation": round(total_balance, 2),
    }