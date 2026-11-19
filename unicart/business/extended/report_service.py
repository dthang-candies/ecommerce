"""UC-15 Generate Business Report (FR-17) and UC-20 View Recommendation Performance (FR-18).

Definitions (assumptions documented in docs/PROJECT_ANALYSIS.md):
  committed sales  = total of orders in PENDING..DELIVERED (online orders are paid, COD orders are alive)
  delivered revenue = total of DELIVERED orders
  cancel rate       = CANCELLED orders / all orders of the period
  stock turnover    = units sold in the period / units currently in stock
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from ...persistence.repositories import InteractionRepository, InventoryRepository, ReportRepository
from ..exceptions import BusinessError

# Dashboard sections and the roles that see them: the same rights as the pages behind each section.
DASHBOARD_SECTIONS = {
    "sales": {"MANAGER", "ADMIN"},
    "orders": {"SERVICE", "WAREHOUSE", "SALES", "ADMIN", "MANAGER"},
    "inventory": {"WAREHOUSE", "ADMIN", "MANAGER"},
    "support": {"SALES", "ADMIN"},
    "promotions": {"ADMIN", "MARKETING", "MANAGER"},
    "accounts": {"ADMIN"},
}

STATUSES = ("PENDING_PAYMENT", "PENDING", "CONFIRMED", "PACKED", "SHIPPING", "DELIVERED", "CANCELLED")


def _range(start: date, end: date) -> tuple[datetime, datetime]:
    if end < start:
        raise BusinessError("Ngày kết thúc phải sau ngày bắt đầu")
    if (end - start).days > 366:
        raise BusinessError("Khoảng thời gian tối đa là 1 năm")
    return datetime.combine(start, datetime.min.time()), datetime.combine(end + timedelta(days=1), datetime.min.time())


class ReportService:
    def __init__(self, session, reports: ReportRepository, inventory: InventoryRepository,
                 interactions: InteractionRepository):
        self.session, self.reports, self.inventory, self.interactions = session, reports, inventory, interactions

    def business(self, start: date, end: date) -> dict:
        lo, hi = _range(start, end)
        by_day = {str(d): (n, amount) for d, n, amount in self.reports.sales_by_day(lo, hi)}
        series, day = [], start
        while day <= end:
            n, amount = by_day.get(str(day), (0, Decimal("0")))
            series.append({"date": str(day), "orders": n, "sales": amount})
            day += timedelta(days=1)
        status = {s: 0 for s in STATUSES} | self.reports.orders_by_status(lo, hi)
        total_orders = sum(status.values())
        committed_orders = sum(x["orders"] for x in series)
        committed_sales = sum((x["sales"] for x in series), Decimal("0"))
        units_sold = self.reports.units_sold(lo, hi)
        inv = self.inventory.summary()
        return {
            "period": {"start": str(start), "end": str(end)},
            "kpis": {
                "total_orders": total_orders, "committed_orders": committed_orders,
                "committed_sales": committed_sales,
                "delivered_revenue": self.reports.delivered_revenue(lo, hi),
                "average_order_value": (committed_sales / committed_orders) if committed_orders else Decimal("0"),
                "cancel_rate": round(status["CANCELLED"] / total_orders * 100, 1) if total_orders else 0.0,
                "units_sold": units_sold,
                "stock_turnover": round(units_sold / inv["units"], 2) if inv["units"] else 0.0,
            },
            "series": series, "by_status": status,
            "top_products": [{"product_id": pid, "name": name, "sku": sku, "quantity": qty, "revenue": rev}
                             for pid, name, sku, qty, rev in self.reports.top_products(lo, hi, 10)],
            "inventory": inv,
        }

    def dashboard(self, role: str, today: date | None = None) -> dict:
        """Staff home page: what happened today and what is waiting, limited to the sections `role` may see."""
        today = today or date.today()
        can = lambda section: role in DASHBOARD_SECTIONS[section]
        out: dict = {"date": str(today)}
        if can("sales"):
            lo, hi = _range(today - timedelta(days=13), today)
            by_day = {str(d): (n, amount) for d, n, amount in self.reports.sales_by_day(lo, hi)}
            days = [today - timedelta(days=i) for i in range(13, -1, -1)]
            series = [{"date": str(d), "orders": by_day.get(str(d), (0, 0))[0],
                       "sales": by_day.get(str(d), (0, Decimal("0")))[1]} for d in days]
            total = lambda rows: {"orders": sum(r["orders"] for r in rows),
                                  "sales": sum((r["sales"] for r in rows), Decimal("0"))}
            out["sales"] = {"today": total(series[-1:]), "yesterday": total(series[-2:-1]),
                            "last_7_days": total(series[7:]), "previous_7_days": total(series[:7]),
                            "series": series[7:]}
        if can("orders"):
            waiting = self.reports.open_orders_by_status()
            out["orders"] = {
                "waiting": {s: waiting.get(s, 0) for s in STATUSES if s not in ("DELIVERED", "CANCELLED")},
                "recent": [{"id": o.id, "recipient": o.ship_recipient, "total_amount": o.total_amount,
                            "status": o.status, "created_at": o.created_at.isoformat()}
                           for o in self.reports.recent_orders(6)],
            }
        if can("inventory"):
            inv = self.inventory.summary()
            low = [i for i in self.inventory.low_stock() if i.product.status == "ACTIVE"]
            out["inventory"] = {
                "low_stock": inv["low_stock"], "out_of_stock": inv["out_of_stock"],
                "open_restock_requests": self.reports.open_restock_requests(),
                "lowest": [{"product_id": i.product_id, "name": i.product.name, "sku": i.product.sku,
                            "quantity": i.quantity, "min_threshold": i.min_threshold} for i in low[:5]],
            }
        if can("support"):
            support = self.reports.support_by_status()
            out["support"] = {"open": support.get("OPEN", 0), "in_progress": support.get("IN_PROGRESS", 0)}
        if can("promotions"):
            out["promotions"] = {"active": self.reports.active_promotions(datetime.now())}
        if can("accounts"):
            out["accounts"] = self.reports.account_counts(
                datetime.combine(today - timedelta(days=6), datetime.min.time()))
        return out

    def recommendation_performance(self, start: date, end: date) -> dict:
        lo, hi = _range(start, end)
        stats: dict[str, dict[str, int]] = defaultdict(lambda: {"impressions": 0, "clicks": 0, "add_to_cart": 0,
                                                                "purchases": 0})
        for event, keyword, n in self.interactions.counts(lo, hi):
            placement = (keyword or "").removeprefix("rec:") or "other"
            if event == "REC_IMPRESSION":
                stats[placement]["impressions"] += n
            elif event == "CLICK_REC":
                stats[placement]["clicks"] += n
            elif event == "ADD_TO_CART" and (keyword or "").startswith("rec:"):
                stats[placement]["add_to_cart"] += n
            elif event == "PURCHASE" and (keyword or "").startswith("rec:"):
                stats[placement]["purchases"] += n

        def row(name: str, s: dict[str, int]) -> dict:
            pct = lambda a, b: round(a / b * 100, 2) if b else 0.0
            return {"placement": name, **s, "ctr": pct(s["clicks"], s["impressions"]),                   # (3.3)
                    "add_to_cart_rate": pct(s["add_to_cart"], s["clicks"]),                               # (3.4)
                    "conversion_rate": pct(s["purchases"], s["impressions"])}                             # (3.5)

        rows = [row(k, v) for k, v in sorted(stats.items())]
        total = {k: sum(v[k] for v in stats.values()) for k in ("impressions", "clicks", "add_to_cart", "purchases")}
        return {"period": {"start": str(start), "end": str(end)}, "total": row("all", total), "placements": rows}
