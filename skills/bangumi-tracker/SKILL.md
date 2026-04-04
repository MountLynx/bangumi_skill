---
name: bangumi-tracker
description: Bangumi local user edition with OAuth authentication. Manage collections and track watch progress. Requires Bangumi account.
---

# Bangumi Tracker

Bangumi local user edition with OAuth authentication. Manage your collections and track watch progress.

## When to Use

Use this skill when the user wants to:
- Manage their Bangumi collections (wish/doing/collect/on_hold/dropped)
- Track watch progress for anime/episodes
- View personal collection lists
- Access user-specific Bangumi data

## First Time Setup

### Step 1: Create Bangumi OAuth App

1. Visit https://bgm.tv/dev/app/create
2. Fill in the form:
   - **App Name**: `bangumi-tracker` (or any name you prefer)
   - **Homepage URL**: `http://localhost:17321` (or your preferred URL)
   - **Callback URL**: `http://localhost:17321/callback` (must match the script)
3. Submit and get your **Client ID** and **Client Secret**

### Step 2: Configure the Skill

```bash
python bangumi_tracker.py config --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

Or manually create `~/.bangumi/config.json`:

```json
{
  "client_id": "your-client-id",
  "redirect_uri": "http://localhost:17321/callback"
}
```

> **Note**: On Windows, your `client_secret` is securely stored in Windows Credential Manager instead of the config file.

### Step 3: Authenticate

Run the OAuth flow:

```bash
python bangumi_tracker.py auth
```

This will:
1. Open your browser to Bangumi authorization page
2. **If not logged in**: You'll be redirected to the login page first, then authorize after logging in
3. You authorize the app
4. Callback to localhost saves the token

> **Important**: The OAuth flow requires browser interaction. Make sure you can access the callback URL `http://localhost:17321/callback` on your machine.

## Commands

### Authentication

```bash
# Configure OAuth credentials
python bangumi_tracker.py config --client-id <id> --client-secret <secret>

# Run OAuth authorization flow
python bangumi_tracker.py auth

# Check current login status
python bangumi_tracker.py status

# Logout (remove saved token)
python bangumi_tracker.py logout
```

### Collections

```bash
# List my collections
python bangumi_tracker.py collections [--type anime|book|game|music|real] [--status wish|doing|collect|on_hold|dropped]

# Add/update collection status
python bangumi_tracker.py collect <subject_id> <status>
# status: wish, doing, collect, on_hold, dropped

# Remove from collection
python bangumi_tracker.py uncollect <subject_id>
```

### Progress Tracking

```bash
# Get watch progress for a subject
python bangumi_tracker.py progress <subject_id>
```

### User Info

```bash
# Get current user info
python bangumi_tracker.py me
```

## Parameters

| Flag | Values | Default |
|------|--------|---------|
| `--type` | anime, book, game, music, real | anime |
| `--status` | wish, doing, collect, on_hold, dropped | all |

## Data Storage

### Windows
On Windows, sensitive data is stored securely using Windows Credential Manager:
- **Client ID**: `~/.bangumi/config.json`
- **Client Secret**: Windows Credential Manager (`BangumiTracker:client_secret`)
- **Access Token**: Windows Credential Manager (`BangumiTracker:access_token`)
- **Refresh Token**: Windows Credential Manager (`BangumiTracker:refresh_token`)
- **Expires At**: `~/.bangumi/token.json` (non-sensitive timestamp only)

### Other Platforms
On macOS/Linux, data is stored in files:
- `~/.bangumi/config.json` - OAuth app credentials
- `~/.bangumi/token.json` - Access/refresh tokens

## Security Notes

- **Windows**: Uses Windows Credential Manager for secure storage
- **Other Platforms**: Tokens stored in plain JSON files (use with caution)
- Token auto-refreshes when expired
- All API requests respect Bangumi rate limits
- Nothing is uploaded to external servers

## Troubleshooting

### "Callback server failed" or "No authorization code received"

- Make sure `http://localhost:17321/callback` is accessible
- Check that your OAuth app's Callback URL matches exactly
- Try running the command again

### "Token expired" errors

- Run `python bangumi_tracker.py auth` to re-authorize
- Your refresh token should automatically handle expiration

### Check credential storage (Windows)

To view stored credentials:
1. Open Windows Credential Manager (Control Panel → Credential Manager)
2. Look for entries starting with `BangumiTracker:`

## Requirements

- Python 3.9+
- Internet access to Bangumi API
- Browser for OAuth flow