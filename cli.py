"""
Command-line interface for Chirpy RSS reader.

Provides argument parsing and command-line options.
"""

import argparse
from pathlib import Path
from typing import Any

from config import ChirpyConfig


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="chirpy",
        description="Chirpy RSS Reader - Text-to-speech RSS article reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Read 3 latest unread articles with TTS
  %(prog)s --process-summaries      # Process articles with empty summaries
  %(prog)s --max-articles 5         # Read 5 articles instead of 3
  %(prog)s --no-speech              # Skip text-to-speech (silent mode)
  %(prog)s --log-level DEBUG        # Enable debug logging
  %(prog)s --config-file my.env     # Use custom environment file

For more information, see: https://github.com/nyasuto/chirpy
        """,
    )

    # Main operation modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--process-summaries",
        action="store_true",
        help="Process articles with empty summaries using AI",
    )
    mode_group.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and exit",
    )

    # Database options
    parser.add_argument(
        "database",
        nargs="?",
        default=None,
        help="Path to SQLite database file (default: from config)",
    )

    # Article processing options
    parser.add_argument(
        "--max-articles",
        type=int,
        metavar="N",
        help="Maximum number of articles to process (default: from config)",
    )

    # Text-to-speech options
    tts_group = parser.add_argument_group("text-to-speech options")
    tts_group.add_argument(
        "--no-speech",
        action="store_true",
        help="Disable text-to-speech output",
    )
    tts_group.add_argument(
        "--tts-rate",
        type=int,
        metavar="WPM",
        help="Speech rate in words per minute (50-500)",
    )
    tts_group.add_argument(
        "--tts-volume",
        type=float,
        metavar="LEVEL",
        help="Speech volume level (0.0-1.0)",
    )
    tts_group.add_argument(
        "--tts-engine",
        choices=["pyttsx3", "say"],
        help="Text-to-speech engine to use",
    )

    # Interactive mode options
    ui_group = parser.add_argument_group("user interface options")
    ui_group.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enable interactive mode with keyboard controls",
    )
    ui_group.add_argument(
        "--select-articles",
        action="store_true",
        help="Show article selection menu before reading",
    )

    # Content fetching options
    content_group = parser.add_argument_group("content fetching options")
    content_group.add_argument(
        "--fetch-timeout",
        type=int,
        metavar="SECONDS",
        help="HTTP request timeout in seconds",
    )
    content_group.add_argument(
        "--rate-limit",
        type=int,
        metavar="SECONDS",
        dest="rate_limit_delay",
        help="Delay between API calls in seconds",
    )

    # Logging options
    log_group = parser.add_argument_group("logging options")
    log_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level",
    )
    log_group.add_argument(
        "--log-file",
        metavar="PATH",
        help="Write logs to file (in addition to console)",
    )
    log_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (equivalent to --log-level DEBUG)",
    )
    log_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output (equivalent to --log-level ERROR)",
    )

    # Configuration options
    config_group = parser.add_argument_group("configuration options")
    config_group.add_argument(
        "--config-file",
        metavar="PATH",
        help="Load configuration from specific .env file",
    )
    config_group.add_argument(
        "--show-config",
        action="store_true",
        help="Show current configuration and exit",
    )

    # Translation options
    translation_group = parser.add_argument_group("translation options")
    translation_group.add_argument(
        "--no-translate",
        action="store_true",
        help="Disable automatic translation of non-Japanese articles",
    )
    translation_group.add_argument(
        "--target-language",
        metavar="LANG",
        help="Target language for translation (default: ja for Japanese)",
    )
    translation_group.add_argument(
        "--translate-articles",
        action="store_true",
        help="Process existing articles for translation",
    )

    # Application behavior
    behavior_group = parser.add_argument_group("application behavior")
    behavior_group.add_argument(
        "--no-mark-read",
        action="store_true",
        help="Don't mark articles as read after processing",
    )
    behavior_group.add_argument(
        "--no-pause",
        action="store_true",
        help="Don't pause between articles",
    )

    # Version
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_parser()
    return parser.parse_args(args)


def apply_args_to_config(
    args: argparse.Namespace, config: ChirpyConfig
) -> ChirpyConfig:
    """Apply command-line arguments to configuration."""
    # Handle configuration file
    if args.config_file:
        from dotenv import load_dotenv

        config_path = Path(args.config_file)
        if config_path.exists():
            load_dotenv(config_path)
            # Reload config from environment
            config = ChirpyConfig.from_env()
        else:
            print(f"Warning: Configuration file not found: {config_path}")

    # Apply command-line overrides
    updates: dict[str, Any] = {}

    if args.database:
        updates["database_path"] = args.database

    if args.max_articles:
        updates["max_articles"] = args.max_articles

    # TTS settings
    if args.no_speech:
        updates["speech_enabled"] = False

    if args.tts_rate:
        updates["tts_rate"] = args.tts_rate

    if args.tts_volume:
        updates["tts_volume"] = args.tts_volume

    if args.tts_engine:
        updates["tts_engine"] = args.tts_engine

    # Content fetching
    if args.fetch_timeout:
        updates["fetch_timeout"] = args.fetch_timeout

    if args.rate_limit_delay:
        updates["rate_limit_delay"] = args.rate_limit_delay

    # Logging
    if args.verbose:
        updates["log_level"] = "DEBUG"
    elif args.quiet:
        updates["log_level"] = "ERROR"
    elif args.log_level:
        updates["log_level"] = args.log_level

    if args.log_file:
        updates["log_file"] = args.log_file

    # Translation settings
    if args.no_translate:
        updates["auto_translate"] = False

    if args.target_language:
        updates["target_language"] = args.target_language

    # Application behavior
    if args.no_mark_read:
        updates["auto_mark_read"] = False

    if args.no_pause:
        updates["pause_between_articles"] = False

    # Interactive mode
    if args.interactive:
        updates["interactive_mode"] = True

    # Store select_articles flag for later use
    if hasattr(args, "select_articles"):
        updates["select_articles"] = args.select_articles

    # Apply updates
    if updates:
        config.update_from_dict(updates)

    return config


def show_config(config: ChirpyConfig) -> None:
    """Display current configuration."""
    print("🐦 Chirpy Configuration")
    print("=" * 50)

    sections = {
        "Database": ["database_path"],
        "Article Processing": ["max_articles", "max_summary_length"],
        "OpenAI API": [
            "openai_api_key",
            "openai_model",
            "openai_max_tokens",
            "openai_temperature",
        ],
        "Text-to-Speech": ["tts_engine", "tts_rate", "tts_volume"],
        "Content Fetching": ["fetch_timeout", "rate_limit_delay"],
        "Logging": ["log_level", "log_format", "log_file"],
        "Translation": [
            "auto_translate",
            "target_language",
            "preserve_original",
            "translation_provider",
        ],
        "Application Behavior": [
            "auto_mark_read",
            "pause_between_articles",
            "speech_enabled",
        ],
    }

    config_dict = config.to_dict()

    for section, keys in sections.items():
        print(f"\n📋 {section}:")
        for key in keys:
            value = config_dict.get(key)
            if key == "openai_api_key" and value:
                # Mask API key for security
                value = f"{value[:8]}..." if len(value) > 8 else "***"
            print(f"  {key}: {value}")

    print()


def handle_special_modes(args: argparse.Namespace, config: ChirpyConfig) -> bool:
    """
    Handle special operation modes that don't require main application flow.

    Returns True if a special mode was handled and the application should exit.
    """
    if args.show_config:
        show_config(config)
        return True

    if args.stats:
        from database_service import DatabaseManager

        db = DatabaseManager(config.database_path)
        stats = db.get_database_stats()

        print("🐦 Chirpy Database Statistics")
        print("=" * 40)
        print(f"📊 Total articles: {stats['total_articles']}")
        print(f"📖 Read articles: {stats['read_articles']}")
        print(f"📰 Unread articles: {stats['unread_articles']}")
        print(f"📄 Empty summaries: {stats['empty_summaries']}")

        # Calculate percentages
        total = stats["total_articles"]
        if total > 0:
            read_pct = (stats["read_articles"] / total) * 100
            unread_pct = (stats["unread_articles"] / total) * 100
            empty_pct = (stats["empty_summaries"] / total) * 100

            print("\n📈 Percentages:")
            print(f"  Read: {read_pct:.1f}%")
            print(f"  Unread: {unread_pct:.1f}%")
            print(f"  Empty summaries: {empty_pct:.1f}%")

        return True

    if args.translate_articles:
        from content_fetcher import ContentFetcher
        from database_service import DatabaseManager

        print("🔄 Processing articles for translation...")

        db = DatabaseManager(config.database_path)
        content_fetcher = ContentFetcher(config)

        if not content_fetcher.is_available():
            print("❌ OpenAI API not available for translation")
            return True

        # Get untranslated articles
        untranslated = db.get_untranslated_articles(limit=config.max_articles)

        if not untranslated:
            print("✅ No articles requiring translation found")
            return True

        print(f"📋 Found {len(untranslated)} articles to process")

        processed = 0
        for article in untranslated:
            try:
                result = content_fetcher.process_article_with_translation(article)
                summary, detected_lang, is_translated = result

                if summary and is_translated:
                    # Update database with translation
                    original_summary = article.get("summary", "")
                    db.update_article_summary(article["id"], summary)
                    db.update_article_language_info(
                        article["id"], detected_lang, original_summary, True
                    )
                    print(f"✅ Translated article {article['id']}")
                    processed += 1
                elif summary:
                    # Update language info only
                    db.update_article_language_info(
                        article["id"], detected_lang, None, False
                    )
                    print(
                        f"ℹ️  Processed article {article['id']} (no translation needed)"
                    )
                else:
                    print(f"❌ Failed to process article {article['id']}")

            except Exception as e:
                print(f"❌ Error processing article {article['id']}: {e}")

        print(f"\n🎉 Translation complete! {processed} articles translated")
        return True

    return False
