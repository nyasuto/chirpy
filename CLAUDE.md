# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chirpy is an MVP RSS reader with text-to-speech functionality. It reads articles from a local SQLite database and provides audio narration of article titles and summaries.

## Architecture

- **Database**: SQLite3 database (`data/articles.db`) with articles table containing RSS feed data
- **Data Source**: Database is synchronized from a remote machine using `collect.sh` script
- **Main Application**: Will be implemented as `chirpy.py` (not yet created)
- **Tech Stack**: Python 3.x with modern tooling (uv, ruff, ty mentioned in README)

## Database Schema

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    link TEXT UNIQUE,
    published TEXT,
    summary TEXT,
    embedded INTEGER DEFAULT 0
);
```

Key points:
- `summary` contains full article text when available
- Empty `summary` requires fetching original content from `link`
- `published` field used for date filtering
- Need to implement read/unread tracking system

## Common Commands

### Database Operations
- Check article count: `sqlite3 data/articles.db "SELECT COUNT(*) FROM articles"`
- View schema: `sqlite3 data/articles.db ".schema articles"`
- Sync database: `./collect.sh`

### Development Setup
- Virtual environment: `python3 -m venv venv && source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Run application: `python chirpy.py`

## Key Requirements

- Text-to-speech using `pyttsx3` or macOS `say` command
- Process 3 most recent unread articles per session
- Implement read tracking (separate table needed)
- Handle empty summaries by fetching from article links
- Use OpenAI API for content summarization when needed

## Implementation Notes

- Main script should be `chirpy.py` in project root
- Articles database contains 1894+ entries
- Focus on MVP functionality: read from DB → text-to-speech output
- No MP3 saving in MVP version