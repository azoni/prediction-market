from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from models import User, Achievement, UserAchievement


SIGNUP_BONUS = 1000.0
DAILY_LOGIN_BASE = 50.0
STREAK_BONUS_PER_DAY = 10.0
MAX_STREAK_BONUS = 100.0

ACHIEVEMENT_DEFINITIONS = [
    {"id": "first_trade", "name": "First Steps", "description": "Place your first trade", "icon": "🎯", "reward": 100.0, "category": "trading"},
    {"id": "ten_trades", "name": "Getting Serious", "description": "Complete 10 trades", "icon": "📈", "reward": 250.0, "category": "trading"},
    {"id": "fifty_trades", "name": "Active Trader", "description": "Complete 50 trades", "icon": "💹", "reward": 500.0, "category": "trading"},
    {"id": "hundred_trades", "name": "Trading Machine", "description": "Complete 100 trades", "icon": "🤖", "reward": 1000.0, "category": "trading"},
    {"id": "first_market", "name": "Market Maker", "description": "Create your first market", "icon": "🏪", "reward": 150.0, "category": "creation"},
    {"id": "five_markets", "name": "Question Master", "description": "Create 5 markets", "icon": "❓", "reward": 300.0, "category": "creation"},
    {"id": "first_win", "name": "Winner Winner", "description": "Profit from a resolved market", "icon": "🏆", "reward": 200.0, "category": "winning"},
    {"id": "five_wins", "name": "On a Roll", "description": "Profit from 5 resolved markets", "icon": "🔥", "reward": 500.0, "category": "winning"},
    {"id": "ten_wins", "name": "Oracle", "description": "Profit from 10 resolved markets", "icon": "🔮", "reward": 1000.0, "category": "winning"},
    {"id": "streak_3", "name": "Dedicated", "description": "Log in 3 days in a row", "icon": "📅", "reward": 100.0, "category": "streak"},
    {"id": "streak_7", "name": "Weekly Regular", "description": "Log in 7 days in a row", "icon": "🗓️", "reward": 300.0, "category": "streak"},
    {"id": "streak_30", "name": "Monthly Master", "description": "Log in 30 days in a row", "icon": "📆", "reward": 1000.0, "category": "streak"},
    {"id": "balance_5000", "name": "Building Wealth", "description": "Reach a balance of 5,000 DuCoins", "icon": "💰", "reward": 250.0, "category": "wealth"},
    {"id": "balance_10000", "name": "High Roller", "description": "Reach a balance of 10,000 DuCoins", "icon": "💎", "reward": 500.0, "category": "wealth"},
]


@dataclass
class DailyLoginResult:
    already_claimed: bool
    base_reward: float
    streak_bonus: float
    total_reward: float
    new_streak: int
    new_balance: float
    achievements_earned: list[dict]


def seed_achievements(db: Session) -> int:
    created = 0
    for defn in ACHIEVEMENT_DEFINITIONS:
        existing = db.query(Achievement).filter(Achievement.id == defn["id"]).first()
        if not existing:
            achievement = Achievement(
                id=defn["id"],
                name=defn["name"],
                description=defn["description"],
                icon=defn["icon"],
                reward=defn["reward"],
                category=defn["category"],
            )
            db.add(achievement)
            created += 1

    if created > 0:
        db.commit()

    return created


def process_daily_login(db: Session, user: User) -> DailyLoginResult:
    today = datetime.utcnow().date()
    achievements_earned = []

    if user.last_login_date and user.last_login_date.date() == today:
        return DailyLoginResult(
            already_claimed=True,
            base_reward=0,
            streak_bonus=0,
            total_reward=0,
            new_streak=user.login_streak,
            new_balance=user.balance,
            achievements_earned=[],
        )

    yesterday = today - timedelta(days=1)
    if user.last_login_date and user.last_login_date.date() == yesterday:
        new_streak = user.login_streak + 1
    else:
        new_streak = 1

    base_reward = DAILY_LOGIN_BASE
    streak_bonus = min((new_streak - 1) * STREAK_BONUS_PER_DAY, MAX_STREAK_BONUS)
    total_reward = base_reward + streak_bonus

    user.last_login_date = datetime.utcnow()
    user.login_streak = new_streak
    user.balance = round(user.balance + total_reward, 2)
    user.lifetime_earnings = round(user.lifetime_earnings + total_reward, 2)

    streak_achievements = check_streak_achievements(db, user, new_streak)
    achievements_earned.extend(streak_achievements)

    balance_achievements = check_balance_achievements(db, user)
    achievements_earned.extend(balance_achievements)

    return DailyLoginResult(
        already_claimed=False,
        base_reward=base_reward,
        streak_bonus=streak_bonus,
        total_reward=total_reward,
        new_streak=new_streak,
        new_balance=user.balance,
        achievements_earned=achievements_earned,
    )


def check_and_award_achievement(
    db: Session,
    user: User,
    achievement_id: str,
) -> Optional[dict]:
    existing = db.query(UserAchievement).filter(
        UserAchievement.user_id == user.id,
        UserAchievement.achievement_id == achievement_id,
    ).first()

    if existing:
        return None

    achievement = db.query(Achievement).filter(Achievement.id == achievement_id).first()
    if not achievement:
        return None

    user_achievement = UserAchievement(
        id=str(uuid4()),
        user_id=user.id,
        achievement_id=achievement_id,
    )
    db.add(user_achievement)

    user.balance = round(user.balance + achievement.reward, 2)
    user.lifetime_earnings = round(user.lifetime_earnings + achievement.reward, 2)

    return {
        "id": achievement.id,
        "name": achievement.name,
        "description": achievement.description,
        "icon": achievement.icon,
        "reward": achievement.reward,
    }


def check_trading_achievements(db: Session, user: User) -> list[dict]:
    earned = []

    if user.total_trades >= 1:
        result = check_and_award_achievement(db, user, "first_trade")
        if result:
            earned.append(result)

    if user.total_trades >= 10:
        result = check_and_award_achievement(db, user, "ten_trades")
        if result:
            earned.append(result)

    if user.total_trades >= 50:
        result = check_and_award_achievement(db, user, "fifty_trades")
        if result:
            earned.append(result)

    if user.total_trades >= 100:
        result = check_and_award_achievement(db, user, "hundred_trades")
        if result:
            earned.append(result)

    return earned


def check_market_creation_achievements(db: Session, user: User) -> list[dict]:
    earned = []

    if user.total_markets_created >= 1:
        result = check_and_award_achievement(db, user, "first_market")
        if result:
            earned.append(result)

    if user.total_markets_created >= 5:
        result = check_and_award_achievement(db, user, "five_markets")
        if result:
            earned.append(result)

    return earned


def check_winning_achievements(db: Session, user: User) -> list[dict]:
    earned = []

    if user.total_correct_predictions >= 1:
        result = check_and_award_achievement(db, user, "first_win")
        if result:
            earned.append(result)

    if user.total_correct_predictions >= 5:
        result = check_and_award_achievement(db, user, "five_wins")
        if result:
            earned.append(result)

    if user.total_correct_predictions >= 10:
        result = check_and_award_achievement(db, user, "ten_wins")
        if result:
            earned.append(result)

    return earned


def check_streak_achievements(db: Session, user: User, streak: int) -> list[dict]:
    earned = []

    if streak >= 3:
        result = check_and_award_achievement(db, user, "streak_3")
        if result:
            earned.append(result)

    if streak >= 7:
        result = check_and_award_achievement(db, user, "streak_7")
        if result:
            earned.append(result)

    if streak >= 30:
        result = check_and_award_achievement(db, user, "streak_30")
        if result:
            earned.append(result)

    return earned


def check_balance_achievements(db: Session, user: User) -> list[dict]:
    earned = []

    if user.balance >= 5000:
        result = check_and_award_achievement(db, user, "balance_5000")
        if result:
            earned.append(result)

    if user.balance >= 10000:
        result = check_and_award_achievement(db, user, "balance_10000")
        if result:
            earned.append(result)

    return earned


def get_user_achievements(db: Session, user_id: str) -> list[dict]:
    user_achievements = db.query(UserAchievement).filter(
        UserAchievement.user_id == user_id
    ).all()

    result = []
    for ua in user_achievements:
        achievement = ua.achievement
        result.append({
            "id": achievement.id,
            "name": achievement.name,
            "description": achievement.description,
            "icon": achievement.icon,
            "reward": achievement.reward,
            "category": achievement.category,
            "earned_at": ua.earned_at.isoformat(),
        })

    return result


def get_all_achievements(db: Session, user_id: Optional[str] = None) -> list[dict]:
    achievements = db.query(Achievement).all()

    earned_ids = set()
    if user_id:
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id
        ).all()
        earned_ids = {ua.achievement_id for ua in user_achievements}

    result = []
    for a in achievements:
        result.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "reward": a.reward,
            "category": a.category,
            "earned": a.id in earned_ids,
        })

    return result
