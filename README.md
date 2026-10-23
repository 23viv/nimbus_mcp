# 🔧 Nimbus MCP Server

Standalone **Model Context Protocol (MCP)** HTTP server for the Nimbus Furniture platform.

Built with **FastMCP** and integrated directly with **MongoDB Atlas** (pure cloud database operations, no local file fallbacks). Exposes live tools to query products, place and manage orders, and retrieve customer account profiles.

---

## 🌟 Capabilities & Exposed Tools

| Tool | Category | Description |
|---|---|---|
| `place_order` | Orders | Place a new furniture order into MongoDB Atlas (updates inventory, calculates total, generates tracking) |
| `get_order_by_id` | Orders | Retrieve order tracking, delivery estimate, item breakdown, and status by order ID |
| `get_customer_orders` | Orders | Retrieve full order history for a customer by email |
| `cancel_order` | Orders | Cancel an order and automatically restore stock to the product catalog |
| `list_products` | Products | Browse furniture catalog with category and keyword search filters |
| `get_product_details` | Products | Get full specs, dimensions, materials, stock count, and price for a product |
| `get_user_by_email` | Accounts | Look up customer account details, membership plan, and order history count |
| `get_user_account_status` | Accounts | Retrieve plan details (Free vs. Premium) and account status/suspensions |

---

## 🗄️ MongoDB Collections

The server operates against the `nimbus_db` database on MongoDB Atlas:

### 1. `products` Collection (30 Fake Furniture Items)
Contains 30 high-detail furniture records across Chairs, Desks, Sofas, Tables, Storage, Beds, Lighting, and Outdoor.
Includes the requested items and schemas:
```json
{
  "product_id": "PROD-001",
  "product": "chair",
  "price": "200rs",
  "price_num": 200,
  "category": "Chairs",
  "description": "Versatile lightweight minimalist stacking chair, ideal for dining or home study.",
  "material": "Molded Polymer & Powder-Coated Steel Legs",
  "color": "Matte White",
  "dimensions": "32H x 18W x 18D inches",
  "stock": 50,
  "in_stock": true,
  "rating": 4.5,
  "reviews_count": 89,
  "warranty": "1-Year Warranty"
}
```

### 2. `orders` Collection
Tracks all customer orders placed through the MCP server (simplified mock schema):
```json
{
  "_id": {
    "$oid": "6adb6cba92bd13bd47018b6f"
  },
  "order_id": "ORD-20260801-7102",
  "customer_email": "sarah.chen@example.com",
  "customer_name": "Sarah Chen",
  "items": [
    {
      "product_id": "PROD-002",
      "product": "Nimbus Ergonomic Task Chair",
      "price": "4500rs",
      "quantity": 1
    }
  ],
  "total_amount": "4500rs",
  "total_price_num": 4500,
  "shipping_address": "742 Evergreen Terrace, Springfield"
}
```

---

## 🚀 Running the MCP Server

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables (.env)
```env
MONGODB_URI="mongodb+srv://<user>:<password>@cluster0.v3dfdhj.mongodb.net/?appName=Cluster0"
MONGODB_DB_NAME="nimbus_db"
MCP_SERVER_PORT=8001
MCP_SERVER_HOST="0.0.0.0"
```

### 3. Seed Database (Optional — runs automatically on startup if empty)
```bash
python seed_db.py
```

### 4. Start Server
```bash
python server.py
```
Server runs streamable HTTP on `http://127.0.0.1:8001/mcp`.
