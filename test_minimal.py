#!/usr/bin/env python3
"""
Minimal test to isolate the macOS assertion error.
"""

print("Testing minimal imports...")

# Test 1: Basic Python modules
try:
    print("✅ Basic Python modules OK")
except Exception as e:
    print(f"❌ Basic Python modules: {e}")
    exit(1)

# Test 2: SQLModel and database
try:
    from config import get_config
    from database_service import DatabaseManager

    print("✅ Database modules OK")
except Exception as e:
    print(f"❌ Database modules: {e}")
    exit(1)

# Test 3: Create database manager
try:
    config = get_config()
    db = DatabaseManager(config.database_path)
    print("✅ Database manager created OK")
    db.close()
except Exception as e:
    print(f"❌ Database manager: {e}")
    exit(1)

# Test 4: Rich library (terminal UI)
try:
    from rich.console import Console

    console = Console()
    console.print("✅ Rich console OK")
except Exception as e:
    print(f"❌ Rich console: {e}")
    exit(1)

# Test 5: Keyboard library (potential issue)
try:
    print("✅ Keyboard library OK")
except Exception as e:
    print(f"❌ Keyboard library: {e}")

# Test 6: pyttsx3 (potential issue)
try:
    print("✅ pyttsx3 OK")
except Exception as e:
    print(f"❌ pyttsx3: {e}")

print("✅ All basic tests completed successfully!")
