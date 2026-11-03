"""Domain objects -> JSON-friendly dicts. Money is sent as numbers (VND, NFR-18)."""
from datetime import datetime, timedelta
from decimal import Decimal

from .. import config


def num(v) -> int | float:
    d = Decimal(v)
    return int(d) if d == d.to_integral_value() else float(d)


def iso(d):
    return d.isoformat() if d else None


def category_json(c, count: int | None = None) -> dict:
    out = {"id": c.id, "name": c.name, "description": c.description}
    if count is not None:
        out["product_count"] = count
    return out


def product_json(p, rating: tuple[float, int] | None = None, admin: bool = False) -> dict:
    qty = p.inventory.quantity if p.inventory else 0
    out = {"id": p.id, "sku": p.sku, "name": p.name, "brand": p.brand, "description": p.description,
           "price": num(p.price), "image_url": p.image_url, "attributes": p.attributes or {},
           "category": category_json(p.category) if p.category else {"id": p.category_id},
           "in_stock": qty > 0, "quantity": qty, "created_at": iso(p.created_at)}
    if rating is not None:
        out["rating"] = {"average": round(rating[0], 1), "count": rating[1]}
    if admin:
        out["status"] = p.status
        out["min_threshold"] = p.inventory.min_threshold if p.inventory else 0
    return out


def recommendation_json(r) -> dict:
    return {**product_json(r.product), "reason": r.reason}


def cart_json(c) -> dict:
    items = []
    for i in sorted(c.items, key=lambda i: i.product_id):
        p = i.product
        stock = p.inventory.quantity if p.inventory else 0
        items.append({"product_id": i.product_id, "name": p.name, "sku": p.sku, "image_url": p.image_url,
                      "category_id": p.category_id, "unit_price": num(p.price), "quantity": i.quantity,
                      "sub_total": num(i.sub_total()), "stock": stock, "available": p.is_visible() and stock >= i.quantity})
    return {"id": c.id, "items": items, "item_count": sum(i["quantity"] for i in items),
            "subtotal": num(c.subtotal())}


def quote_json(q: dict) -> dict:
    return {"lines": [{"product_id": l["product"].id, "name": l["product"].name, "image_url": l["product"].image_url,
                       "quantity": l["quantity"], "unit_price": num(l["unit_price"]),
                       "sub_total": num(l["sub_total"]), "problem": l["problem"]} for l in q["lines"]],
            "subtotal": num(q["subtotal"]), "discount": num(q["discount"]), "shipping_fee": num(q["shipping_fee"]),
            "total": num(q["total"]), "promo_code": q["promo_code"], "promo_error": q["promo_error"],
            "issues": q["issues"], "can_checkout": q["can_checkout"]}


def payment_json(p) -> dict | None:
    if p is None:
        return None
    return {"method": p.method, "amount": num(p.amount), "status": p.status,
            "transaction_id": p.transaction_id, "paid_at": iso(p.paid_at)}


def shipment_json(s) -> dict | None:
    if s is None:
        return None
    return {"carrier": s.carrier, "tracking_number": s.tracking_number, "status": s.status,
            "delivery_date": iso(s.delivery_date)}


def pay_seconds_left(o) -> int | None:
    """Seconds until an unpaid online order expires (BR-04), measured on the server clock."""
    if o.status != "PENDING_PAYMENT":
        return None
    left = o.created_at + timedelta(minutes=config.UNPAID_ORDER_TIMEOUT_MINUTES) - datetime.now()
    return max(int(left.total_seconds()), 0)


def order_json(o, detail: bool = False, reviewed: set[int] | None = None) -> dict:
    out = {"id": o.id, "status": o.status, "payment_method": o.payment_method, "customer_id": o.customer_id,
           "subtotal": num(o.subtotal), "discount": num(o.discount), "shipping_fee": num(o.shipping_fee),
           "total_amount": num(o.total_amount), "item_count": o.item_count(), "created_at": iso(o.created_at),
           "ship_recipient": o.ship_recipient, "ship_phone": o.ship_phone, "ship_address": o.ship_address,
           "can_cancel": o.can_be_cancelled(), "pay_seconds_left": pay_seconds_left(o), "payment": payment_json(o.payment), "shipment": shipment_json(o.shipment),
           "items": [{"product_id": i.product_id, "name": i.product.name, "sku": i.product.sku,
                      "image_url": i.product.image_url, "quantity": i.quantity, "unit_price": num(i.unit_price),
                      "sub_total": num(i.sub_total()), "reviewed": i.product_id in (reviewed or set())}
                     for i in sorted(o.items, key=lambda i: i.product_id)]}
    if detail:
        out["history"] = [{"from_status": h.from_status, "to_status": h.to_status, "changed_by": h.changed_by,
                           "changed_at": iso(h.changed_at)} for h in sorted(o.history, key=lambda h: h.id)]
    return out


def inventory_json(i) -> dict:
    out = {"product_id": i.product_id, "quantity": i.quantity, "min_threshold": i.min_threshold, "low": i.is_low()}
    if "product" in i.__dict__ and i.product is not None:
        out |= {"name": i.product.name, "sku": i.product.sku, "status": i.product.status}
    return out


def account_json(a) -> dict:
    return {"id": a.id, "email": a.email, "role": a.role.name, "status": a.status}


def customer_json(c, account) -> dict:
    return {"id": c.id, "email": account.email, "first_name": c.first_name, "middle_name": c.middle_name,
            "last_name": c.last_name, "full_name": c.full_name(), "phone": c.phone,
            "loyalty_tier": c.loyalty_tier, "loyalty_point": c.loyalty_point}


def address_json(a) -> dict:
    return {"id": a.id, "recipient": a.recipient, "phone": a.phone, "street": a.street, "district": a.district,
            "city": a.city, "post_code": a.post_code, "is_default": a.is_default, "one_line": a.one_line()}


def promotion_json(p, used: int | None = None) -> dict:
    out = {"id": p.id, "code": p.code, "discount_type": p.discount_type, "discount_value": num(p.discount_value),
           "min_order_value": num(p.min_order_value), "start_at": iso(p.start_at), "end_at": iso(p.end_at),
           "active": p.active}
    if used is not None:
        out["used_count"] = used
    return out


def review_json(r, author: str) -> dict:
    return {"id": r.id, "rating": r.rating, "comment": r.comment, "author": author, "created_at": iso(r.created_at)}


def support_json(s) -> dict:
    return {"id": s.id, "customer_id": s.customer_id, "order_id": s.order_id, "content": s.content,
            "status": s.status, "response": s.response, "handled_by": s.handled_by, "created_at": iso(s.created_at)}


def restock_json(r) -> dict:
    return {"id": r.id, "product_id": r.product_id, "supplier_id": r.supplier_id, "quantity": r.quantity,
            "status": r.status, "created_by": r.created_by, "created_at": iso(r.created_at)}


def deep_money(value):
    """Convert Decimals nested in report dictionaries."""
    if isinstance(value, Decimal):
        return num(value)
    if isinstance(value, dict):
        return {k: deep_money(v) for k, v in value.items()}
    if isinstance(value, list):
        return [deep_money(v) for v in value]
    return value
