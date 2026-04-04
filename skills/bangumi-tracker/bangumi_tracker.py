#!/usr/bin/env python3
"""
Bangumi Tracker - Local user edition with OAuth authentication
Manage collections and track watch progress
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any

# Constants
BASE_URL = "https://api.bgm.tv/v0"
OAUTH_URL = "https://bgm.tv/oauth"
DEFAULT_REDIRECT_URI = "http://localhost:17321/callback"
DEFAULT_PORT = 17321
CONFIG_DIR = Path.home() / ".bangumi"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
HEADERS = {"User-Agent": "bangumi-tracker/1.0 (private)"}


def ensure_config_dir():
    """Ensure config directory exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Optional[Dict[str, Any]]:
    """Load OAuth config from file"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_config(config: Dict[str, Any]):
    """Save OAuth config to file"""
    ensure_config_dir()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Config saved to {CONFIG_FILE}")


def load_token() -> Optional[Dict[str, Any]]:
    """Load access token from file"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_token(token: Dict[str, Any]):
    """Save access token to file"""
    ensure_config_dir()
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(token, f, indent=2)
    print(f"✅ Token saved to {TOKEN_FILE}")


def remove_token():
    """Remove saved token"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("✅ Token removed")
    else:
        print("ℹ️ No token to remove")


def api_get(path: str, params: Optional[Dict] = None, token: Optional[str] = None) -> Dict:
    """Make authenticated GET request"""
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, headers=HEADERS)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}


def api_post(path: str, data: Dict, token: Optional[str] = None) -> Dict:
    """Make authenticated POST request"""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=body, headers=HEADERS, method='POST')
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}


def get_valid_token() -> Optional[str]:
    """Get valid access token, refresh if expired"""
    token_data = load_token()
    if not token_data:
        return None
    
    # Check if token is expired (with 5 min buffer)
    if token_data.get("expires_at", 0) - time.time() < 300:
        print("🔄 Token expired, refreshing...")
        return refresh_access_token(token_data.get("refresh_token"))
    
    return token_data.get("access_token")


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """Refresh access token using refresh token"""
    config = load_config()
    if not config:
        print("❌ No config found. Run 'config' first.")
        return None
    
    data = {
        "grant_type": "refresh_token",
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": refresh_token
    }
    
    url = f"{OAUTH_URL}/access_token"
    body = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=HEADERS, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            new_token = json.loads(response.read().decode('utf-8'))
            new_token["expires_at"] = time.time() + new_token.get("expires_in", 3600)
            save_token(new_token)
            return new_token["access_token"]
    except urllib.error.HTTPError as e:
        print(f"❌ Failed to refresh token: {e.reason}")
        return None


# Command implementations
def cmd_config(args):
    """Save OAuth configuration"""
    config = {
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "redirect_uri": args.redirect_uri or DEFAULT_REDIRECT_URI
    }
    save_config(config)
    print("\nNext step: Run 'python bangumi_tracker.py auth' to authorize")


def cmd_auth(args):
    """Run OAuth authorization flow"""
    config = load_config()
    if not config:
        print("❌ No config found. Run 'config' first:")
        print("   python bangumi_tracker.py config --client-id <id> --client-secret <secret>")
        return 1
    
    # Build authorization URL
    auth_params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "redirect_uri": config.get("redirect_uri", DEFAULT_REDIRECT_URI)
    }
    auth_url = f"{OAUTH_URL}/authorize?{urllib.parse.urlencode(auth_params)}"
    
    print("=" * 60)
    print("Bangumi OAuth Authorization")
    print("=" * 60)
    print(f"\n1. Opening browser to: {auth_url}")
    print("2. Login to Bangumi and authorize the app")
    print("3. You will be redirected to localhost")
    print("\n⚠️  Note: This requires a local HTTP server to receive the callback.")
    print("   The server will run on port 17321.")
    print("=" * 60)
    
    # Open browser
    import webbrowser
    webbrowser.open(auth_url)
    
    # Start temporary server to receive callback
    print("\n🚀 Starting callback server...")
    return start_callback_server(config)


def start_callback_server(config: Dict) -> int:
    """Start temporary HTTP server to receive OAuth callback"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    
    authorization_code = None
    server_running = True
    
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal authorization_code, server_running
            
            if "/callback" in self.path:
                # Parse query parameters
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                
                if "code" in params:
                    authorization_code = params["code"][0]
                    self.send_response(200)
                    self.end_headers()
                    html = '''<html>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>Authorization Successful!</h1>
    <p>You can close this window and return to the terminal.</p>
</body>
</html>'''
                    self.wfile.write(html.encode('utf-8'))
                    server_running = False
                elif "error" in params:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(f"Error: {params['error'][0]}".encode())
                    server_running = False
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing authorization code")
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress log output
    
    port = DEFAULT_PORT
    server = HTTPServer(("localhost", port), CallbackHandler)
    
    # Run server in thread
    def run_server():
        while server_running:
            server.handle_request()
    
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    
    print(f"🌐 Waiting for callback on http://localhost:{port}/callback ...")
    print("   (Press Ctrl+C to cancel)\n")
    
    # Wait for authorization code
    try:
        while server_running and authorization_code is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return 1
    
    server.server_close()
    
    if not authorization_code:
        print("❌ Failed to get authorization code")
        return 1
    
    print(f"✅ Got authorization code")
    
    # Exchange code for token
    print("🔄 Exchanging code for token...")
    token_data = {
        "grant_type": "authorization_code",
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": authorization_code,
        "redirect_uri": config.get("redirect_uri", DEFAULT_REDIRECT_URI)
    }
    
    url = f"{OAUTH_URL}/access_token"
    body = urllib.parse.urlencode(token_data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=HEADERS, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            token = json.loads(response.read().decode('utf-8'))
            token["expires_at"] = time.time() + token.get("expires_in", 3600)
            save_token(token)
            print("\n🎉 Authorization successful!")
            print(f"   User ID: {token.get('user_id', 'N/A')}")
            return 0
    except urllib.error.HTTPError as e:
        print(f"❌ Failed to get token: {e.reason}")
        return 1


def cmd_status(args):
    """Check login status"""
    config = load_config()
    token = load_token()
    
    print("=" * 60)
    print("Bangumi Tracker Status")
    print("=" * 60)
    
    if config:
        print(f"✅ Config: {CONFIG_FILE}")
        print(f"   Client ID: {config.get('client_id', 'N/A')[:20]}...")
    else:
        print(f"❌ Config: Not found ({CONFIG_FILE})")
    
    if token:
        print(f"✅ Token: {TOKEN_FILE}")
        print(f"   Expires: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(token.get('expires_at', 0)))}")
        
        # Try to get user info
        access_token = get_valid_token()
        if access_token:
            user = api_get("/me", token=access_token)
            if "error" not in user:
                print(f"   Logged in as: {user.get('nickname', user.get('username', 'Unknown'))}")
            else:
                print(f"   ⚠️  Token may be invalid: {user['error']}")
        else:
            print("   ⚠️  Token expired and refresh failed")
    else:
        print(f"❌ Token: Not found ({TOKEN_FILE})")
    
    print("=" * 60)
    return 0


def cmd_logout(args):
    """Logout and remove token"""
    remove_token()
    return 0


def cmd_collections(args):
    """List user's collections"""
    token = get_valid_token()
    if not token:
        print("❌ Not logged in. Run 'auth' first.")
        return 1
    
    # Get user info first
    user = api_get("/me", token=token)
    if "error" in user:
        print(f"❌ Failed to get user info: {user['error']}")
        return 1
    
    username = user.get("username")
    print(f"📚 Collections for {user.get('nickname', username)}\n")
    
    # Build params
    params = {}
    if args.type:
        type_map = {"anime": 2, "book": 1, "game": 4, "music": 3, "real": 6}
        params["subject_type"] = type_map.get(args.type, 2)
    if args.status:
        params["type"] = args.status
    
    # Get collections
    collections = api_get(f"/v0/users/{username}/collections", params=params, token=token)
    
    if "error" in collections:
        print(f"❌ Failed to get collections: {collections['error']}")
        return 1
    
    data = collections.get("data", [])
    if not data:
        print("ℹ️ No collections found")
        return 0
    
    # Format output
    status_emoji = {
        "wish": "🔖",
        "collect": "✅",
        "doing": "▶️",
        "on_hold": "⏸️",
        "dropped": "❌"
    }
    
    for item in data:
        subject = item.get("subject", {})
        status = item.get("type", "unknown")
        emoji = status_emoji.get(status, "❓")
        
        print(f"{emoji} [{status.upper()}] {subject.get('name_cn', subject.get('name', 'Unknown'))}")
        print(f"   ID: {subject.get('id')} | Score: {subject.get('score', 'N/A')}")
        if item.get("ep_status"):
            print(f"   Progress: {item['ep_status']}/{subject.get('eps', '?')} eps")
        print()
    
    print(f"Total: {len(data)} items")
    return 0


def cmd_collect(args):
    """Add or update collection"""
    token = get_valid_token()
    if not token:
        print("❌ Not logged in. Run 'auth' first.")
        return 1
    
    subject_id = args.subject_id
    status = args.status
    
    # Validate status
    valid_statuses = ["wish", "doing", "collect", "on_hold", "dropped"]
    if status not in valid_statuses:
        print(f"❌ Invalid status. Use: {', '.join(valid_statuses)}")
        return 1
    
    print(f"📝 Setting collection status to '{status}' for subject {subject_id}...")
    
    # Bangumi API uses POST for new collections and PUT for updates
    # We'll try POST first, then PUT if it fails
    data = {"type": status}
    result = api_post(f"/v0/users/-/collections/{subject_id}", data, token=token)
    
    if "error" in result:
        # Try PUT for update
        url = f"{BASE_URL}/v0/users/-/collections/{subject_id}"
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={**HEADERS, "Authorization": f"Bearer {token}"}, method='PUT')
        req.add_header("Content-Type", "application/json")
        
        try:
            with urllib.request.urlopen(req) as response:
                print("✅ Collection updated successfully")
                return 0
        except urllib.error.HTTPError as e:
            print(f"❌ Failed to update collection: {e.reason}")
            return 1
    else:
        print("✅ Collection added successfully")
        return 0


def cmd_uncollect(args):
    """Remove from collection"""
    token = get_valid_token()
    if not token:
        print("❌ Not logged in. Run 'auth' first.")
        return 1
    
    subject_id = args.subject_id
    print(f"🗑️  Removing subject {subject_id} from collections...")
    
    url = f"{BASE_URL}/v0/users/-/collections/{subject_id}"
    req = urllib.request.Request(url, headers={**HEADERS, "Authorization": f"Bearer {token}"}, method='DELETE')
    
    try:
        with urllib.request.urlopen(req) as response:
            print("✅ Removed from collection")
            return 0
    except urllib.error.HTTPError as e:
        print(f"❌ Failed to remove: {e.reason}")
        return 1


def cmd_progress(args):
    """Get watch progress"""
    token = get_valid_token()
    if not token:
        print("❌ Not logged in. Run 'auth' first.")
        return 1
    
    subject_id = args.subject_id
    
    # Get collection info with progress
    result = api_get(f"/v0/users/-/collections/{subject_id}", token=token)
    
    if "error" in result:
        print(f"❌ Failed to get progress: {result['error']}")
        return 1
    
    subject = result.get("subject", {})
    print(f"📺 {subject.get('name_cn', subject.get('name', 'Unknown'))}")
    print(f"   Status: {result.get('type', 'unknown')}")
    print(f"   Progress: {result.get('ep_status', 0)}/{subject.get('eps', '?')} episodes")
    
    if result.get("vol_status"):
        print(f"   Volumes: {result['vol_status']}/{subject.get('volumes', '?')}")
    
    return 0


def cmd_me(args):
    """Get current user info"""
    token = get_valid_token()
    if not token:
        print("❌ Not logged in. Run 'auth' first.")
        return 1
    
    user = api_get("/me", token=token)
    
    if "error" in user:
        print(f"❌ Failed to get user info: {user['error']}")
        return 1
    
    print("=" * 60)
    print("User Profile")
    print("=" * 60)
    print(f"Username: {user.get('username')}")
    print(f"Nickname: {user.get('nickname')}")
    print(f"ID: {user.get('id')}")
    
    if user.get('user_group'):
        group_names = {1: "管理员", 2: "Bangumi 管理猿", 3: "天窗联盟管理猿", 
                       4: "禁言用户", 5: "禁止访问用户", 6: "人物管理猿", 7: "维基条目管理猿",
                       8: "用户", 9: "维基人", 10: "目录管理猿", 11: "天窗用户"}
        print(f"Group: {group_names.get(user['user_group'], user['user_group'])}")
    
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Bangumi Tracker - OAuth edition")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configure OAuth credentials")
    config_parser.add_argument("--client-id", required=True, help="OAuth client ID")
    config_parser.add_argument("--client-secret", required=True, help="OAuth client secret")
    config_parser.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI, help="Redirect URI")
    config_parser.set_defaults(func=cmd_config)
    
    # Auth command
    auth_parser = subparsers.add_parser("auth", help="Authorize with Bangumi")
    auth_parser.set_defaults(func=cmd_auth)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check login status")
    status_parser.set_defaults(func=cmd_status)
    
    # Logout command
    logout_parser = subparsers.add_parser("logout", help="Logout and remove token")
    logout_parser.set_defaults(func=cmd_logout)
    
    # Collections command
    collections_parser = subparsers.add_parser("collections", help="List my collections")
    collections_parser.add_argument("--type", choices=["anime", "book", "game", "music", "real"], help="Subject type")
    collections_parser.add_argument("--status", choices=["wish", "doing", "collect", "on_hold", "dropped"], help="Collection status")
    collections_parser.set_defaults(func=cmd_collections)
    
    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Add/update collection")
    collect_parser.add_argument("subject_id", type=int, help="Subject ID")
    collect_parser.add_argument("status", choices=["wish", "doing", "collect", "on_hold", "dropped"], help="Status")
    collect_parser.set_defaults(func=cmd_collect)
    
    # Uncollect command
    uncollect_parser = subparsers.add_parser("uncollect", help="Remove from collection")
    uncollect_parser.add_argument("subject_id", type=int, help="Subject ID")
    uncollect_parser.set_defaults(func=cmd_uncollect)
    
    # Progress command
    progress_parser = subparsers.add_parser("progress", help="Get watch progress")
    progress_parser.add_argument("subject_id", type=int, help="Subject ID")
    progress_parser.set_defaults(func=cmd_progress)
    
    # Me command
    me_parser = subparsers.add_parser("me", help="Get user info")
    me_parser.set_defaults(func=cmd_me)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
