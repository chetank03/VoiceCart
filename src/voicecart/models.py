from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroceryItem:
    name: str
    original_name: str | None = None
    quantity: str = "1"

    @property
    def search_query(self) -> str:
        return self.name.strip()


@dataclass(frozen=True)
class GroceryRequest:
    raw_text: str
    items: tuple[GroceryItem, ...]
    language: str = "en"

    def summary(self) -> str:
        return ", ".join(f"{item.quantity} {item.name}" for item in self.items)
