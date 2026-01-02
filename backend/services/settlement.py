from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Market, Order, Position, User, MarketStatus, OrderStatus


@dataclass
class SettlementResult:
    user_id: str
    market_id: str
    winning_shares: int
    losing_shares: int
    payout: float
    winning_cost_basis: float
    losing_cost_basis: float
    profit_loss: float
    new_balance: float


@dataclass
class MarketSettlementSummary:
    market_id: str
    outcome: str
    total_payout: float
    positions_settled: int
    results: list[SettlementResult]


def cancel_market_orders(db: Session, market_id: str) -> int:
    open_orders = db.query(Order).filter(
        Order.market_id == market_id,
        Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL])
    ).all()

    count = 0
    for order in open_orders:
        order.status = OrderStatus.CANCELLED
        count += 1

    return count


def settle_position(
    db: Session,
    position: Position,
    winning_side: str,
) -> SettlementResult:
    user = db.query(User).filter(User.id == position.user_id).first()
    if user is None:
        raise ValueError(f"User not found: {position.user_id}")

    if winning_side == "YES":
        winning_shares = position.yes_shares
        losing_shares = position.no_shares
        winning_cost = position.yes_cost_basis
        losing_cost = position.no_cost_basis
    else:
        winning_shares = position.no_shares
        losing_shares = position.yes_shares
        winning_cost = position.no_cost_basis
        losing_cost = position.yes_cost_basis

    payout = winning_shares * 1.00
    profit_from_winners = payout - winning_cost
    loss_from_losers = 0 - losing_cost
    total_pnl = profit_from_winners + loss_from_losers

    user.balance = round(user.balance + payout, 4)
    position.realized_pnl = round(position.realized_pnl + total_pnl, 4)
    position.yes_shares = 0
    position.no_shares = 0
    position.yes_cost_basis = 0.0
    position.no_cost_basis = 0.0

    return SettlementResult(
        user_id=position.user_id,
        market_id=position.market_id,
        winning_shares=winning_shares,
        losing_shares=losing_shares,
        payout=round(payout, 4),
        winning_cost_basis=round(winning_cost, 4),
        losing_cost_basis=round(losing_cost, 4),
        profit_loss=round(total_pnl, 4),
        new_balance=user.balance,
    )


def resolve_market(
    db: Session,
    market_id: str,
    outcome: bool,
    resolver_user_id: Optional[str] = None,
) -> MarketSettlementSummary:
    market = db.query(Market).filter(Market.id == market_id).first()
    if market is None:
        raise ValueError(f"Market not found: {market_id}")

    if market.status == MarketStatus.RESOLVED:
        raise ValueError(f"Market already resolved: {market_id}")

    winning_side = "YES" if outcome else "NO"
    cancelled_count = cancel_market_orders(db, market_id)

    positions = db.query(Position).filter(
        Position.market_id == market_id
    ).all()

    results = []
    total_payout = 0.0

    for position in positions:
        if position.yes_shares == 0 and position.no_shares == 0:
            continue
        result = settle_position(db, position, winning_side)
        results.append(result)
        total_payout += result.payout

    market.status = MarketStatus.RESOLVED
    market.resolved_outcome = outcome
    market.resolved_at = datetime.utcnow()

    return MarketSettlementSummary(
        market_id=market_id,
        outcome=winning_side,
        total_payout=round(total_payout, 4),
        positions_settled=len(results),
        results=results,
    )


def close_market(db: Session, market_id: str) -> int:
    market = db.query(Market).filter(Market.id == market_id).first()
    if market is None:
        raise ValueError(f"Market not found: {market_id}")

    if market.status != MarketStatus.OPEN:
        raise ValueError(f"Market not open: {market_id}")

    cancelled_count = cancel_market_orders(db, market_id)
    market.status = MarketStatus.CLOSED

    return cancelled_count


def get_leaderboard(db: Session, limit: int = 10) -> list[dict]:
    results = db.query(
        Position.user_id,
        func.sum(Position.realized_pnl).label("total_pnl")
    ).group_by(
        Position.user_id
    ).order_by(
        func.sum(Position.realized_pnl).desc()
    ).limit(limit).all()

    leaderboard = []
    for user_id, total_pnl in results:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            leaderboard.append({
                "user_id": user_id,
                "display_name": user.display_name,
                "total_pnl": round(total_pnl or 0, 2),
                "balance": round(user.balance, 2),
            })

    return leaderboard


def get_user_market_history(db: Session, user_id: str) -> list[dict]:
    positions = db.query(Position).filter(
        Position.user_id == user_id
    ).all()

    history = []
    for position in positions:
        market = db.query(Market).filter(Market.id == position.market_id).first()
        if market and market.status == MarketStatus.RESOLVED:
            history.append({
                "market_id": market.id,
                "question": market.question,
                "outcome": "YES" if market.resolved_outcome else "NO",
                "resolved_at": market.resolved_at.isoformat() if market.resolved_at else None,
                "realized_pnl": position.realized_pnl,
            })

    history.sort(key=lambda x: x["resolved_at"] or "", reverse=True)
    return history
