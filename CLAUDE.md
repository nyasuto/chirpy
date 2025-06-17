# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🛠️ Development Tools

**Use the Makefile for all development tasks!** This project includes a comprehensive Makefile that standardizes development workflows.

- **Quick start:** `make help` to see all available commands
- **Code quality:** `make quality` (replaces individual ruff/mypy commands)
- **Development:** `make dev` for quick setup and run
- **PR preparation:** `make pr-ready` to ensure code is ready for submission

## 🔨 最重要ルール - 新しいルールの追加プロセス

ユーザーから今回限りではなく常に対応が必要だと思われる指示を受けた場合：

1. 「これを標準のルールにしますか？」と質問する
2. YESの回答を得た場合、CLAUDE.mdに追加ルールとして記載する
3. 以降は標準ルールとして常に適用する

このプロセスにより、プロジェクトのルールを継続的に改善していきます。

## GitHub Issue管理ルール

### 必須ラベル設定
Issueを作成・更新する際は、以下のラベルを必ず設定する：

#### Priority Labels（優先度）
- `priority: critical` - 緊急対応が必要（アプリケーション停止、セキュリティ問題など）
- `priority: high` - 高優先度（主要機能、重要なバグ修正など）
- `priority: medium` - 中優先度（機能改善、マイナーバグなど）
- `priority: low` - 低優先度（将来的な機能、ドキュメント改善など）

#### Type Labels（種類）
- `type: feature` - 新機能の追加
- `type: bug` - バグ修正
- `type: enhancement` - 既存機能の改善
- `type: docs` - ドキュメント関連
- `type: test` - テスト関連
- `type: refactor` - リファクタリング
- `type: ci/cd` - CI/CD関連
- `type: security` - セキュリティ関連

### ラベル適用例
```
title: "Add retry mechanism for API calls"
labels: ["priority: high", "type: enhancement"]

title: "Fix crash when database is missing"  
labels: ["priority: critical", "type: bug"]

title: "Add web interface"
labels: ["priority: low", "type: feature"]
```

## Project Overview

Chirpy is an MVP RSS reader with text-to-speech functionality. It reads articles from a local SQLite database and provides audio narration of article titles and summaries.

## Architecture

- **Database**: SQLite3 database (`data/articles.db`) with articles table containing RSS feed data
- **Data Source**: Database is synchronized from a remote machine using `collect.sh` script
- **Main Application**: Will be implemented as `chirpy.py` (not yet created)
- **Tech Stack**: Python 3.9+ with modern tooling (uv for dependency management, ruff for linting, mypy for type checking)

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

### Code Quality (Using Makefile)
- **Run all quality checks:** `make quality` (lint + format + type-check)
- **Auto-fix issues:** `make quality-fix`
- **Individual checks:**
  - Lint code: `make lint`
  - Format code: `make format`
  - Type check: `make type-check`

### Application Commands
- **Run Chirpy:** `make run`
- **Interactive mode:** `make run-interactive`
- **Debug mode:** `make run-debug`
- **Show help:** `make run-help`
- **Process summaries:** `make run-process`
- **Show stats:** `make run-stats`

### Database Operations
- **Article statistics:** `make db-stats`
- **Database schema:** `make db-schema`
- **Sync database:** `make db-sync`

### Development Setup
- **Full setup:** `make dev-setup`
- **Install dependencies:** `make install`
- **Build package:** `make build`
- **Clean artifacts:** `make clean`
- **Show environment:** `make env-info`

### Development Workflow
- **Quick dev cycle:** `make dev` (setup + quality + run)
- **PR preparation:** `make pr-ready`
- **Setup git hooks:** `make git-hooks`
- **All commands:** `make help`

### Legacy Commands (if Makefile unavailable)
- Install dependencies: `uv sync`
- Run application: `uv run python chirpy.py`
- Add new dependency: `uv add <package>`
- Activate shell: `uv shell`

## Key Requirements

- Text-to-speech using `pyttsx3` or macOS `say` command
- Process 3 most recent unread articles per session
- Implement read tracking (separate table needed)
- Handle empty summaries by fetching from article links
- Use OpenAI API for content summarization when needed

## Development Workflow

### Git and Commit Rules
- **NEVER commit directly to main branch**
- Always create feature branches for changes: `git checkout -b feature-name`
- Use descriptive branch names: `issue-X-feature-description`
- Create Pull Requests for all changes, no matter how small
- All commits must follow conventional commit format
- Include issue references: `Closes #X` in PR descriptions

### Branch Naming Convention
- Feature: `feat/issue-X-feature-name` (e.g., `feat/issue-4-main-script`)
- Bug fix: `fix/X-description` (e.g., `fix/audio-playback`)
- Hotfix: `hotfix/X-description`
other things follow to same convention like test/, doc/, cicd/ etc.

### Commit Message Format
```
<type>: <description>

<optional body>

<optional footer with issue references>
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Required Workflow
1. Create branch from main
2. Make changes
3. **Run Code Quality checks before commit:**
   - `make quality` (runs all: lint + format + type-check)
   - OR `make quality-fix` (auto-fix + check)
   - OR individual commands: `make lint`, `make format`, `make type-check`
4. Commit only after all checks pass
5. Push branch to remote
6. Create Pull Request
7. Wait for CI checks to pass
8. Merge via GitHub (not locally)

### Pre-commit Setup (Recommended)
- Run `make git-hooks` to automatically run quality checks before each commit
- This prevents committing code that doesn't pass quality standards

## Implementation Notes

- Main script should be `chirpy.py` in project root
- Articles database contains 1894+ entries
- Focus on MVP functionality: read from DB → text-to-speech output
- No MP3 saving in MVP version