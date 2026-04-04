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

Create `config.json` in the skill directory:

```bash
python bangumi_tracker.py config --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

Or manually create `~/.bangumi/config.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "http://localhost:17321/callback"
}
```

### Step 3: Authenticate

Run the OAuth flow:

```bash
python bangumi_tracker.py auth
```

This will:
1. Open your browser to Bangumi authorization page
2. You login and authorize the app
3. Callback to localhost saves the token
4. Token stored in `~/.bangumi/token.json`

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

# Mark episode as watched
python bangumi_tracker.py watch <subject_id> <episode_id>

# Mark multiple episodes
python bangumi_tracker.py watch-batch <subject_id> <episode_ids...>
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

All data stored in `~/.bangumi/`:

- `config.json` - OAuth app credentials (you create this)
- `token.json` - Access/refresh tokens (auto-generated after auth)
- `cache/` - API response cache

## Notes

- Requires Python 3.9+
- OAuth token auto-refreshes when expired
- All API requests respect Bangumi rate limits
- Token stored locally, never uploaded
