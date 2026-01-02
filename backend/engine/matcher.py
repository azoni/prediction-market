from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .order_book import OrderBook, BookOrder, BookSide, MarketOrderBooks


@dataclass
class TradeResult:
    trade_id: str
    market_id: str
    side: str
    buyer_order_id: str
    seller_order_id: str
    buyer_user_id: str
    seller_user_id: str
    price: float
    quantity: int
    total: float
    executed_at: datetime


@dataclass
class MatchResult:
    order_id: str
    trades: list[TradeResult]
    filled_quantity: int
    remaining_quantity: int
    added_to_book: bool

    @property
    def fully_filled(self) -> bool:
        return self.remaining_quantity == 0

    @property
    def average_price(self) -> Optional[float]:
        if not self.trades:
            return None
        total_value = sum(t.total for t in self.trades)
        total_qty = sum(t.quantity for t in self.trades)
        return round(total_value / total_qty, 4) if total_qty > 0 else None


class MatchingEngine:
    def __init__(self):
        self.books: dict[str, MarketOrderBooks] = {}

    def get_or_create_books(self, market_id: str) -> MarketOrderBooks:
        if market_id not in self.books:
            self.books[market_id] = MarketOrderBooks(market_id)
        return self.books[market_id]

    def process_order(
        self,
        market_id: str,
        order_id: str,
        user_id: str,
        side: str,
        action: str,
        order_type: str,
        quantity: int,
        price: Optional[float] = None,
        is_market_maker: bool = False,
    ) -> MatchResult:
        if order_type == "LIMIT" and price is None:
            raise ValueError("LIMIT orders require a price")
        if order_type == "LIMIT" and (price < 0.01 or price > 0.99):
            raise ValueError("Price must be between $0.01 and $0.99")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        books = self.get_or_create_books(market_id)
        book = books.get_book(side)

        trades, remaining = self._match_order(
            book=book,
            market_id=market_id,
            order_id=order_id,
            user_id=user_id,
            side=side,
            action=action,
            order_type=order_type,
            quantity=quantity,
            price=price,
            is_market_maker=is_market_maker,
        )

        added_to_book = False
        if remaining > 0 and order_type == "LIMIT":
            book_order = BookOrder(
                order_id=order_id,
                user_id=user_id,
                price=price,
                quantity=remaining,
                timestamp=datetime.utcnow(),
                is_market_maker=is_market_maker,
            )
            book_side = BookSide.BID if action == "BUY" else BookSide.ASK
            book.add_order(book_order, book_side)
            added_to_book = True

        return MatchResult(
            order_id=order_id,
            trades=trades,
            filled_quantity=quantity - remaining,
            remaining_quantity=remaining,
            added_to_book=added_to_book,
        )

    def _match_order(
        self,
        book: OrderBook,
        market_id: str,
        order_id: str,
        user_id: str,
        side: str,
        action: str,
        order_type: str,
        quantity: int,
        price: Optional[float],
        is_market_maker: bool,
    ) -> tuple[list[TradeResult], int]:
        trades = []
        remaining = quantity

        if action == "BUY":
            opposite_side = book.asks

            def price_acceptable(resting_price: float) -> bool:
                if order_type == "MARKET":
                    return True
                return price >= resting_price
        else:
            opposite_side = book.bids

            def price_acceptable(resting_price: float) -> bool:
                if order_type == "MARKET":
                    return True
                return price <= resting_price

        while remaining > 0:
            best_level = opposite_side.get_best()
            if best_level is None:
                break
            if not price_acceptable(best_level.price):
                break

            while remaining > 0 and best_level.orders:
                resting_order = best_level.orders[0]

                if resting_order.user_id == user_id:
                    best_level.orders.pop(0)
                    continue

                fill_qty = min(remaining, resting_order.quantity)
                fill_price = resting_order.price

                if action == "BUY":
                    buyer_order_id = order_id
                    buyer_user_id = user_id
                    seller_order_id = resting_order.order_id
                    seller_user_id = resting_order.user_id
                else:
                    seller_order_id = order_id
                    seller_user_id = user_id
                    buyer_order_id = resting_order.order_id
                    buyer_user_id = resting_order.user_id

                trade = TradeResult(
                    trade_id=str(uuid4()),
                    market_id=market_id,
                    side=side,
                    buyer_order_id=buyer_order_id,
                    seller_order_id=seller_order_id,
                    buyer_user_id=buyer_user_id,
                    seller_user_id=seller_user_id,
                    price=fill_price,
                    quantity=fill_qty,
                    total=round(fill_price * fill_qty, 4),
                    executed_at=datetime.utcnow(),
                )
                trades.append(trade)

                remaining -= fill_qty
                resting_order.quantity -= fill_qty

                if resting_order.quantity == 0:
                    best_level.orders.pop(0)

            if not best_level.orders:
                opposite_side.levels.pop(0)

        return trades, remaining

    def cancel_order(
        self,
        market_id: str,
        order_id: str,
        side: str,
        action: str,
        price: float,
    ) -> bool:
        books = self.get_or_create_books(market_id)
        book = books.get_book(side)
        book_side = BookSide.BID if action == "BUY" else BookSide.ASK
        removed = book.remove_order(order_id, price, book_side)
        return removed is not None

    def get_book_snapshot(self, market_id: str, depth: int = 10) -> dict:
        books = self.get_or_create_books(market_id)
        return books.get_full_snapshot(depth)
