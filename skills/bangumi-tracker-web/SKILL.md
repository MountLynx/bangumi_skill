---
name: bangumi
description: Search and manage Bangumi (bgm.tv) collections. Use for searching anime/manga/games, getting details about specific titles, checking current season anime, viewing rankings, looking up voice actors or staff, and managing personal Bangumi collections. Also use when user wants to track watch progress or update collection status on Bangumi.
---

# Bangumi

Query the Bangumi database and manage personal collections.

## When to Use

Use this skill when the user wants to:
- Search for anime, manga, games, music, or real (三次元)
- Get details about a specific title by ID
- View what anime is airing this season
- Check top-rated titles
- Find information about voice actors, directors, or other staff
- View or update their Bangumi collection status
- Track watch progress for anime

## Commands

### Search

Search for titles in the Bangumi database.

```
bangumi search <keyword> [--type anime|book|game|music|real] [--limit 10]
```

Examples:
- `bangumi search 葬送的芙莉莲`
- `bangumi search 迷宫饭 --type anime`
- `bangumi search --limit 20`

### Get Details

Get detailed information about a title. Use the subject ID from search results.

```
bangumi info <subject_id>
```

Examples:
- `bangumi info 428477`
- `bangumi info 300107` (for books)

### Episodes

List all episodes for a title.

```
bangumi episodes <subject_id> [--limit 100]
```

Examples:
- `bangumi episodes 428477`
- `bangumi episodes 428477 --limit 50`

### Season Calendar

View anime airing in a specific month.

```
bangumi season [--year 2026] [--month 4]
```

Examples:
- `bangumi season`
- `bangumi season --month 10`

### Rankings

View top-rated titles.

```
bangumi rank [--type anime|book|game|music|real] [--top 20]
```

Examples:
- `bangumi rank`
- `bangumi rank --top 10`
- `bangumi rank --type game`

### Person Search

Search for voice actors, directors, or other staff.

```
bangumi person <keyword>
```

Examples:
- `bangumi person 斋藤圭一郎`
- `bangumi person 花泽香菜`

### Collection (Requires Auth)

View your Bangumi collection.

```
bangumi collections [--status wish|doing|collect|on_hold|dropped] [--type anime|book|game|music|real]
```

Examples:
- `bangumi collections`
- `bangumi collections --status doing`
- `bangumi collections --type anime --status wish`

### Update Collection (Requires Auth)

Update the collection status for a title.

```
bangumi collect <subject_id> <status>
```

Status options: `wish`, `doing`, `collect`, `on_hold`, `dropped`

Examples:
- `bangumi collect 428477 doing`
- `bangumi collect 428477 collect`

### Progress (Requires Auth)

View your watch progress for a title.

```
bangumi progress <subject_id>
```

Examples:
- `bangumi progress 428477`

### User Info (Requires Auth)

Get your Bangumi profile information.

```
bangumi me
```

## Authentication

Some commands require Bangumi OAuth authentication.

### First-time Setup (Local Version)

1. Get OAuth credentials from https://bgm.tv/dev/app/create
2. Run: `python bangumi_tracker.py config --client-id <id> --client-secret <secret>`
3. Run: `python bangumi_tracker.py auth`
4. Open the displayed URL in your browser and complete authorization

### Multiple Users (MCP Server)

If your administrator has set up an MCP server, authentication is handled by the server. Users register via the server's web interface.

## Output Format

Results are formatted as readable text:

```
【Title】 ⭐ Rating | Rank #Rank
Type: TV · Episodes · Air Date
Tags: tag1, tag2, ...
Collection: Watching X | Completed X | Wish X
Summary: ...
```

## Notes

- Subject IDs can be found in the Bangumi URL: `bgm.tv/subject/428477`
- Unauthenticated users can: search, info, episodes, season, rank, person
- Authenticated users can additionally: collections, collect, progress, me
- Some commands may be slow due to Bangumi API rate limits