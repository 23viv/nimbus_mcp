# 🔧 Nimbus MCP Server

Standalone **Model Context Protocol (MCP)** server for the Nimbus Furniture platform.

Provides live user account lookup tools over HTTP, consumed by the **[nimbus_agent](../nimbus_agent/)** AI support agent.

---

## What is this?

The `nimbus_mcp` service is a lightweight, independently deployable HTTP server that exposes two tools via [FastMCP](https://github.com/jlowin/fastmcp):

| Tool | Description |
|---|---|
| `get_user_by_email` | Look up a Nimbus customer account by email address |
| `get_user_account_status` | Retrieve plan type, account status, and plan details by user ID |

The agent calls these tools at runtime over HTTP using the MCP protocol — keeping live user data completely separate from the AI agent logic.

---

## Project Structure

```
nimbus_mcp/
├── server.py          # FastMCP server — defines and exposes MCP tools
├── data/
│   └── users.json     # Nimbus customer database (8 mock users)
├── requirements.txt   # Minimal dependencies (fastmcp, mcp, python-dotenv)
├── .gitignore
└── README.md
```

---

## Tools Exposed

### `get_user_by_email(email: str) → dict`

Looks up a customer by their email address.

**Returns:**
```json
{
  "found": true,
  "id": "usr_001",
  "name": "Sarah Chen",
  "email": "sarah.chen@example.com",
  "plan": "premium",
  "account_status": "active",
  "last_login": "2026-08-03T10:22:14Z",
  "created_at": "2024-03-15T08:00:00Z",
  "total_orders": 12,
  "store_credit": 25.00
}
```

If not found:
```json
{ "found": false, "error": "No Nimbus Furniture account found for email: x@x.com" }
```

---

### `get_user_account_status(user_id: str) → dict`

Returns plan and status details for a user by ID.

**Returns (Free plan):**
```json
{
  "found": true,
  "id": "usr_002",
  "name": "James Patel",
  "plan": "free",
  "account_status": "active",
  "plan_details": "Nimbus Free: standard shipping rates apply, White Glove Delivery available for $49/item, regular support. Upgrade to Nimbus Premium for $9.99/month..."
}
```

**Returns (Premium plan):**
```json
{
  "found": true,
  "id": "usr_001",
  "name": "Sarah Chen",
  "plan": "premium",
  "account_status": "active",
  "plan_details": "Nimbus Premium: free standard shipping on all furniture orders, free White Glove Delivery & assembly on large items, 10% member discount..."
}
```

**Returns (Suspended):**
```json
{
  "found": true,
  "id": "usr_004",
  "name": "Derek Kim",
  "plan": "free",
  "account_status": "suspended",
  "suspension_reason": "Payment dispute — account under review",
  "plan_details": "..."
}
```

---

## Setup

### 1. Prerequisites

- Python 3.10+

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)

The only configurable variable is the port. Create a `.env` file if needed:

```env
MCP_SERVER_PORT=8001
```

The default port is `8001` if not set.

---

## Running Locally

```bash
python server.py
```

The MCP server starts at:
```
http://127.0.0.1:8001/mcp
```

To verify it's running, check the console output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8001
```

> ⚠️ Always start `nimbus_mcp` **before** `nimbus_agent`. The agent connects to this server on startup and falls back to RAG-only mode if it can't reach it.

---

## Deploying to Render

Deploy as a **Web Service** from your GitHub repo:

| Setting | Value |
|---|---|
| **Root Directory** | `nimbus_mcp` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python server.py` |
| **Port** | `8001` |

**Environment variable to set in Render dashboard:**

```
MCP_SERVER_PORT=8001
```

After deploying, copy the public URL (e.g. `https://nimbus-mcp.onrender.com`) and set the following in your **nimbus_agent** Render service:

```
MCP_SERVER_URL=https://nimbus-mcp.onrender.com/mcp
```

> ⚠️ Deploy `nimbus_mcp` **first**, then deploy `nimbus_agent`. The agent needs the MCP URL to be live at startup.

---

## Updating the User Database

The user data lives in `data/users.json`. Each user record follows this schema:

```json
{
  "id": "usr_001",
  "email": "user@example.com",
  "name": "Full Name",
  "plan": "premium | free",
  "account_status": "active | suspended",
  "last_login": "2026-08-03T10:22:14Z",
  "created_at": "2024-03-15T08:00:00Z",
  "total_orders": 12,
  "store_credit": 25.00,
  "suspension_reason": "Optional — only present if account_status is suspended"
}
```

After editing `users.json`, restart the server — the file is loaded once at startup.

---

## Mock Users (for testing)

| Email | Plan | Status |
|---|---|---|
| sarah.chen@example.com | Premium | Active |
| james.patel@example.com | Free | Active |
| maria.gonzalez@example.com | Premium | Active |
| derek.kim@example.com | Free | **Suspended** |
| linda.wu@example.com | Premium | Active |
| tom.nguyen@example.com | Free | Active |
| aisha.johnson@example.com | Premium | Active |
| carlos.rivera@example.com | Free | Active |

---

## Requirements

```
fastmcp>=2.0.0
mcp>=1.0.0
python-dotenv>=1.0.0
```

---

## License

MIT — free to use, modify, and extend.
