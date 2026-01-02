from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from uuid import uuid4

from models import Position, User, Trade, Side


@dataclass
class PositionUpdate:
    user_id: str
    market_id: str
    side: str
    shares_delta: int
    price: float
    cost_delta: float
    realized_pnl: float


@dataclass
class PositionSummary:
    market_id: str
    yes_shares: int
    no_shares: int
    yes_avg_price: float
    no_avg_price: float
    yes_cost_basis: float
    no_cost_basis: float
    yes_current_value: float
    no_current_value: float
    unrealized_pnl: float
    realized_pnl: float


def get_or_create_position(db: Session, user_id: str, market_id: str) -> Position:
    position = db.query(Position).filter(
        Position.user_id == user_id,
        Position.market_id == market_id
    ).first()

    if position is None:
        position = Position(
            id=str(uuid4()),
            user_id=user_id,
            market_id=market_id,
            yes_shares=0,
            no_shares=0,
            yes_avg_price=0.0,
            no_avg_price=0.0,
            yes_cost_basis=0.0,
            no_cost_basis=0.0,
            realized_pnl=0.0,
        )
        db.add(position)

    return position


def update_position_for_buy(
    position: Position,
    side: str,
    quantity: int,
    price: float,
) -> PositionUpdate:
    cost = quantity * price

    if side == "YES":
        old_shares = position.yes_shares
        old_avg = position.yes_avg_price
        old_cost = position.yes_cost_basis

        new_shares = old_shares + quantity
        if new_shares > 0:
            new_avg = ((old_shares * old_avg) + (quantity * price)) / new_shares
        else:
            new_avg = 0.0
        new_cost = old_cost + cost

        position.yes_shares = new_shares
        position.yes_avg_price = round(new_avg, 4)
        position.yes_cost_basis = round(new_cost, 4)
    else:
        old_shares = position.no_shares
        old_avg = position.no_avg_price
        old_cost = position.no_cost_basis

        new_shares = old_shares + quantity
        if new_shares > 0:
            new_avg = ((old_shares * old_avg) + (quantity * price)) / new_shares
        else:
            new_avg = 0.0
        new_cost = old_cost + cost

        position.no_shares = new_shares
        position.no_avg_price = round(new_avg, 4)
        position.no_cost_basis = round(new_cost, 4)

    return PositionUpdate(
        user_id=position.user_id,
        market_id=position.market_id,
        side=side,
        shares_delta=quantity,
        price=price,
        cost_delta=cost,
        realized_pnl=0.0,
    )


def update_position_for_sell(
    position: Position,
    side: str,
    quantity: int,
    price: float,
) -> PositionUpdate:
    if side == "YES":
        old_shares = position.yes_shares
        old_avg = position.yes_avg_price
        old_cost = position.yes_cost_basis

        if quantity > old_shares:
            raise ValueError(f"Cannot sell {quantity} shares, only own {old_shares}")

        realized = (price - old_avg) * quantity
        new_shares = old_shares - quantity
        cost_reduction = old_avg * quantity
        new_cost = old_cost - cost_reduction

        position.yes_shares = new_shares
        position.yes_cost_basis = round(max(0, new_cost), 4)
        position.realized_pnl = round(position.realized_pnl + realized, 4)

        if new_shares == 0:
            position.yes_avg_price = 0.0
    else:
        old_shares = position.no_shares
        old_avg = position.no_avg_price
        old_cost = position.no_cost_basis

        if quantity > old_shares:
            raise ValueError(f"Cannot sell {quantity} shares, only own {old_shares}")

        realized = (price - old_avg) * quantity
        new_shares = old_shares - quantity
        cost_reduction = old_avg * quantity
        new_cost = old_cost - cost_reduction

        position.no_shares = new_shares
        position.no_cost_basis = round(max(0, new_cost), 4)
        position.realized_pnl = round(position.realized_pnl + realized, 4)

        if new_shares == 0:
            position.no_avg_price = 0.0

    proceeds = quantity * price

    return PositionUpdate(
        user_id=position.user_id,
        market_id=position.market_id,
        side=side,
        shares_delta=-quantity,
        price=price,
        cost_delta=-proceeds,
        realized_pnl=round(realized, 4),
    )


def process_trade_for_positions(
    db: Session,
    trade: Trade,
    buyer_user_id: str,
    seller_user_id: str,
) -> tuple[PositionUpdate, PositionUpdate]:
    side = trade.side.value if isinstance(trade.side, Side) else trade.side

    buyer_position = get_or_create_position(db, buyer_user_id, trade.market_id)
    seller_position = get_or_create_position(db, seller_user_id, trade.market_id)

    buyer_update = update_position_for_buy(
        buyer_position, side, trade.quantity, trade.price
    )
    seller_update = update_position_for_sell(
        seller_position, side, trade.quantity, trade.price
    )

    return buyer_update, seller_update


def update_user_balance(db: Session, user_id: str, delta: float) -> float:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError(f"User not found: {user_id}")

    new_balance = user.balance + delta
    if new_balance < 0:
        raise ValueError(f"Insufficient balance. Has {user.balance}, needs {-delta}")

    user.balance = round(new_balance, 4)
    return user.balance


def calculate_unrealized_pnl(
    position: Position,
    yes_price: float,
    no_price: float,
) -> float:
    yes_value = position.yes_shares * yes_price
    no_value = position.no_shares * no_price
    total_value = yes_value + no_value
    total_cost = position.yes_cost_basis + position.no_cost_basis
    return round(total_value - total_cost, 4)


def get_position_summary(
    position: Position,
    yes_price: float,
    no_price: float,
) -> PositionSummary:
    yes_value = position.yes_shares * yes_price
    no_value = position.no_shares * no_price
    unrealized = calculate_unrealized_pnl(position, yes_price, no_price)

    return PositionSummary(
        market_id=position.market_id,
        yes_shares=position.yes_shares,
        no_shares=position.no_shares,
        yes_avg_price=position.yes_avg_price,
        no_avg_price=position.no_avg_price,
        yes_cost_basis=position.yes_cost_basis,
        no_cost_basis=position.no_cost_basis,
        yes_current_value=round(yes_value, 4),
        no_current_value=round(no_value, 4),
        unrealized_pnl=unrealized,
        realized_pnl=position.realized_pnl,
    )


def get_user_positions(
    db: Session,
    user_id: str,
    price_getter: callable,
) -> list[PositionSummary]:
    positions = db.query(Position).filter(Position.user_id == user_id).all()

    summaries = []
    for position in positions:
        if position.yes_shares == 0 and position.no_shares == 0:
            continue
        yes_price, no_price = price_getter(position.market_id)
        summaries.append(get_position_summary(position, yes_price, no_price))

    return summaries
