"""
Dashboard REST API — runs on the bot hoster alongside main.py.
The static dashboard HTML (dashboard/index.html) is hosted separately
and makes requests to this server using the DASHBOARD_SECRET env var.
"""
import os
import uuid
import json
import socket
import aiohttp
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv
from database import Database

load_dotenv()

# Define Permission Levels
ROLE_LEVELS = {"admin": 3, "staff": 2, "viewer": 1}

def has_perm(request, required_role):
    user_role = request.get("user_role", "viewer")
    return ROLE_LEVELS.get(user_role, 0) >= ROLE_LEVELS.get(required_role, 0)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
DB_PATH = BASE_DIR / "GVRY_database.db"
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "changeme-set-DASHBOARD_SECRET-in-env")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def json_response(data, status=200):
    resp = web.Response(
        text=json.dumps(data, default=str),
        status=status,
        content_type="application/json"
    )
    return resp

def get_role_for_token(request, token_header):
    """Extracts token and matches it to a role from config or env fallback."""
    token = token_header.replace("Bearer ", "").strip()
    if not token:
        return None
    
    bot = request.app.get("bot")
    auth_map = bot.config.get("api", {}).get("dashboard_auth", {}) if bot else {}
    if token in auth_map:
        return auth_map[token]
    
    # Fallback to .env secret as admin
    return "admin" if token == DASHBOARD_SECRET else None


# ---------------------------------------------------------------------------
# Global Middleware (CORS + Auth)
# ---------------------------------------------------------------------------

@web.middleware
async def global_middleware(request: web.Request, handler):
    # 1. Handle CORS Preflight (OPTIONS)
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        # 2. Check Auth for API routes
        if request.path.startswith("/api/"):
            role = get_role_for_token(request, request.headers.get("Authorization", ""))
            if not role:
                resp = json_response({"error": "Unauthorized"}, status=401)
            else:
                request["user_role"] = role
                resp = await handler(request)
        else:
            # Non-API routes (static files)
            resp = await handler(request)

    # 3. Apply CORS headers to ALL responses
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

async def get_config(request: web.Request):
    if not has_perm(request, "admin"):
        return json_response({"error": "Forbidden: Admin required"}, status=403)
    return json_response(load_config())

async def post_config(request: web.Request):
    if not has_perm(request, "admin"):
        return json_response({"error": "Forbidden: Admin required"}, status=403)
    try:
        data = await request.json()
        save_config(data)
        bot = request.app.get("bot")
        if bot:
            bot.config = data
        return json_response({"success": True})
    except Exception as e:
        return json_response({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

async def get_stats(request: web.Request):
    if not has_perm(request, "viewer"):
        return json_response({"error": "Forbidden"}, status=403)
        
    citations_unpaid_res = await Database.fetch_one("SELECT COUNT(*) as c FROM citations WHERE status='Unpaid'")
    citations_total_res = await Database.fetch_one("SELECT COUNT(*) as c FROM citations")
    sessions_total_res = await Database.fetch_one("SELECT COUNT(*) as c FROM staff_sessions")
    mod_total_res = await Database.fetch_one("SELECT COUNT(*) as c FROM moderation")
    economy_users_res = await Database.fetch_one("SELECT COUNT(*) as c FROM economy")
    total_wallet_res = await Database.fetch_one("SELECT COALESCE(SUM(wallet),0) as s FROM economy")
    total_bank_res = await Database.fetch_one("SELECT COALESCE(SUM(bank),0) as s FROM economy")
    vehicles_total_res = await Database.fetch_one("SELECT COUNT(*) as c FROM vehicles")

    bot = request.app.get("bot")
    return json_response({
        "citations_unpaid": citations_unpaid_res["c"],
        "citations_total": citations_total_res["c"],
        "sessions_total": sessions_total_res["c"],
        "moderation_total": mod_total_res["c"],
        "economy_users": economy_users_res["c"],
        "total_wallet": total_wallet_res["s"],
        "total_bank": total_bank_res["s"],
        "vehicles_total": vehicles_total_res["c"],
        "latency": round(bot.latency * 1000) if bot else 0,
        "guilds": len(bot.guilds) if bot else 0,
        "users": sum(g.member_count for g in bot.guilds) if bot else 0,
        "role": request.get("user_role", "viewer")
    })

async def get_logs(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    bot = request.app.get("bot")
    logs = list(bot.log_buffer) if bot else []
    return json_response({"logs": logs})

async def get_guild_data(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    bot = request.app.get("bot")
    if not bot or not bot.guilds: return json_response({"error": "No guild"}, status=404)
    guild = bot.guilds[0] 
    roles = [{"id": r.id, "name": r.name, "color": str(r.color), "members": len(r.members)} for r in guild.roles]
    return json_response({
        "name": guild.name,
        "id": guild.id,
        "icon": str(guild.icon.url) if guild.icon else None,
        "member_count": guild.member_count,
        "roles": sorted(roles, key=lambda x: x['members'], reverse=True)
    })

async def db_action(request: web.Request):
    if not has_perm(request, "admin"):
        return json_response({"error": "Forbidden: Admin required"}, status=403)
    data = await request.json()
    action = data.get("action")
    
    if action == "vacuum": 
        await Database.execute("VACUUM")
    elif action == "clear_mod_logs":
        await Database.execute("DELETE FROM moderation")
    elif action == "clear_sessions":
        await Database.execute("DELETE FROM staff_sessions")
    elif action == "clear_unpaid_citations":
        await Database.execute("DELETE FROM citations WHERE status='Unpaid'")
    elif action == "restart":
        os._exit(0)
        
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

async def get_sessions(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    rows = await Database.fetch_all("SELECT * FROM staff_sessions ORDER BY id DESC")
    return json_response(rows)

async def update_session(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    sid = request.match_info["id"]
    data = await request.json()
    await Database.execute(
        "UPDATE staff_sessions SET user_id=?, session_type=?, session_date=?, start_time=?, end_time=?, notes=? WHERE id=?",
        (data.get("user_id"), data.get("session_type"), data.get("session_date"),
            data.get("start_time"), data.get("end_time"), data.get("notes"), sid)
    )
    return json_response({"success": True})

async def delete_session(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    await Database.execute("DELETE FROM staff_sessions WHERE id=?", (request.match_info["id"],))
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------

async def get_citations(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    rows = await Database.fetch_all("SELECT * FROM citations ORDER BY rowid DESC")
    return json_response(rows)

async def update_citation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    cid = request.match_info["id"]
    data = await request.json()
    await Database.execute(
        "UPDATE citations SET user_id=?, department=?, reason=?, penal_code=?, price=?, "
        "officer_id=?, status=?, vehicle_make=?, vehicle_model=?, vehicle_color=?, vehicle_plate=? WHERE id=?",
        (data.get("user_id"), data.get("department"), data.get("reason"),
         data.get("penal_code"), data.get("price"), data.get("officer_id"),
         data.get("status"), data.get("vehicle_make"), data.get("vehicle_model"),
         data.get("vehicle_color"), data.get("vehicle_plate"), cid)
    )
    return json_response({"success": True})

async def delete_citation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    await Database.execute("DELETE FROM citations WHERE id=?", (request.match_info["id"],))
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# Moderation
# ---------------------------------------------------------------------------

async def get_moderation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    rows = await Database.fetch_all("SELECT * FROM moderation ORDER BY timestamp DESC")
    return json_response(rows)

async def update_moderation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    mid = request.match_info["id"]
    data = await request.json()
    await Database.execute(
        "UPDATE moderation SET user_id=?, type=?, reason=?, proof=?, moderator_id=?, "
        "timestamp=?, cleared=?, cleared_by=?, cleared_reason=? WHERE id=?",
        (data.get("user_id"), data.get("type"), data.get("reason"), data.get("proof"),
         data.get("moderator_id"), data.get("timestamp"), data.get("cleared"),
         data.get("cleared_by"), data.get("cleared_reason"), mid)
    )
    return json_response({"success": True})

async def delete_moderation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    await Database.execute("DELETE FROM moderation WHERE id=?", (request.match_info["id"],))
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------

async def get_economy(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    rows = await Database.fetch_all("SELECT * FROM economy ORDER BY wallet DESC")
    return json_response(rows)

async def update_economy(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    user_id = request.match_info["user_id"]
    data = await request.json()
    await Database.execute(
        "INSERT INTO economy (user_id, wallet, bank) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET wallet=excluded.wallet, bank=excluded.bank",
        (user_id, int(data.get("wallet", 0)), int(data.get("bank", 0)))
    )
    return json_response({"success": True})

async def delete_economy(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    await Database.execute("DELETE FROM economy WHERE user_id=?", (request.match_info["user_id"],))
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

async def get_vehicles(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    rows = await Database.fetch_all("SELECT * FROM vehicles ORDER BY id DESC")
    return json_response(rows)

async def update_vehicle(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    vid = request.match_info["id"]
    data = await request.json()
    await Database.execute(
        "UPDATE vehicles SET user_id=?, year=?, make=?, model=?, color=?, plate=? WHERE id=?",
        (data.get("user_id"), data.get("year"), data.get("make"),
         data.get("model"), data.get("color"), data.get("plate"), vid)
    )
    return json_response({"success": True})

async def delete_vehicle(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    await Database.execute("DELETE FROM vehicles WHERE id=?", (request.match_info["id"],))
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# Ticket Panel Trigger
# ---------------------------------------------------------------------------

async def create_session(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    data = await request.json()
    await Database.execute(
        "INSERT INTO staff_sessions (user_id, session_type, session_date, start_time, end_time, notes) VALUES (?,?,?,?,?,?)",
        (data.get("user_id"), data.get("session_type", "Host"), data.get("session_date"),
         data.get("start_time"), data.get("end_time"), data.get("notes"))
    )
    return json_response({"success": True})


async def create_citation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    data = await request.json()
    cid = data.get("id") or f"GVRY-{uuid.uuid4().hex[:6].upper()}"
    await Database.execute(
        "INSERT OR IGNORE INTO citations (id, user_id, department, reason, penal_code, price, officer_id, status, vehicle_make, vehicle_model, vehicle_color, vehicle_plate) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, data.get("user_id"), data.get("department"), data.get("reason"),
         data.get("penal_code"), int(data.get("price", 0)), data.get("officer_id"),
         data.get("status", "Unpaid"), data.get("vehicle_make"), data.get("vehicle_model"),
         data.get("vehicle_color"), data.get("vehicle_plate"))
    )
    return json_response({"success": True, "id": cid})


async def create_moderation(request: web.Request):
    if not has_perm(request, "staff"):
        return json_response({"error": "Forbidden: Staff required"}, status=403)
    data = await request.json()
    mid = data.get("id") or f"MOD-{uuid.uuid4().hex[:6].upper()}"
    await Database.execute(
        "INSERT OR IGNORE INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp, cleared, cleared_by, cleared_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (mid, data.get("user_id"), data.get("type", "infraction"), data.get("reason"),
         data.get("proof"), data.get("moderator_id"), data.get("timestamp", ""),
         int(data.get("cleared", 0)), data.get("cleared_by"), data.get("cleared_reason"))
    )
    return json_response({"success": True, "id": mid})


# ---------------------------------------------------------------------------
# Ticket Panel Trigger
# ---------------------------------------------------------------------------

async def post_send_ticket_panel(request: web.Request):
    if not has_perm(request, "admin"):
        return json_response({"error": "Forbidden: Admin required"}, status=403)
        
    bot = request.app.get("bot")
    if not bot:
        return json_response({"error": "Bot not available"}, status=500)
    
    try:
        from commands.tickets import TicketPanelView
    except ImportError:
        from tickets import TicketPanelView

    cfg = bot.config.get('tickets', {})
    target_id = cfg.get('panel_channel_id')
    target_channel = bot.get_channel(int(target_id)) if target_id else None
    
    if not target_channel:
        return json_response({"error": f"Target channel ID {target_id} not found."}, status=404)

    embed = bot.format_embed(bot.config, 'ticket_panel')
    await target_channel.send(embed=embed, view=TicketPanelView(bot.config))
    return json_response({"success": True})


# ---------------------------------------------------------------------------
# App factory + startup
# ---------------------------------------------------------------------------

def create_app(bot=None) -> web.Application:
    app = web.Application(middlewares=[global_middleware])
    app["bot"] = bot

    app.router.add_route("OPTIONS", "/{tail:.*}", lambda r: web.Response(status=204))

    app.router.add_get("/api/stats",        get_stats)

    app.router.add_get("/api/config",       get_config)
    app.router.add_post("/api/config",      post_config)

    app.router.add_get("/api/logs",         get_logs)
    app.router.add_get("/api/guild/data",   get_guild_data)
    app.router.add_post("/api/db/action",   db_action)

    app.router.add_get("/api/sessions",              get_sessions)
    app.router.add_post("/api/sessions",             create_session)
    app.router.add_put("/api/sessions/{id}",         update_session)
    app.router.add_delete("/api/sessions/{id}",      delete_session)

    app.router.add_get("/api/citations",             get_citations)
    app.router.add_post("/api/citations",            create_citation)
    app.router.add_put("/api/citations/{id}",        update_citation)
    app.router.add_delete("/api/citations/{id}",     delete_citation)

    app.router.add_get("/api/moderation",            get_moderation)
    app.router.add_post("/api/moderation",           create_moderation)
    app.router.add_put("/api/moderation/{id}",       update_moderation)
    app.router.add_delete("/api/moderation/{id}",    delete_moderation)

    app.router.add_get("/api/economy",               get_economy)
    app.router.add_put("/api/economy/{user_id}",     update_economy)
    app.router.add_delete("/api/economy/{user_id}",  delete_economy)

    app.router.add_get("/api/vehicles",              get_vehicles)
    app.router.add_put("/api/vehicles/{id}",         update_vehicle)
    app.router.add_delete("/api/vehicles/{id}",      delete_vehicle)

    # Ticket Panel Trigger
    app.router.add_post("/api/tickets/send-panel",   post_send_ticket_panel)

    # Explicitly serve the index file at the root to prevent 403 Forbidden errors
    async def serve_index(request):
        return web.FileResponse(BASE_DIR / "dashboard" / "index.html")

    app.router.add_get("/", serve_index)

    # Serve static dashboard files
    if (BASE_DIR / "dashboard").exists():
        app.router.add_static("/", BASE_DIR / "dashboard", append_version=True)

    return app


async def start_dashboard_api(bot=None) -> web.AppRunner:
    cfg = load_config()
    # Railway (and most PaaS) set PORT env var — always prefer it
    port = int(os.getenv("PORT", cfg.get("api", {}).get("port", 8080)))
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    # Log the IP for the user
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    public_ip = "your-public-ip"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org") as resp:
                if resp.status == 200:
                    public_ip = await resp.text()
    except Exception:
        pass

    print(f"\n[Dashboard API] Online and accessible!")
    print(f" - Local Network: http://{local_ip}:{port}")
    print(f" - External Access: http://{public_ip}:{port}")
    print(f"Note: Ensure port {port} is forwarded on your router for external access.\n")
    
    return runner
