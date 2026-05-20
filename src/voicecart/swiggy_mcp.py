from __future__ import annotations

from dataclasses import dataclass

from voicecart.models import GroceryItem


@dataclass(frozen=True)
class McpCartResult:
    item: GroceryItem
    status: str
    detail: str


class SwiggyMcpClient:
    """Thin adapter boundary for the real Swiggy MCP tools.

    Keep MCP-specific transport details here once the tool names/schema are known.
    The rest of VoiceCart should only work with normalized GroceryItem objects.
    """

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    async def build_cart(self, items: tuple[GroceryItem, ...]) -> list[McpCartResult]:
        if self.dry_run:
            return [
                McpCartResult(
                    item=item,
                    status="dry_run",
                    detail=f"Would search Swiggy MCP for '{item.search_query}' and add {item.quantity}.",
                )
                for item in items
            ]

        raise NotImplementedError(
            "Connect the Swiggy MCP tool names/schema in SwiggyMcpClient before live cart changes."
        )
