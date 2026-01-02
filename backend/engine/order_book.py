from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import bisect


class BookSide(str, Enum):
    BID = "BID"
    ASK = "ASK"


@dataclass
class BookOrder:
    order_id: str
    user_id: str
    price: float
    quantity: int
    timestamp: datetime
    is_market_maker: bool = False

    def __lt__(self, other: "BookOrder") -> bool:
        return self.timestamp < other.timestamp


@dataclass
class PriceLevel:
    price: float
    orders: list[BookOrder] = field(default_factory=list)

    @property
    def total_quantity(self) -> int:
        return sum(order.quantity for order in self.orders)

    def add_order(self, order: BookOrder) -> None:
        bisect.insort(self.orders, order)

    def remove_order(self, order_id: str) -> Optional[BookOrder]:
        for i, order in enumerate(self.orders):
            if order.order_id == order_id:
                return self.orders.pop(i)
        return None


class OrderBookSide:
    def __init__(self, side: BookSide):
        self.side = side
        self.levels: list[PriceLevel] = []

    def _find_level_index(self, price: float) -> tuple[int, bool]:
        for i, level in enumerate(self.levels):
            if level.price == price:
                return i, True
            if self.side == BookSide.BID and level.price < price:
                return i, False
            if self.side == BookSide.ASK and level.price > price:
                return i, False
        return len(self.levels), False

    def add_order(self, order: BookOrder) -> None:
        index, exists = self._find_level_index(order.price)
        if exists:
            self.levels[index].add_order(order)
        else:
            level = PriceLevel(price=order.price)
            level.add_order(order)
            self.levels.insert(index, level)

    def remove_order(self, order_id: str, price: float) -> Optional[BookOrder]:
        index, exists = self._find_level_index(price)
        if not exists:
            return None
        order = self.levels[index].remove_order(order_id)
        if order and len(self.levels[index].orders) == 0:
            self.levels.pop(index)
        return order

    def get_best(self) -> Optional[PriceLevel]:
        return self.levels[0] if self.levels else None

    def get_best_price(self) -> Optional[float]:
        best = self.get_best()
        return best.price if best else None

    def get_depth(self, num_levels: int = 10) -> list[dict]:
        return [
            {"price": level.price, "quantity": level.total_quantity}
            for level in self.levels[:num_levels]
        ]


class OrderBook:
    def __init__(self):
        self.bids = OrderBookSide(BookSide.BID)
        self.asks = OrderBookSide(BookSide.ASK)

    def add_order(self, order: BookOrder, side: BookSide) -> None:
        if side == BookSide.BID:
            self.bids.add_order(order)
        else:
            self.asks.add_order(order)

    def remove_order(self, order_id: str, price: float, side: BookSide) -> Optional[BookOrder]:
        if side == BookSide.BID:
            return self.bids.remove_order(order_id, price)
        else:
            return self.asks.remove_order(order_id, price)

    def get_best_bid(self) -> Optional[float]:
        return self.bids.get_best_price()

    def get_best_ask(self) -> Optional[float]:
        return self.asks.get_best_price()

    def get_spread(self) -> Optional[float]:
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid is None or ask is None:
            return None
        return round(ask - bid, 2)

    def get_mid_price(self) -> Optional[float]:
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid is None or ask is None:
            return None
        return round((bid + ask) / 2, 2)

    def get_snapshot(self, depth: int = 10) -> dict:
        return {
            "bids": self.bids.get_depth(depth),
            "asks": self.asks.get_depth(depth),
            "best_bid": self.get_best_bid(),
            "best_ask": self.get_best_ask(),
            "spread": self.get_spread(),
            "mid_price": self.get_mid_price(),
        }


class MarketOrderBooks:
    def __init__(self, market_id: str):
        self.market_id = market_id
        self.yes_book = OrderBook()
        self.no_book = OrderBook()

    def get_book(self, side: str) -> OrderBook:
        if side.upper() == "YES":
            return self.yes_book
        elif side.upper() == "NO":
            return self.no_book
        else:
            raise ValueError(f"Invalid side: {side}")

    def get_full_snapshot(self, depth: int = 10) -> dict:
        return {
            "market_id": self.market_id,
            "yes": self.yes_book.get_snapshot(depth),
            "no": self.no_book.get_snapshot(depth),
        }
