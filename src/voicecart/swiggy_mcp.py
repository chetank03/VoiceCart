from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from voicecart.models import GroceryItem
from voicecart.nlu import VoiceCartError


_MCP_URL = "https://mcp.swiggy.com/im"
_TIMEOUT = 20.0
_MAX_ORDER_TOTAL = 1000  # Swiggy MCP checkout limit in rupees


@dataclass(frozen=True)
class ProductVariant:
    spin_id: str
    name: str
    price: float
    unit: str


@dataclass(frozen=True)
class McpCartResult:
    item: GroceryItem
    status: str
    detail: str
    price: float = 0.0
    quantity: int = 1


@dataclass
class BillSummary:
    items: list[tuple[str, int, float]] = field(default_factory=list)  # (name, qty, price)
    item_total: float = 0.0
    delivery_fee: float = 0.0
    small_order_fee: float = 0.0
    surge_fee: float = 0.0
    discount: float = 0.0
    taxes: float = 0.0
    grand_total: float = 0.0
    minimum_order_value: float = 0.0
    payment_methods: list[str] = field(default_factory=list)

    @property
    def amount_to_avoid_small_order_fee(self) -> float:
        if self.small_order_fee > 0 and self.minimum_order_value > 0:
            gap = self.minimum_order_value - self.item_total
            return max(0.0, gap)
        return 0.0

    def speak_lines(self) -> list[str]:
        lines: list[str] = []

        # Item breakdown
        for name, qty, price in self.items:
            lines.append(f"  {qty}x {name} — ₹{price:.0f}")

        lines.append(f"Items total: ₹{self.item_total:.0f}")

        if self.delivery_fee:
            lines.append(f"Delivery fee: ₹{self.delivery_fee:.0f}")
        if self.small_order_fee:
            lines.append(f"Small order fee: ₹{self.small_order_fee:.0f}")
        if self.surge_fee:
            lines.append(f"Surge fee: ₹{self.surge_fee:.0f}")
        if self.discount:
            lines.append(f"Discount: -₹{self.discount:.0f}")
        if self.taxes:
            lines.append(f"Taxes: ₹{self.taxes:.0f}")

        lines.append(f"Grand total: ₹{self.grand_total:.0f}")

        gap = self.amount_to_avoid_small_order_fee
        if gap > 0:
            lines.append(
                f"Tip: Add ₹{gap:.0f} more to avoid the small order fee."
            )

        return lines


class SwiggyMcpClient:
    def __init__(self, token: str, dry_run: bool = True) -> None:
        self._token = token
        self.dry_run = dry_run
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def get_addresses(self) -> list[dict]:
        data = await self._call("get_addresses", {})
        return data.get("addresses", [])

    async def search_products(self, address_id: str, query: str) -> list[ProductVariant]:
        data = await self._call("search_products", {"addressId": address_id, "query": query})
        variants = []
        for product in data.get("products", []):
            for v in product.get("variants", [product]):
                variants.append(ProductVariant(
                    spin_id=v.get("spinId", ""),
                    name=v.get("name", query),
                    price=float(v.get("price", 0)),
                    unit=v.get("unit", ""),
                ))
        return variants

    async def update_cart(self, address_id: str, items: list[dict]) -> dict:
        return await self._call("update_cart", {
            "selectedAddressId": address_id,
            "items": items,
        })

    async def get_cart(self) -> dict:
        return await self._call("get_cart", {})

    async def checkout(self, address_id: str, payment_method: str | None = None) -> dict:
        params: dict = {"addressId": address_id}
        if payment_method:
            params["paymentMethod"] = payment_method
        return await self._call("checkout", params)

    # ------------------------------------------------------------------ #
    # High-level cart builder (called from main.py)
    # ------------------------------------------------------------------ #

    async def build_cart(self, items: tuple[GroceryItem, ...]) -> tuple[list[McpCartResult], BillSummary]:
        addresses = await self.get_addresses()
        if not addresses:
            raise VoiceCartError("No saved delivery address found on your Swiggy account. Add one in the app first.")
        address_id = addresses[0]["id"]

        results: list[McpCartResult] = []
        cart_items: list[dict] = []

        for item in items:
            variants = await self.search_products(address_id, item.search_query)

            if not variants:
                results.append(McpCartResult(
                    item=item, status="not_found",
                    detail=f"No results found for '{item.name}' on Instamart.",
                ))
                continue

            chosen = variants[0]
            try:
                qty = max(1, int(float(item.quantity.split()[0])))
            except (ValueError, IndexError):
                qty = 1

            line_price = chosen.price * qty

            if self.dry_run:
                results.append(McpCartResult(
                    item=item, status="dry_run",
                    detail=f"{qty}x {chosen.name} — ₹{line_price:.0f}",
                    price=line_price, quantity=qty,
                ))
            else:
                cart_items.append({"spinId": chosen.spin_id, "quantity": qty})
                results.append(McpCartResult(
                    item=item, status="added",
                    detail=f"{qty}x {chosen.name} — ₹{line_price:.0f}",
                    price=line_price, quantity=qty,
                ))

        if not self.dry_run and cart_items:
            await self.update_cart(address_id, cart_items)

        bill = await self._make_bill_summary(results)
        return results, bill

    async def get_item_prices(self, items: tuple[GroceryItem, ...]) -> list[str]:
        """Return spoken price lines for each item without touching the cart."""
        addresses = await self.get_addresses()
        if not addresses:
            raise VoiceCartError("No saved delivery address found on your Swiggy account.")
        address_id = addresses[0]["id"]

        lines: list[str] = []
        for item in items:
            variants = await self.search_products(address_id, item.search_query)
            if not variants:
                lines.append(f"{item.name} not found on Instamart.")
                continue

            default = variants[0]
            if item.has_quantity:
                # Specific size asked — show best match
                lines.append(f"{default.name} costs ₹{default.price:.0f}.")
            else:
                # No quantity — show default variant, mention others available
                unit_str = f" {default.unit}" if default.unit else ""
                extra = len(variants) - 1
                more = f" ({extra} more size{'s' if extra > 1 else ''} available)" if extra > 0 else ""
                lines.append(
                    f"{default.name}{unit_str} costs ₹{default.price:.0f}{more}."
                )
        return lines

    async def place_order(self, address_id: str) -> str:
        cart = await self.get_cart()
        total = _pick(cart, "billTotal", "grandTotal", "total", default=0)
        if total > _MAX_ORDER_TOTAL:
            raise VoiceCartError(
                f"Cart total ₹{total} exceeds the ₹{_MAX_ORDER_TOTAL} limit for AI ordering. "
                "Please complete this order in the Swiggy app."
            )
        result = await self.checkout(address_id)
        return result.get("message", "Order placed successfully.")

    # ------------------------------------------------------------------ #
    # Bill summary helpers
    # ------------------------------------------------------------------ #

    async def _make_bill_summary(self, results: list[McpCartResult]) -> BillSummary:
        bill = BillSummary()

        if not self.dry_run:
            # Fetch live bill from Swiggy cart
            cart = await self.get_cart()
            b = cart.get("bill", cart.get("billBreakup", cart.get("billDetails", {})))

            bill.item_total   = float(_pick(b, "itemTotal", "subTotal", "mrpTotal", default=0))
            bill.delivery_fee = float(_pick(b, "deliveryFee", "deliveryCharge", "deliveryCharges", default=0))
            bill.small_order_fee = float(_pick(b, "smallOrderFee", "smallCartFee", "smallOrderCharge", default=0))
            bill.surge_fee    = float(_pick(b, "surgeFee", "surgeCharge", "surge", default=0))
            bill.discount     = float(_pick(b, "discount", "totalDiscount", "savings", default=0))
            bill.taxes        = float(_pick(b, "taxes", "gst", "tax", default=0))
            bill.grand_total  = float(_pick(b, "grandTotal", "billTotal", "totalAmount", "total", default=0))
            bill.minimum_order_value = float(_pick(
                b, "minimumOrderValue", "minOrderValue", "minCartValue", default=0
            ))
            methods = cart.get("availablePaymentMethods", [])
            bill.payment_methods = [
                m.get("name", m.get("type", str(m))) for m in methods if isinstance(m, dict)
            ] or ([str(m) for m in methods] if methods else [])
        else:
            # Dry-run: calculate from variant prices only
            bill.item_total = sum(r.price for r in results if r.status == "dry_run")
            bill.grand_total = bill.item_total  # fees unknown in dry-run

        bill.items = [
            (r.item.name, r.quantity, r.price)
            for r in results
            if r.status in {"dry_run", "added"}
        ]

        return bill

    # ------------------------------------------------------------------ #
    # Transport
    # ------------------------------------------------------------------ #

    async def _call(self, tool: str, arguments: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
            "id": 1,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(_MCP_URL, json=payload, headers=self._headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise VoiceCartError("Swiggy session expired. Re-run the OAuth flow to get a new token.") from e
                raise VoiceCartError(f"Swiggy MCP error {e.response.status_code}: {e.response.text}") from e
            except httpx.RequestError as e:
                raise VoiceCartError(f"Could not reach Swiggy MCP. Check your internet connection. ({e})") from e

        body = resp.json()
        if "error" in body:
            raise VoiceCartError(f"Swiggy MCP tool error: {body['error'].get('message', body['error'])}")

        return body.get("result", {}).get("content", [{}])[0].get("data", {})


def _pick(d: dict, *keys: str, default=None):
    """Return the first matching key from a dict, or default."""
    for k in keys:
        if k in d:
            return d[k]
    return default
