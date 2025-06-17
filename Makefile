# Chirpy RSS Reader - Development Makefile
# Provides convenient commands for development tasks and code quality checks

.PHONY: help install test lint format type-check quality check run run-interactive clean build dev-setup

# Default target
help: ## Show this help message
	@echo "Chirpy RSS Reader - Development Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Environment Variables:"
	@echo "  OPENAI_API_KEY     OpenAI API key for content fetching"
	@echo "  INTERACTIVE_MODE   Enable interactive mode (true/false)"
	@echo "  LOG_LEVEL         Set logging level (DEBUG/INFO/WARNING/ERROR)"

# Development setup
dev-setup: ## Set up development environment
	@echo "🔧 Setting up development environment..."
	uv sync
	@echo "✅ Development environment ready!"

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	uv sync
	@echo "✅ Dependencies installed!"

# Code quality checks
lint: ## Run linting with ruff
	@echo "🔍 Running linting checks..."
	uv run ruff check .
	@echo "✅ Linting completed!"

lint-fix: ## Run linting with auto-fix
	@echo "🔧 Running linting with auto-fix..."
	uv run ruff check . --fix
	@echo "✅ Linting with fixes completed!"

format: ## Format code with ruff
	@echo "🎨 Formatting code..."
	uv run ruff format .
	@echo "✅ Code formatting completed!"

format-check: ## Check code formatting without making changes
	@echo "🎨 Checking code formatting..."
	uv run ruff format --check .
	@echo "✅ Format check completed!"

type-check: ## Run type checking with mypy
	@echo "🔍 Running type checks..."
	uv run mypy .
	@echo "✅ Type checking completed!"

# Comprehensive quality checks
quality: ## Run all code quality checks (lint, format, type-check)
	@echo "🚀 Running comprehensive code quality checks..."
	@echo ""
	@echo "1️⃣ Linting..."
	uv run ruff check .
	@echo ""
	@echo "2️⃣ Format checking..."
	uv run ruff format --check .
	@echo ""
	@echo "3️⃣ Type checking..."
	uv run mypy .
	@echo ""
	@echo "✅ All quality checks passed!"

check: quality ## Alias for quality checks

quality-fix: ## Run quality checks with auto-fixes where possible
	@echo "🔧 Running quality checks with auto-fixes..."
	@echo ""
	@echo "1️⃣ Linting with fixes..."
	uv run ruff check . --fix
	@echo ""
	@echo "2️⃣ Formatting..."
	uv run ruff format .
	@echo ""
	@echo "3️⃣ Type checking..."
	uv run mypy .
	@echo ""
	@echo "✅ Quality checks with fixes completed!"

# Application execution
run: ## Run Chirpy with default settings
	@echo "🐦 Starting Chirpy RSS Reader..."
	uv run python chirpy.py

run-interactive: ## Run Chirpy in interactive mode
	@echo "🎮 Starting Chirpy in interactive mode..."
	uv run python chirpy.py --interactive

run-debug: ## Run Chirpy with debug logging
	@echo "🐛 Starting Chirpy with debug logging..."
	LOG_LEVEL=DEBUG uv run python chirpy.py

run-help: ## Show Chirpy help
	@echo "📖 Chirpy help:"
	uv run python chirpy.py --help

run-stats: ## Show database statistics
	@echo "📊 Database statistics:"
	uv run python chirpy.py --stats

run-process: ## Process articles with empty summaries
	@echo "🔄 Processing articles with empty summaries..."
	uv run python chirpy.py --process-summaries

# Database operations
db-stats: ## Show database statistics
	@echo "📊 Database statistics:"
	sqlite3 data/articles.db "SELECT COUNT(*) as total_articles FROM articles;"
	sqlite3 data/articles.db "SELECT COUNT(*) as read_articles FROM read_articles;"
	sqlite3 data/articles.db "SELECT COUNT(*) as unread_articles FROM articles a LEFT JOIN read_articles r ON a.id = r.article_id WHERE r.article_id IS NULL;"

db-schema: ## Show database schema
	@echo "🗄️  Database schema:"
	sqlite3 data/articles.db ".schema"

db-sync: ## Sync database from remote
	@echo "🔄 Syncing database..."
	./collect.sh

# Testing (placeholder for future implementation)
test: ## Run tests (placeholder)
	@echo "🧪 Running tests..."
	@echo "ℹ️  Tests not yet implemented"
	@echo "   Future: pytest integration planned"

test-watch: ## Run tests in watch mode (placeholder)
	@echo "👀 Running tests in watch mode..."
	@echo "ℹ️  Test watch mode not yet implemented"

# Build and packaging
build: ## Build the package
	@echo "📦 Building package..."
	uv build
	@echo "✅ Package built successfully!"

# Cleanup
clean: ## Clean up build artifacts and caches
	@echo "🧹 Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup completed!"

clean-logs: ## Clean up log files
	@echo "🧹 Cleaning up log files..."
	find . -name "*.log" -delete
	@echo "✅ Log cleanup completed!"

# Git and development workflow
git-hooks: ## Set up git pre-commit hooks with main branch protection
	@echo "🎣 Setting up git hooks..."
	@echo "#!/bin/sh" > .git/hooks/pre-commit
	@echo "# Pre-commit hook for Chirpy project" >> .git/hooks/pre-commit
	@echo "" >> .git/hooks/pre-commit
	@echo "set -e" >> .git/hooks/pre-commit
	@echo "" >> .git/hooks/pre-commit
	@echo "# Get current branch name" >> .git/hooks/pre-commit
	@echo 'current_branch=$$(git rev-parse --abbrev-ref HEAD)' >> .git/hooks/pre-commit
	@echo "" >> .git/hooks/pre-commit
	@echo "# Check if trying to commit directly to main branch" >> .git/hooks/pre-commit
	@echo 'if [ "$$current_branch" = "main" ]; then' >> .git/hooks/pre-commit
	@echo '    echo "🚫 ERROR: Direct commits to main branch are not allowed!"' >> .git/hooks/pre-commit
	@echo '    echo ""' >> .git/hooks/pre-commit
	@echo '    echo "📋 Please follow the proper workflow:"' >> .git/hooks/pre-commit
	@echo '    echo "  1. Create a feature branch:"' >> .git/hooks/pre-commit
	@echo '    echo "     git checkout -b {type}/issue-X-description"' >> .git/hooks/pre-commit
	@echo '    echo ""' >> .git/hooks/pre-commit
	@echo '    echo "  2. Make your changes and commit to the feature branch"' >> .git/hooks/pre-commit
	@echo '    echo ""' >> .git/hooks/pre-commit
	@echo '    echo "  3. Push and create a Pull Request:"' >> .git/hooks/pre-commit
	@echo '    echo "     git push -u origin {type}/issue-X-description"' >> .git/hooks/pre-commit
	@echo '    echo "     gh pr create"' >> .git/hooks/pre-commit
	@echo '    echo ""' >> .git/hooks/pre-commit
	@echo '    echo "💡 Example branch names:"' >> .git/hooks/pre-commit
	@echo '    echo "  - feat/issue-49-session-management"' >> .git/hooks/pre-commit
	@echo '    echo "  - fix/issue-50-config-inconsistency"' >> .git/hooks/pre-commit
	@echo '    echo "  - test/issue-54-main-app-coverage"' >> .git/hooks/pre-commit
	@echo '    echo ""' >> .git/hooks/pre-commit
	@echo '    echo "📖 See CLAUDE.md for complete workflow guidelines"' >> .git/hooks/pre-commit
	@echo '    echo ""' >> .git/hooks/pre-commit
	@echo '    exit 1' >> .git/hooks/pre-commit
	@echo 'fi' >> .git/hooks/pre-commit
	@echo "" >> .git/hooks/pre-commit
	@echo "# Run quality checks" >> .git/hooks/pre-commit
	@echo 'echo "🔍 Running quality checks..."' >> .git/hooks/pre-commit
	@echo "make quality" >> .git/hooks/pre-commit
	@echo "" >> .git/hooks/pre-commit
	@echo 'echo "✅ Pre-commit checks passed!"' >> .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "✅ Git hooks with main branch protection installed!"

# Development shortcuts
dev: dev-setup quality run ## Quick development setup and run

pr-ready: ## Ensure code is ready for PR submission
	@echo "🚀 Preparing for PR submission..."
	@echo ""
	make clean
	make quality-fix
	make quality
	@echo ""
	@echo "✅ Code is ready for PR submission!"
	@echo "📝 Don't forget to:"
	@echo "   - Update CHANGELOG.md if needed"
	@echo "   - Ensure commit messages follow conventional format"
	@echo "   - Run final tests before pushing"

# Configuration and environment
config-show: ## Show current configuration
	@echo "⚙️  Current configuration:"
	uv run python chirpy.py --show-config

config-test: ## Test configuration
	@echo "🧪 Testing configuration..."
	uv run python -c "from config import ChirpyConfig; config = ChirpyConfig.from_env(); print('✅ Configuration is valid')"

# Performance and monitoring
profile: ## Run with profiling (basic timing)
	@echo "📊 Running with basic profiling..."
	time uv run python chirpy.py --max-articles 1

# Documentation
docs: ## Generate/update documentation (placeholder)
	@echo "📚 Generating documentation..."
	@echo "ℹ️  Documentation generation not yet implemented"
	@echo "   Future: Sphinx or MkDocs integration planned"

# Security
security-check: ## Check for security issues (placeholder)
	@echo "🔒 Running security checks..."
	@echo "ℹ️  Security scanning not yet implemented"
	@echo "   Future: bandit or safety integration planned"

# Environment info
env-info: ## Show environment information
	@echo "🌍 Environment Information:"
	@echo "Python version: $$(python --version)"
	@echo "UV version: $$(uv --version)"
	@echo "Current directory: $$(pwd)"
	@echo "Virtual environment: $$(echo $$VIRTUAL_ENV)"
	@echo "Dependencies:"
	@uv tree --depth 1

# All-in-one commands
all: clean install quality build ## Run complete build pipeline

ci: quality test ## Run CI pipeline checks

# Debug and troubleshooting
debug-deps: ## Debug dependency issues
	@echo "🔍 Debugging dependencies..."
	uv tree
	uv pip list

debug-config: ## Debug configuration issues
	@echo "🔍 Debugging configuration..."
	@uv run python -c "from config import ChirpyConfig, initialize_app_logging; config, logger = initialize_app_logging(); print('Config loaded successfully'); print(f'Database path: {config.database_path}'); print(f'Max articles: {config.max_articles}'); print(f'TTS enabled: {config.speech_enabled}')"