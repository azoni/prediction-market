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
    db: Session,
    position: Position,
    side: str,
    quantity: int,
    price: float,
    user_id: str,
) -> PositionUpdate:
    """
    Update position when buying shares.
    """
    from market_maker import MarketMakerBot
    
    # Market maker doesn't track positions
    if user_id == MarketMakerBot.USER_ID:
        return PositionUpdate(
            shares_delta=quantity,
            cost_basis_delta=0,
            realized_pnl=0,
        )
    
    cost = price * quantity

    if side == "YES":
        position.yes_shares += quantity
        position.yes_cost_basis += cost
    else:
        position.no_shares += quantity
        position.no_cost_basis += cost

    return PositionUpdate(
        shares_delta=quantity,
        cost_basis_delta=cost,
        realized_pnl=0,
    )


def update_position_for_sell(
    db: Session,
    position: Position,
    side: str,
    quantity: int,
    price: float,
    user_id: str,
) -> PositionUpdate:
    """
    Update position when selling shares.
    Returns the P&L realized from this sale.
    """
    from market_maker import MarketMakerBot
    
    # Market maker can sell without owning (it provides liquidity)
    if user_id == MarketMakerBot.USER_ID:
        return PositionUpdate(
            shares_delta=-quantity,
            cost_basis_delta=0,
            realized_pnl=0,
        )
    
    if side == "YES":
        old_shares = position.yes_shares
        old_cost_basis = position.yes_cost_basis
    else:
        old_shares = position.no_shares
        old_cost_basis = position.no_cost_basis

    if old_shares < quantity:
        raise ValueError(f"Cannot sell {quantity} shares, only own {old_shares}")

    avg_cost = old_cost_basis / old_shares if old_shares > 0 else 0
    cost_of_sold = avg_cost * quantity
    sale_proceeds = price * quantity
    realized_pnl = sale_proceeds - cost_of_sold

    if side == "YES":
        position.yes_shares -= quantity
        position.yes_cost_basis -= cost_of_sold
    else:
        position.no_shares -= quantity
        position.no_cost_basis -= cost_of_sold

    position.realized_pnl += realized_pnl

    return PositionUpdate(
        shares_delta=-quantity,
        cost_basis_delta=-cost_of_sold,
        realized_pnl=realized_pnl,
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
