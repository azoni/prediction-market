from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from models import Transaction, TransactionType, User


def record_transaction(
    db: Session,
    user_id: str,
    tx_type: TransactionType,
    amount: float,
    balance_after: float,
    description: str = None,
    reference_id: str = None,
) -> Transaction:
    """Record a transaction for audit trail."""
    tx = Transaction(
        id=str(uuid4()),
        user_id=user_id,
        type=tx_type,
        amount=amount,
        balance_after=balance_after,
        description=description,
        reference_id=reference_id,
    )
    db.add(tx)
    return tx


def record_signup_bonus(db: Session, user: User) -> Transaction:
    return record_transaction(
        db=db,
        user_id=user.id,
        tx_type=TransactionType.SIGNUP_BONUS,
        amount=1000.0,
        balance_after=user.balance,
        description="Welcome to DuMarket! Here's 1,000 DC to get started.",
    )


def record_daily_reward(
    db: Session,
    user: User,
    base_reward: float,
    streak_bonus: float,
    streak_days: int,
) -> Transaction:
    total = base_reward + streak_bonus
    if streak_bonus > 0:
        description = f"Daily reward: {base_reward:.0f} DC + {streak_bonus:.0f} DC streak bonus (Day {streak_days})"
    else:
        description = f"Daily reward: {base_reward:.0f} DC"
    
    return record_transaction(
        db=db,
        user_id=user.id,
        tx_type=TransactionType.DAILY_REWARD,
        amount=total,
        balance_after=user.balance,
        description=description,
    )


def record_trade_buy(
    db: Session,
    user: User,
    amount: float,
    trade_id: str,
    side: str,
    quantity: int,
    price: float,
) -> Transaction:
    return record_transaction(
        db=db,
        user_id=user.id,
        tx_type=TransactionType.TRADE_BUY,
        amount=-amount,
        balance_after=user.balance,
        description=f"Bought {quantity} {side} @ {price*100:.0f}¢",
        reference_id=trade_id,
    )


def record_trade_sell(
    db: Session,
    user: User,
    amount: float,
    trade_id: str,
    side: str,
    quantity: int,
    price: float,
) -> Transaction:
    return record_transaction(
        db=db,
        user_id=user.id,
        tx_type=TransactionType.TRADE_SELL,
        amount=amount,
        balance_after=user.balance,
        description=f"Sold {quantity} {side} @ {price*100:.0f}¢",
        reference_id=trade_id,
    )


def record_market_payout(
    db: Session,
    user: User,
    amount: float,
    market_id: str,
    outcome: str,
    shares: int,
) -> Transaction:
    return record_transaction(
        db=db,
        user_id=user.id,
        tx_type=TransactionType.MARKET_PAYOUT,
        amount=amount,
        balance_after=user.balance,
        description=f"Payout: {shares} {outcome} shares @ $1.00",
        reference_id=market_id,
    )


def record_admin_adjustment(
    db: Session,
    user: User,
    amount: float,
    reason: str,
) -> Transaction:
    return record_transaction(
        db=db,
        user_id=user.id,
        tx_type=TransactionType.ADMIN_ADJUSTMENT,
        amount=amount,
        balance_after=user.balance,
        description=f"Admin adjustment: {reason}",
    )


def get_user_transactions(db: Session, user_id: str, limit: int = 50) -> list[Transaction]:
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).limit(limit).all()
