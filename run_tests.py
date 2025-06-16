#!/usr/bin/env python3
"""
Test runner script for Chirpy RSS Reader.

This script runs the complete test suite with coverage reporting.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run the complete test suite."""
    print("🧪 Running Chirpy RSS Reader Test Suite\n")
    
    # Ensure we're in the project directory
    project_root = Path(__file__).parent
    
    try:
        # Run pytest with coverage
        cmd = [
            "uv", "run", "pytest",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=80",
            "-v",
            "--tb=short",
            "tests/"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("📊 Coverage report generated in htmlcov/")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running tests: {e}")
        return 1
    except FileNotFoundError:
        print("❌ pytest not found. Make sure you've run 'uv sync --group test'")
        return 1


def run_unit_tests_only():
    """Run only unit tests."""
    print("🧪 Running Unit Tests Only\n")
    
    project_root = Path(__file__).parent
    
    try:
        cmd = [
            "uv", "run", "pytest",
            "--cov=.",
            "--cov-report=term-missing",
            "-v",
            "-m", "unit",
            "tests/unit/"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running unit tests: {e}")
        return 1


def run_integration_tests_only():
    """Run only integration tests."""
    print("🧪 Running Integration Tests Only\n")
    
    project_root = Path(__file__).parent
    
    try:
        cmd = [
            "uv", "run", "pytest",
            "--cov=.",
            "--cov-report=term-missing",
            "-v",
            "-m", "integration",
            "tests/integration/"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running integration tests: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            exit_code = run_unit_tests_only()
        elif sys.argv[1] == "integration":
            exit_code = run_integration_tests_only()
        else:
            print("Usage: python run_tests.py [unit|integration]")
            exit_code = 1
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)