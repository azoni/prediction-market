from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


@dataclass
class Quote:
    bid_price: Optional[float]
    bid_size: int
    ask_price: Optional[float]
    ask_size: int


@dataclass
class MarketMakerConfig:
    spread: float = 0.04
    base_size: int = 100
    default_fair_price: float = 0.50
    max_inventory: int = 500
    inventory_skew_factor: float = 0.01
    min_price: float = 0.01
    max_price: float = 0.99


class MarketMakerBot:
    USER_ID = "MARKET_MAKER_BOT"

    def __init__(self, config: Optional[MarketMakerConfig] = None):
        self.config = config or MarketMakerConfig()
        self.inventory: dict[str, dict[str, int]] = {}
        self.fair_prices: dict[str, dict[str, float]] = {}

    def get_inventory(self, market_id: str, side: str) -> int:
        if market_id not in self.inventory:
            self.inventory[market_id] = {"YES": 0, "NO": 0}
        return self.inventory[market_id][side]

    def update_inventory(self, market_id: str, side: str, delta: int) -> None:
        if market_id not in self.inventory:
            self.inventory[market_id] = {"YES": 0, "NO": 0}
        self.inventory[market_id][side] += delta

    def get_fair_price(self, market_id: str, side: str) -> float:
        if market_id not in self.fair_prices:
            self.fair_prices[market_id] = {
                "YES": self.config.default_fair_price,
                "NO": 1.0 - self.config.default_fair_price,
            }
        return self.fair_prices[market_id][side]

    def set_fair_price(self, market_id: str, yes_price: float) -> None:
        if yes_price < 0.01 or yes_price > 0.99:
            raise ValueError("Fair price must be between 0.01 and 0.99")
        self.fair_prices[market_id] = {
            "YES": yes_price,
            "NO": round(1.0 - yes_price, 2),
        }

    def calculate_quote(self, market_id: str, side: str) -> Quote:
        fair = self.get_fair_price(market_id, side)
        inventory = self.get_inventory(market_id, side)
        half_spread = self.config.spread / 2

        base_bid = fair - half_spread
        base_ask = fair + half_spread

        skew = inventory * self.config.inventory_skew_factor
        bid_price = base_bid - skew
        ask_price = base_ask - skew

        bid_price = max(self.config.min_price, min(self.config.max_price, bid_price))
        ask_price = max(self.config.min_price, min(self.config.max_price, ask_price))

        bid_price = round(bid_price, 2)
        ask_price = round(ask_price, 2)

        if bid_price >= ask_price:
            mid = (bid_price + ask_price) / 2
            bid_price = round(max(self.config.min_price, mid - 0.01), 2)
            ask_price = round(min(self.config.max_price, mid + 0.01), 2)

        bid_size = self.config.base_size
        ask_size = self.config.base_size

        remaining_buy_capacity = self.config.max_inventory - inventory
        if remaining_buy_capacity <= 0:
            bid_size = 0
        elif remaining_buy_capacity < bid_size:
            bid_size = remaining_buy_capacity

        remaining_sell_capacity = self.config.max_inventory + inventory
        if remaining_sell_capacity <= 0:
            ask_size = 0
        elif remaining_sell_capacity < ask_size:
            ask_size = remaining_sell_capacity

        return Quote(
            bid_price=bid_price if bid_size > 0 else None,
            bid_size=bid_size,
            ask_price=ask_price if ask_size > 0 else None,
            ask_size=ask_size,
        )

    def generate_orders(self, market_id: str, side: str) -> list[dict]:
        quote = self.calculate_quote(market_id, side)
        orders = []

        if quote.bid_price is not None and quote.bid_size > 0:
            orders.append({
                "market_id": market_id,
                "order_id": str(uuid4()),
                "user_id": self.USER_ID,
                "side": side,
                "action": "BUY",
                "order_type": "LIMIT",
                "quantity": quote.bid_size,
                "price": quote.bid_price,
                "is_market_maker": True,
            })

        if quote.ask_price is not None and quote.ask_size > 0:
            orders.append({
                "market_id": market_id,
                "order_id": str(uuid4()),
                "user_id": self.USER_ID,
                "side": side,
                "action": "SELL",
                "order_type": "LIMIT",
                "quantity": quote.ask_size,
                "price": quote.ask_price,
                "is_market_maker": True,
            })

        return orders

    def on_trade(self, market_id: str, side: str, action: str, quantity: int) -> None:
        if action == "BUY":
            self.update_inventory(market_id, side, quantity)
        else:
            self.update_inventory(market_id, side, -quantity)

    def get_status(self, market_id: str) -> dict:
        yes_quote = self.calculate_quote(market_id, "YES")
        no_quote = self.calculate_quote(market_id, "NO")

        return {
            "market_id": market_id,
            "inventory": {
                "YES": self.get_inventory(market_id, "YES"),
                "NO": self.get_inventory(market_id, "NO"),
            },
            "fair_prices": {
                "YES": self.get_fair_price(market_id, "YES"),
                "NO": self.get_fair_price(market_id, "NO"),
            },
            "quotes": {
                "YES": {
                    "bid": {"price": yes_quote.bid_price, "size": yes_quote.bid_size},
                    "ask": {"price": yes_quote.ask_price, "size": yes_quote.ask_size},
                },
                "NO": {
                    "bid": {"price": no_quote.bid_price, "size": no_quote.bid_size},
                    "ask": {"price": no_quote.ask_price, "size": no_quote.ask_size},
                },
            },
        }
