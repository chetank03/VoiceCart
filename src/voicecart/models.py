from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroceryItem:
    name: str
    original_name: str | None = None
    quantity: str = "1"

    @property
    def has_quantity(self) -> bool:
        """True if the user specified a real quantity (not the default '1' with no unit)."""
        parts = self.quantity.strip().split()
        return len(parts) >= 2 or (len(parts) == 1 and parts[0] not in {"", "1"})

    @property
    def search_query(self) -> str:
        """Include quantity in search when specified, e.g. 'milk 2 litre'."""
        if self.has_quantity:
            return f"{self.name} {self.quantity}".strip()
        return self.name.strip()


@dataclass(frozen=True)
class GroceryRequest:
    raw_text: str
    items: tuple[GroceryItem, ...]
    language: str = "en"
    intent: str = "order"  # "order" | "price_check"

    def summary(self) -> str:
        return ", ".join(f"{item.quantity} {item.name}" for item in self.items)
