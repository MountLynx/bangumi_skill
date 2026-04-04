#!/usr/bin/env python3
"""
Bangumi Tracker Web - MCP Server Edition
Multi-user deployment with SQLite storage and Web OAuth support
"""

import argparse
import json
import os
import sys
import time
import sqlite3
import secrets
import threading
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, List
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import platform

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Constants
BASE_URL = "https://api.bgm.tv/v0"
OAUTH_URL = "https://bgm.tv/oauth"
DEFAULT_PORT = 17321
DEFAULT_HOST = "0.0.0.0"

# Type mappings
TYPE_MAP = {"anime": 2, "book": 1, "game": 4, "music": 3, "real": 6}
STATUS_MAP = {"wish": 1, "doing": 2, "collect": 3, "on_hold": 4, "dropped": 5}

# Headers
def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "User-Agent": "bangumi-tracker-web/1.0 (https://github.com/MountLynx/bangumi_skill)",
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ============================================================
# Database Layer
# ============================================================

class BangumiDB:
    """SQLite database for users and cache"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bgm_user_id INTEGER UNIQUE,
                bgm_username TEXT UNIQUE NOT NULL,
                nickname TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                client_id TEXT NOT NULL,
                client_secret TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        # OAuth state table (for web OAuth flow)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                redirect_uri TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        # Cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                response_data TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)

        # Rate limits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                endpoint TEXT NOT NULL,
                user_id INTEGER,
                last_request_at INTEGER NOT NULL,
                PRIMARY KEY (endpoint, user_id)
            )
        """)

        # App config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    # User operations
    def save_user(self, user_id: int, username: str, nickname: str, token_data: Dict, client_id: str, client_secret: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        expires_at = int(time.time()) + token_data.get("expires_in", 3600)

        cursor.execute("""
            INSERT OR REPLACE INTO users
            (bgm_user_id, bgm_username, nickname, access_token, refresh_token, expires_at, client_id, client_secret, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
        """, (user_id, username, nickname, token_data["access_token"], token_data["refresh_token"],
              expires_at, client_id, client_secret))
        conn.commit()
        conn.close()

    def get_user(self, username: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE bgm_username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "bgm_user_id": row[1],
                "bgm_username": row[2],
                "nickname": row[3],
                "access_token": row[4],
                "refresh_token": row[5],
                "expires_at": row[6],
                "client_id": row[7],
                "client_secret": row[8]
            }
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE bgm_user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "bgm_user_id": row[1],
                "bgm_username": row[2],
                "nickname": row[3],
                "access_token": row[4],
                "refresh_token": row[5],
                "expires_at": row[6],
                "client_id": row[7],
                "client_secret": row[8]
            }
        return None

    def update_token(self, username: str, token_data: Dict):
        conn = self.get_connection()
        cursor = conn.cursor()
        expires_at = int(time.time()) + token_data.get("expires_in", 3600)
        cursor.execute("""
            UPDATE users SET access_token = ?, refresh_token = ?, expires_at = ?, updated_at = strftime('%s', 'now')
            WHERE bgm_username = ?
        """, (token_data["access_token"], token_data["refresh_token"], expires_at, username))
        conn.commit()
        conn.close()

    def delete_user(self, username: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE bgm_username = ?", (username,))
        conn.commit()
        conn.close()

    def list_users(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bgm_username, nickname, updated_at FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [{"username": r[0], "nickname": r[1], "updated_at": r[2]} for r in rows]

    # OAuth state operations
    def save_oauth_state(self, state: str, client_id: str, redirect_uri: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO oauth_states (state, client_id, redirect_uri, created_at)
            VALUES (?, ?, ?, strftime('%s', 'now'))
        """, (state, client_id, redirect_uri))
        conn.commit()
        conn.close()

    def get_oauth_state(self, state: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, redirect_uri FROM oauth_states WHERE state = ?", (state,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"client_id": row[0], "redirect_uri": row[1]}
        return None

    def delete_oauth_state(self, state: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
        conn.close()

    # Cache operations
    def set_cache(self, key: str, data: Any, ttl_seconds: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute("""
            INSERT OR REPLACE INTO cache (cache_key, response_data, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (key, json.dumps(data), now, now + ttl_seconds))
        conn.commit()
        conn.close()

    def get_cache(self, key: str) -> Optional[Any]:
        conn = self.get_connection()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute("""
            SELECT response_data, expires_at FROM cache WHERE cache_key = ? AND expires_at > ?
        """, (key, now))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None

    def clean_expired_cache(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
        conn.commit()
        conn.close()

    # Rate limiting
    def check_rate_limit(self, endpoint: str, user_id: Optional[int], min_interval: float) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        now = int(time.time())

        cursor.execute("""
            SELECT last_request_at FROM rate_limits WHERE endpoint = ? AND (user_id = ? OR user_id IS NULL)
        """, (endpoint, user_id))
        row = cursor.fetchone()

        if row and (now - row[0]) < min_interval:
            conn.close()
            return False

        cursor.execute("""
            INSERT OR REPLACE INTO rate_limits (endpoint, user_id, last_request_at)
            VALUES (?, ?, ?)
        """, (endpoint, user_id, now))
        conn.commit()
        conn.close()
        return True

    # Config operations
    def set_config(self, key: str, value: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

    def get_config(self, key: str) -> Optional[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None


# ============================================================
# Bangumi API Client
# ============================================================

class BangumiClient:
    """Bangumi API client with caching and rate limiting"""

    def __init__(self, db: BangumiDB):
        self.db = db

    def _request(self, method: str, path: str, data: Optional[Dict] = None,
                 params: Optional[Dict] = None, token: Optional[str] = None) -> Dict:
        """Make HTTP request to Bangumi API"""
        url = f"{BASE_URL}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=get_headers(token), method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else ""
            try:
                error_data = json.loads(body)
                return {"error": f"HTTP {e.code}: {error_data.get('error', e.reason)}", "details": error_data}
            except:
                return {"error": f"HTTP {e.code}: {e.reason}", "details": body}
        except Exception as e:
            return {"error": str(e)}

    def _rate_limit(self, endpoint: str, user_id: Optional[int] = None):
        """Apply rate limiting"""
        intervals = {
            "search": 0.5,
            "subject": 0.5,
            "season": 1.0,
            "collection": 1.0,
            "default": 0.5
        }
        interval = intervals.get(endpoint, intervals["default"])
        while not self.db.check_rate_limit(endpoint, user_id, interval):
            time.sleep(0.1)

    def _get_valid_token(self, username: str) -> Optional[str]:
        """Get valid access token, refresh if expired"""
        user = self.db.get_user(username)
        if not user:
            return None

        # Check if token is expired (with 5 min buffer)
        if user["expires_at"] - time.time() < 300:
            # Refresh token
            config = {"client_id": user["client_id"], "client_secret": user["client_secret"]}
            token_data = self._refresh_token(user["refresh_token"], config)
            if token_data and "access_token" in token_data:
                self.db.update_token(username, token_data)
                return token_data["access_token"]
            return None

        return user["access_token"]

    def _refresh_token(self, refresh_token: str, config: Dict) -> Optional[Dict]:
        """Refresh access token"""
        data = {
            "grant_type": "refresh_token",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": refresh_token
        }
        result = self._request("POST", "/oauth/access_token", data)
        return result if "access_token" in result else None

    # Public API methods
    def search(self, keyword: str, type_: str = "anime", limit: int = 10) -> Dict:
        """Search subjects"""
        self._rate_limit("search")
        cache_key = f"search:{keyword}:{type_}:{limit}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        data = {"keyword": keyword, "limit": limit}
        if type_ and type_ != "all":
            data["type"] = TYPE_MAP.get(type_, 2)

        result = self._request("POST", "/search/subjects", data)
        if "error" not in result:
            self.db.set_cache(cache_key, result, 3600)  # 1 hour
        return result

    def get_subject(self, subject_id: int) -> Dict:
        """Get subject details"""
        self._rate_limit("subject")
        cache_key = f"subject:{subject_id}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        result = self._request("GET", f"/subjects/{subject_id}")
        if "error" not in result:
            self.db.set_cache(cache_key, result, 86400)  # 24 hours
        return result

    def get_episodes(self, subject_id: int, limit: int = 100) -> Dict:
        """Get episodes list"""
        self._rate_limit("subject")
        cache_key = f"episodes:{subject_id}:{limit}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        result = self._request("GET", "/episodes", {"subject_id": subject_id, "limit": limit})
        if "error" not in result:
            self.db.set_cache(cache_key, result, 86400)
        return result

    def get_season(self, year: int, month: int) -> Dict:
        """Get season calendar"""
        self._rate_limit("season")
        cache_key = f"season:{year}:{month}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        result = self._request("GET", "/subjects", {
            "type": 2,
            "year": str(year),
            "month": str(month),
            "sort": "date"
        })
        if "error" not in result:
            self.db.set_cache(cache_key, result, 21600)  # 6 hours
        return result

    def get_rank(self, type_: str = "anime", top: int = 20) -> Dict:
        """Get ranking"""
        self._rate_limit("rank")
        cache_key = f"rank:{type_}:{top}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        params = {"type": TYPE_MAP.get(type_, 2), "sort": "rank", "limit": top}
        result = self._request("GET", "/subjects", params)
        if "error" not in result:
            self.db.set_cache(cache_key, result, 3600)
        return result

    def search_person(self, keyword: str) -> Dict:
        """Search persons"""
        self._rate_limit("search")
        cache_key = f"person:{keyword}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        data = {"keyword": keyword, "limit": 10}
        result = self._request("POST", "/search/persons", data)
        if "error" not in result:
            self.db.set_cache(cache_key, result, 86400)
        return result

    def get_person(self, person_id: int) -> Dict:
        """Get person details"""
        self._rate_limit("subject")
        cache_key = f"person:{person_id}"
        cached = self.db.get_cache(cache_key)
        if cached:
            return cached

        result = self._request("GET", f"/persons/{person_id}")
        if "error" not in result:
            self.db.set_cache(cache_key, result, 86400)
        return result

    # Authenticated methods
    def get_me(self, username: str) -> Dict:
        """Get current user info"""
        token = self._get_valid_token(username)
        if not token:
            return {"error": "Not authenticated"}
        return self._request("GET", "/me", token=token)

    def get_collections(self, username: str, status: Optional[str] = None,
                        type_: Optional[str] = None) -> Dict:
        """Get user collections"""
        token = self._get_valid_token(username)
        if not token:
            return {"error": "Not authenticated"}

        self._rate_limit("collection")
        params = {}
        if status:
            params["type"] = STATUS_MAP.get(status, 1)
        if type_:
            params["subject_type"] = TYPE_MAP.get(type_, 2)

        # Use /me/collections for authenticated user
        return self._request("GET", "/me/collections", params, token=token)

    def update_collection(self, username: str, subject_id: int, status: str) -> Dict:
        """Update collection status"""
        token = self._get_valid_token(username)
        if not token:
            return {"error": "Not authenticated"}

        self._rate_limit("collection")
        data = {"type": STATUS_MAP.get(status, 1)}
        return self._request("POST", f"/v0/users/-/collections/{subject_id}", data, token=token)

    def get_progress(self, username: str, subject_id: int) -> Dict:
        """Get watch progress"""
        token = self._get_valid_token(username)
        if not token:
            return {"error": "Not authenticated"}

        return self._request("GET", f"/v0/users/-/collections/{subject_id}", token=token)

    def mark_episode(self, username: str, subject_id: int, episode_id: int, status: str) -> Dict:
        """Mark episode status"""
        token = self._get_valid_token(username)
        if not token:
            return {"error": "Not authenticated"}

        data = {"episode_id": episode_id, "type": 1 if status == "watched" else 2}
        return self._request("PUT", f"/v0/users/-/collections/{subject_id}/episodes", data, token=token)


# ============================================================
# MCP Protocol Handler
# ============================================================

class MCPRequestHandler(BaseHTTPRequestHandler):
    """Handle MCP protocol requests"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def send_json_response(self, status: int, data: Any):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        path = self.path.split("?")[0]

        # Health check
        if path == "/health":
            self.send_json_response(200, {"status": "ok"})
            return

        # List users
        if path == "/users":
            users = self.server.db.list_users()
            self.send_json_response(200, {"users": users})
            return

        # OAuth status
        if path == "/auth/status":
            username = self.headers.get("X-User")
            if username:
                user = self.server.db.get_user(username)
                if user:
                    self.send_json_response(200, {
                        "authenticated": True,
                        "username": username,
                        "expires_at": user["expires_at"]
                    })
                else:
                    self.send_json_response(200, {"authenticated": False})
            else:
                self.send_json_response(401, {"error": "No user specified"})
            return

        # Web OAuth authorization page
        if path.startswith("/auth/"):
            self._handle_auth_page(path)
            return

        self.send_json_response(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path.split("?")[0]

        # MCP tool call
        if path == "/mcp":
            self._handle_mcp()
            return

        # OAuth token exchange
        if path == "/oauth/callback":
            self._handle_oauth_callback()
            return

        # Register user
        if path == "/register":
            self._handle_register()
            return

        # Unregister user
        if path == "/unregister":
            self._handle_unregister()
            return

        self.send_json_response(404, {"error": "Not found"})

    def _handle_mcp(self):
        """Handle MCP tool calls"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            request = json.loads(body)
        except:
            self.send_json_response(400, {"error": "Invalid JSON"})
            return

        # Get username from header or use default
        username = self.headers.get("X-User", "default")
        tool_name = request.get("name", "")
        args = request.get("arguments", {})

        # Add username to args if needed
        if tool_name.startswith("bangumi_") and "username" not in args:
            args["username"] = username

        # Route to handler
        handler = getattr(self.server.mcp_tools, f"handle_{tool_name}", None)
        if handler:
            try:
                result = handler(args)
                self.send_json_response(200, {"result": result})
            except Exception as e:
                self.send_json_response(500, {"error": str(e)})
        else:
            self.send_json_response(400, {"error": f"Unknown tool: {tool_name}"})

    def _handle_oauth_callback(self):
        """Handle OAuth callback"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            params = urllib.parse.parse_qs(body)
        except:
            self.send_json_response(400, {"error": "Invalid request"})
            return

        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]

        if error:
            self.send_json_response(400, {"error": error})
            return

        if not code or not state:
            self.send_json_response(400, {"error": "Missing code or state"})
            return

        # Validate state
        state_data = self.server.db.get_oauth_state(state)
        if not state_data:
            self.send_json_response(400, {"error": "Invalid state"})
            return

        self.server.db.delete_oauth_state(state)

        # Exchange code for token
        config = {"client_id": state_data["client_id"], "redirect_uri": state_data["redirect_uri"]}
        data = {
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "code": code,
            "redirect_uri": config["redirect_uri"]
        }

        result = self._request("POST", "/oauth/access_token", data)
        if "error" in result:
            self.send_json_response(400, result)
            return

        # Get user info
        me_result = self._request("GET", "/me", token=result["access_token"])
        if "error" in me_result:
            self.send_json_response(400, me_result)
            return

        # Save user
        self.server.db.save_user(
            me_result["id"],
            me_result["username"],
            me_result["nickname"],
            result,
            config["client_id"],
            "N/A"  # client_secret not needed after auth
        )

        self.send_json_response(200, {
            "success": True,
            "username": me_result["username"],
            "nickname": me_result["nickname"]
        })

    def _handle_register(self):
        """Register a new user"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
        except:
            self.send_json_response(400, {"error": "Invalid JSON"})
            return

        username = data.get("username")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")

        if not all([username, client_id, client_secret]):
            self.send_json_response(400, {"error": "Missing required fields"})
            return

        # Store client credentials (they'll be used for OAuth)
        # For now, just save a placeholder
        self.server.db.save_user(0, username, username, {
            "access_token": "",
            "refresh_token": "",
            "expires_in": 0
        }, client_id, client_secret)

        # Generate OAuth URL for this user
        state = secrets.token_urlsafe(32)
        redirect_uri = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}/oauth/callback"
        self.server.db.save_oauth_state(state, client_id, redirect_uri)

        auth_url = f"{OAUTH_URL}/authorize?client_id={client_id}&response_type=code&redirect_uri={urllib.parse.quote(redirect_uri)}&state={state}"

        self.send_json_response(200, {
            "auth_url": auth_url,
            "username": username
        })

    def _handle_unregister(self):
        """Unregister a user"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
        except:
            self.send_json_response(400, {"error": "Invalid JSON"})
            return

        username = data.get("username")
        if not username:
            self.send_json_response(400, {"error": "Missing username"})
            return

        self.server.db.delete_user(username)
        self.send_json_response(200, {"success": True})

    def _handle_auth_page(self, path: str):
        """Serve OAuth authorization page"""
        # Extract state from query
        query = urllib.parse.parse_qs(self.path.split("?")[1] if "?" in self.path else "")
        state = query.get("state", [None])[0]

        if not state:
            self.send_json_response(400, {"error": "Missing state"})
            return

        # Validate state
        state_data = self.server.db.get_oauth_state(state)
        if not state_data:
            self.send_json_response(400, {"error": "Invalid state"})
            return

        # Show authorization page
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bangumi OAuth 授权</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .btn {{ display: inline-block; padding: 12px 24px; background: #2a82e4; color: white; text-decoration: none; border-radius: 6px; margin-right: 10px; }}
        .btn-secondary {{ background: #999; }}
    </style>
</head>
<body>
    <h1>Bangumi OAuth 授权</h1>
    <div class="info">
        <p>应用请求访问您的 Bangumi 账户。</p>
        <p>点击下方按钮继续授权流程。</p>
    </div>
    <a href="{OAUTH_URL}/authorize?client_id={state_data['client_id']}&response_type=code&redirect_uri={urllib.parse.quote(state_data['redirect_uri'])}&state={state}" class="btn">前往授权</a>
    <a href="javascript:window.close();" class="btn btn-secondary">取消</a>
</body>
</html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request"""
        url = f"{BASE_URL}{path}"
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=get_headers(), method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server"""
    daemon_threads = True


# ============================================================
# MCP Tools
# ============================================================

class BangumiMCPTools:
    """MCP tool implementations"""

    def __init__(self, db: BangumiDB):
        self.db = db
        self.client = BangumiClient(db)

    def handle_bangumi_search(self, args: Dict) -> Dict:
        """Search for subjects"""
        return self.client.search(
            args.get("keyword", ""),
            args.get("type", "anime"),
            args.get("limit", 10)
        )

    def handle_bangumi_info(self, args: Dict) -> Dict:
        """Get subject details"""
        subject_id = args.get("subject_id")
        if not subject_id:
            return {"error": "Missing subject_id"}
        return self.client.get_subject(int(subject_id))

    def handle_bangumi_episodes(self, args: Dict) -> Dict:
        """Get episodes list"""
        subject_id = args.get("subject_id")
        if not subject_id:
            return {"error": "Missing subject_id"}
        return self.client.get_episodes(int(subject_id), args.get("limit", 100))

    def handle_bangumi_season(self, args: Dict) -> Dict:
        """Get season calendar"""
        import datetime
        now = datetime.datetime.now()
        return self.client.get_season(
            args.get("year", now.year),
            args.get("month", now.month)
        )

    def handle_bangumi_rank(self, args: Dict) -> Dict:
        """Get ranking"""
        return self.client.get_rank(
            args.get("type", "anime"),
            args.get("top", 20)
        )

    def handle_bangumi_person(self, args: Dict) -> Dict:
        """Search or get person"""
        keyword = args.get("keyword")
        person_id = args.get("person_id")

        if person_id:
            return self.client.get_person(int(person_id))
        if keyword:
            return self.client.search_person(keyword)
        return {"error": "Missing keyword or person_id"}

    def handle_bangumi_my_collections(self, args: Dict) -> Dict:
        """Get user collections"""
        username = args.get("username")
        if not username:
            return {"error": "Missing username"}
        return self.client.get_collections(
            username,
            args.get("status"),
            args.get("type")
        )

    def handle_bangumi_update_collection(self, args: Dict) -> Dict:
        """Update collection status"""
        username = args.get("username")
        subject_id = args.get("subject_id")
        status = args.get("status")

        if not all([username, subject_id, status]):
            return {"error": "Missing required fields"}
        return self.client.update_collection(username, int(subject_id), status)

    def handle_bangumi_progress(self, args: Dict) -> Dict:
        """Get watch progress"""
        username = args.get("username")
        subject_id = args.get("subject_id")

        if not all([username, subject_id]):
            return {"error": "Missing required fields"}
        return self.client.get_progress(username, int(subject_id))

    def handle_bangumi_mark_episode(self, args: Dict) -> Dict:
        """Mark episode status"""
        username = args.get("username")
        subject_id = args.get("subject_id")
        episode_id = args.get("episode_id")
        status = args.get("status", "watched")

        if not all([username, subject_id, episode_id]):
            return {"error": "Missing required fields"}
        return self.client.mark_episode(username, int(subject_id), int(episode_id), status)


# ============================================================
# Main Entry Point
# ============================================================

def get_db_path() -> str:
    """Get database path based on platform"""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return str(base / "bangumi-mcp" / "data.db")


def main():
    parser = argparse.ArgumentParser(description="Bangumi MCP Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--db", help="Database path (default: auto)")
    args = parser.parse_args()

    db_path = args.db or get_db_path()

    print(f"Starting Bangumi MCP Server...")
    print(f"Database: {db_path}")
    print(f"Server: {args.host}:{args.port}")
    print(f"Platform: {platform.system()}")

    # Initialize database
    db = BangumiDB(db_path)

    # Initialize MCP tools
    mcp_tools = BangumiMCPTools(db)

    # Start server
    server = ThreadedHTTPServer((args.host, args.port), MCPRequestHandler)
    server.db = db
    server.mcp_tools = mcp_tools

    print(f"\nMCP Server running at http://{args.host}:{args.port}")
    print("Endpoints:")
    print(f"  - MCP: POST http://{args.host}:{args.port}/mcp")
    print(f"  - Health: GET http://{args.host}:{args.port}/health")
    print(f"  - Users: GET http://{args.host}:{args.port}/users")
    print(f"  - Register: POST http://{args.host}:{args.port}/register")
    print("\nPress Ctrl+C to stop")

    # Clean up expired cache periodically
    def cleanup_cache():
        while True:
            time.sleep(3600)  # Every hour
            db.clean_expired_cache()

    cleanup_thread = threading.Thread(target=cleanup_cache, daemon=True)
    cleanup_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()