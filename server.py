"""
Nimbus Furniture MCP Server — Standalone HTTP Service
Pure MongoDB Atlas architecture.
Exposes product catalog, order management, and customer lookup tools via FastMCP.

Deploy independently on Render/Railway as its own web service.
Start locally with: python server.py

Environment variables:
  MONGODB_URI       — MongoDB Atlas connection URI
  MONGODB_DB_NAME   — Database name (default: nimbus_db)
  MCP_SERVER_PORT   — Port to bind (default: 8001)
  MCP_SERVER_HOST   — Host to bind (default: 0.0.0.0)
"""

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import certifi
from dotenv import load_dotenv
from fastmcp import FastMCP
from pymongo import MongoClient

# ── Load environment variables ────────────────────────────────────────────────
# Check local .env first, then nimbus_agent/.env
_CURRENT_DIR = Path(__file__).parent
load_dotenv(_CURRENT_DIR / ".env")
load_dotenv(_CURRENT_DIR.parent / "nimbus_agent" / ".env")

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "nimbus_db")
MCP_PORT = int(os.getenv("MCP_SERVER_PORT", "8001"))
MCP_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")

# ── MongoDB Client & State ────────────────────────────────────────────────────
_mongo_client: Optional[MongoClient] = None
_db = None
_products_col = None
_orders_col = None
_users_col = None
_mongo_ready = False


def _init_mongodb():
    global _mongo_client, _db, _products_col, _orders_col, _users_col, _mongo_ready
    if not MONGODB_URI:
        print("[mcp-db] Warning: MONGODB_URI not found in environment.")
        _mongo_ready = False
        return

    try:
        _mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where()
        )
        _mongo_client.admin.command("ping")
        _db = _mongo_client[MONGODB_DB_NAME]
        _products_col = _db["products"]
        _orders_col = _db["orders"]
        _users_col = _db["users"]
        _mongo_ready = True
        print(f"[mcp-db] Connected directly to MongoDB Atlas ({MONGODB_DB_NAME}).")
    except Exception as exc:
        print(f"[mcp-db] MongoDB Atlas connection failed ({exc}).")
        _mongo_ready = False


# Initialize MongoDB Atlas on module load
_init_mongodb()

# ── FastMCP Server Instance ───────────────────────────────────────────────────
mcp = FastMCP("nimbus-mcp-server")


# ── Product Database Helpers ──────────────────────────────────────────────────
def _find_product(identifier: str) -> Optional[dict]:
    """Find product by product_id or product name (case-insensitive) in MongoDB Atlas."""
    ident = identifier.strip()
    if not ident or _products_col is None:
        return None

    try:
        # 1. Exact product_id match
        prod = _products_col.find_one({"product_id": {"$regex": f"^{re.escape(ident)}$", "$options": "i"}})
        if prod:
            prod.pop("_id", None)
            return prod

        # 2. Exact product name match
        prod = _products_col.find_one({"product": {"$regex": f"^{re.escape(ident)}$", "$options": "i"}})
        if prod:
            prod.pop("_id", None)
            return prod

        # 3. Substring match on product name
        prod = _products_col.find_one({"product": {"$regex": re.escape(ident), "$options": "i"}})
        if prod:
            prod.pop("_id", None)
            return prod
    except Exception as e:
        print(f"[mcp-db] MongoDB product search error: {e}")
    return None


def _update_product_stock(product_id: str, delta: int) -> bool:
    """Increment/decrement product stock directly in MongoDB Atlas."""
    if _products_col is None:
        return False
    try:
        prod = _products_col.find_one({"product_id": product_id})
        if prod:
            new_stock = max(0, prod.get("stock", 0) + delta)
            _products_col.update_one(
                {"product_id": product_id},
                {"$set": {"stock": new_stock, "in_stock": new_stock > 0}}
            )
            return True
    except Exception as e:
        print(f"[mcp-db] MongoDB stock update error: {e}")
    return False


# ── MCP Tools: Products ───────────────────────────────────────────────────────
@mcp.tool
def list_products(category: str = "", query: str = "", limit: int = 30) -> list[dict]:
    """
    Search and list products from the Nimbus furniture catalog in MongoDB Atlas.
    Optionally filter by category (e.g. 'Chairs', 'Desks', 'Sofas & Seating', 'Tables',
    'Storage & Shelves', 'Beds & Mattresses', 'Lighting', 'Home Decor', 'Outdoor', 'Accessories')
    or search query matching product name/material/description.
    """
    if _products_col is None:
        return []

    category_filter = (category or "").strip()
    query_filter = (query or "").strip()
    try:
        limit_num = int(limit)
    except (ValueError, TypeError):
        limit_num = 30

    try:
        mongo_query: dict[str, Any] = {}
        if category_filter:
            mongo_query["category"] = {"$regex": re.escape(category_filter), "$options": "i"}
        if query_filter:
            mongo_query["$or"] = [
                {"product": {"$regex": re.escape(query_filter), "$options": "i"}},
                {"description": {"$regex": re.escape(query_filter), "$options": "i"}},
                {"material": {"$regex": re.escape(query_filter), "$options": "i"}},
            ]

        cursor = _products_col.find(mongo_query).limit(limit_num)
        results = []
        for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results
    except Exception as e:
        print(f"[mcp-db] MongoDB list_products error: {e}")
        return []


@mcp.tool
def get_product_details(product_identifier: str) -> dict:
    """
    Retrieve comprehensive specifications and stock status for a specific furniture product
    from MongoDB Atlas by product name or product ID (e.g. 'chair', 'Nimbus Ergonomic Task Chair', 'PROD-001').
    """
    prod = _find_product(product_identifier)
    if prod:
        return {
            "found": True,
            "product_id": prod.get("product_id"),
            "product": prod.get("product"),
            "price": prod.get("price"),
            "price_num": prod.get("price_num"),
            "category": prod.get("category"),
            "description": prod.get("description"),
            "material": prod.get("material"),
            "color": prod.get("color"),
            "dimensions": prod.get("dimensions"),
            "stock": prod.get("stock"),
            "in_stock": prod.get("in_stock", True),
            "rating": prod.get("rating"),
            "reviews_count": prod.get("reviews_count"),
            "warranty": prod.get("warranty"),
        }
    return {
        "found": False,
        "error": f"No product found matching '{product_identifier}'. You can use list_products to browse available items."
    }


# ── MCP Tools: Orders ─────────────────────────────────────────────────────────
@mcp.tool
def place_order(
    customer_email: str,
    product_name: str,
    quantity: int = 1,
    shipping_address: str = "742 Evergreen Terrace, Springfield",
    customer_name: str = "",
) -> dict:
    """
    Place a new furniture order on behalf of the user directly in MongoDB Atlas.
    Records the mock order in the MongoDB orders collection with structure:
    order_id, customer_email, customer_name, items (product_id, product, price, quantity),
    total_amount, total_price_num, and shipping_address.

    Parameters:
      - customer_email: Email address of the customer placing the order (required).
      - product_name: Name of the product or product ID (e.g. 'chair', 'Nimbus Ergonomic Task Chair', 'PROD-001').
      - quantity: Number of units to order (default: 1).
      - shipping_address: Delivery address for the order.
      - customer_name: Optional customer name.
    """
    if _orders_col is None:
        return {"success": False, "error": "MongoDB Atlas connection not available."}

    email_clean = (customer_email or "").strip().lower()
    if not email_clean or "@" not in email_clean:
        return {
            "success": False,
            "error": "A valid customer_email address is required to place an order.",
        }

    prod_name_clean = (product_name or "").strip()
    if not prod_name_clean:
        return {
            "success": False,
            "error": "product_name is required to place an order.",
        }

    try:
        qty = int(quantity)
    except (ValueError, TypeError):
        qty = 1
    if qty <= 0:
        qty = 1

    # 1. Lookup Product in MongoDB Atlas
    prod = _find_product(prod_name_clean)
    if not prod:
        return {
            "success": False,
            "error": f"Product '{prod_name_clean}' not found in the catalog. Call list_products to view available furniture.",
        }

    available_stock = prod.get("stock", 0)
    if available_stock < qty:
        return {
            "success": False,
            "error": f"Insufficient stock for '{prod.get('product')}'. Requested: {qty}, Available: {available_stock}.",
            "product": prod.get("product"),
            "available_stock": available_stock,
        }

    # 2. Calculate Pricing
    unit_price_str = prod.get("price", "200rs")
    unit_price_num = prod.get("price_num")
    if unit_price_num is None:
        match = re.search(r"\d+", unit_price_str)
        unit_price_num = int(match.group()) if match else 200

    total_price_num = unit_price_num * qty
    total_amount_str = f"{total_price_num}rs"

    # 3. Generate Order ID
    order_suffix = uuid.uuid4().hex[:6].upper()
    date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    order_id = f"ORD-{date_prefix}-{order_suffix}"

    c_name = (customer_name or "").strip()
    if not c_name:
        user_info = get_user_by_email(email_clean)
        if user_info.get("found"):
            c_name = user_info.get("name", "Customer")
        else:
            c_name = email_clean.split("@")[0].replace(".", " ").title()

    addr = (shipping_address or "").strip() or "742 Evergreen Terrace, Springfield"

    order_doc = {
        "order_id": order_id,
        "customer_email": email_clean,
        "customer_name": c_name,
        "items": [
            {
                "product_id": prod.get("product_id"),
                "product": prod.get("product"),
                "price": unit_price_str,
                "quantity": qty,
            }
        ],
        "total_amount": total_amount_str,
        "total_price_num": total_price_num,
        "shipping_address": addr,
    }

    # 4. Save Order directly to MongoDB Atlas
    try:
        _orders_col.insert_one(dict(order_doc))
    except Exception as e:
        return {"success": False, "error": f"Failed to save order to MongoDB Atlas: {e}"}

    # 5. Decrement Inventory in MongoDB Atlas
    _update_product_stock(prod.get("product_id"), -qty)

    # 6. Update User total_orders count if user exists in MongoDB Atlas
    if _users_col is not None:
        try:
            _users_col.update_one(
                {"email": {"$regex": f"^{re.escape(email_clean)}$", "$options": "i"}},
                {"$inc": {"total_orders": 1}}
            )
        except Exception as e:
            print(f"[mcp-db] Error updating user order count: {e}")

    return {
        "success": True,
        "order_id": order_id,
        "customer_email": email_clean,
        "customer_name": c_name,
        "items": order_doc["items"],
        "total_amount": total_amount_str,
        "total_price_num": total_price_num,
        "shipping_address": addr,
    }


@mcp.tool
def order_on_behalf_of_user(
    customer_email: str,
    product_name: str,
    quantity: int = 1,
    shipping_address: str = "742 Evergreen Terrace, Springfield",
    customer_name: str = "",
) -> dict:
    """
    Order a product on behalf of the customer/user directly in MongoDB Atlas.
    Creates a mock order record in MongoDB with structure:
    order_id, customer_email, customer_name, items ([product_id, product, price, quantity]),
    total_amount, total_price_num, and shipping_address.
    """
    return place_order(
        customer_email=customer_email,
        product_name=product_name,
        quantity=quantity,
        shipping_address=shipping_address,
        customer_name=customer_name,
    )


@mcp.tool
def get_order_by_id(order_id: str) -> dict:
    """
    Look up order details and items by unique order ID directly from MongoDB Atlas.
    """
    oid = (order_id or "").strip()
    if not oid or _orders_col is None:
        return {"found": False, "error": "order_id is required or database unavailable."}

    try:
        order = _orders_col.find_one({"order_id": {"$regex": f"^{re.escape(oid)}$", "$options": "i"}})
        if order:
            order.pop("_id", None)
            order["found"] = True
            return order
    except Exception as e:
        print(f"[mcp-db] MongoDB order lookup error: {e}")

    return {"found": False, "error": f"No order found with order_id '{oid}'."}


@mcp.tool
def get_customer_orders(customer_email: str) -> list[dict]:
    """
    Retrieve all placed orders for a customer by their email address directly from MongoDB Atlas.
    """
    email_clean = (customer_email or "").strip().lower()
    if not email_clean or _orders_col is None:
        return []

    try:
        cursor = _orders_col.find(
            {"customer_email": {"$regex": f"^{re.escape(email_clean)}$", "$options": "i"}}
        )
        orders = []
        for doc in cursor:
            doc.pop("_id", None)
            orders.append(doc)
        return orders
    except Exception as e:
        print(f"[mcp-db] MongoDB customer orders lookup error: {e}")
        return []


@mcp.tool
def delete_order(order_id: str) -> dict:
    """
    Remove an order from MongoDB Atlas orders collection by order_id.
    """
    oid = (order_id or "").strip()
    if not oid or _orders_col is None:
        return {"success": False, "error": "order_id is required or database unavailable."}

    try:
        res = _orders_col.delete_one({"order_id": {"$regex": f"^{re.escape(oid)}$", "$options": "i"}})
        if res.deleted_count > 0:
            return {"success": True, "message": f"Order '{oid}' removed successfully from MongoDB Atlas."}
    except Exception as e:
        print(f"[mcp-db] MongoDB delete order error: {e}")

    return {"success": False, "error": f"Order '{oid}' not found."}


@mcp.tool
def clear_all_orders() -> dict:
    """
    Remove all orders from MongoDB Atlas orders collection.
    """
    if _orders_col is None:
        return {"success": False, "error": "MongoDB Atlas connection not available."}
    try:
        res = _orders_col.delete_many({})
        return {"success": True, "message": f"Cleared {res.deleted_count} orders from MongoDB Atlas."}
    except Exception as e:
        return {"success": False, "error": f"MongoDB clear orders error: {e}"}


# ── MCP Tools: User Account Lookups ───────────────────────────────────────────
@mcp.tool
def get_user_by_email(email: str) -> dict:
    """
    Look up a Nimbus Furniture customer account by email address from MongoDB Atlas.
    Returns the user record including name, plan, account_status, created_at, and total_orders.
    """
    clean_email = email.strip().lower()
    if not clean_email or _users_col is None:
        return {"found": False, "error": "Email address cannot be empty or database unavailable."}

    try:
        user = _users_col.find_one({"email": {"$regex": f"^{re.escape(clean_email)}$", "$options": "i"}})
        if user:
            return {
                "found": True,
                "id": user.get("id", user.get("user_id")),
                "name": user.get("name"),
                "email": user.get("email"),
                "plan": user.get("plan", "free"),
                "account_status": user.get("account_status", "active"),
                "created_at": user.get("created_at", ""),
                "total_orders": user.get("total_orders", 0),
            }
    except Exception as e:
        print(f"[mcp-db] MongoDB user lookup error: {e}")

    return {
        "found": False,
        "error": f"No Nimbus Furniture account found for email: {clean_email}",
    }


@mcp.tool
def get_user_account_status(user_id: str) -> dict:
    """
    Retrieve the account plan and status details for a customer by user ID from MongoDB Atlas.
    Returns plan type, account status, and (if suspended) the suspension reason.
    """
    clean_id = user_id.strip()
    if not clean_id or _users_col is None:
        return {"found": False, "error": "user_id cannot be empty or database unavailable."}

    try:
        user = _users_col.find_one({"id": clean_id})
        if not user:
            user = _users_col.find_one({"user_id": clean_id})
        if user:
            result = {
                "found": True,
                "id": user.get("id", clean_id),
                "name": user.get("name"),
                "plan": user.get("plan"),
                "account_status": user.get("account_status"),
            }
            if user.get("account_status") == "suspended" and "suspension_reason" in user:
                result["suspension_reason"] = user["suspension_reason"]

            if user.get("plan") == "premium":
                result["plan_details"] = (
                    "Nimbus Premium: free standard shipping on all furniture orders, "
                    "free White Glove Delivery & assembly on large items, "
                    "10% member discount on all products, early access to new collections and sales, "
                    "priority support, and free access to the Nimbus Design Concierge. $9.99/month or $89.99/year."
                )
            else:
                result["plan_details"] = (
                    "Nimbus Free: standard shipping rates apply, White Glove Delivery available for $49/item, "
                    "regular support. Upgrade to Nimbus Premium for $9.99/month to unlock free shipping, "
                    "assembly, a 10% discount, and the Design Concierge service."
                )
            return result
    except Exception as e:
        print(f"[mcp-db] MongoDB user_id lookup error: {e}")

    return {
        "found": False,
        "error": f"No Nimbus Furniture account found for user_id: {clean_id}",
    }


# ── Server Startup ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[mcp] Starting Nimbus MCP Server on {MCP_HOST}:{MCP_PORT}...")
    print(f"[mcp] MongoDB Status: {'Connected to Atlas' if _mongo_ready else 'Connection Failed'}")
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
