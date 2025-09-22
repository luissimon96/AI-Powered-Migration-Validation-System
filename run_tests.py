#!/usr/bin/env python3
"""
Comprehensive test runner for AI-Powered Migration Validation System.

This script provides organized test execution with proper categorization and reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"\n✅ {description} - PASSED")
    else:
        print(f"\n❌ {description} - FAILED")

    return result.returncode


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Migration Validation System Test Runner"
    )
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument(
        "--behavioral", action="store_true", help="Run behavioral validation tests only"
    )
    parser.add_argument("--system", action="store_true", help="Run system tests only")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument(
        "--parallel", "-j", type=int, default=1, help="Number of parallel processes"
    )
    parser.add_argument("--markers", type=str, help="Run tests with specific markers")
    parser.add_argument("--pattern", type=str, help="Run tests matching pattern")
    parser.add_argument(
        "--html-report", action="store_true", help="Generate HTML test report"
    )

    args = parser.parse_args()

    # Set up environment
    os.environ["PYTHONPATH"] = str(Path(__file__).parent)
    os.environ["TESTING"] = "true"

    # Base pytest command
    pytest_cmd = ["python", "-m", "pytest"]

    # Add parallel processing if specified
    if args.parallel > 1:
        pytest_cmd.extend(["-n", str(args.parallel)])

    # Add verbosity
    if args.verbose:
        pytest_cmd.append("-v")
    else:
        pytest_cmd.append("-q")

    # Add coverage if requested
    if args.coverage:
        pytest_cmd.extend(
            [
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
            ]
        )

    # Add HTML report if requested
    if args.html_report:
        pytest_cmd.extend(["--html=test_report.html", "--self-contained-html"])

    # Determine test selection
    test_patterns = []
    markers = []

    if args.unit:
        markers.append("unit")
        test_patterns.append("tests/unit/")

    if args.integration:
        markers.append("integration")
        test_patterns.append("tests/integration/")

    if args.behavioral:
        markers.append("behavioral")
        test_patterns.append("tests/behavioral/")

    if args.system:
        markers.append("system")
        test_patterns.append("tests/system/")

    if args.performance:
        markers.append("performance")

    if args.fast:
        markers.append("not slow")

    if args.markers:
        markers.append(args.markers)

    # Add marker selection
    if markers:
        pytest_cmd.extend(["-m", " and ".join(markers)])

    # Add test patterns
    if test_patterns:
        pytest_cmd.extend(test_patterns)
    elif args.pattern:
        pytest_cmd.extend(["-k", args.pattern])
    else:
        pytest_cmd.append("tests/")

    exit_codes = []

    # If no specific test category is selected, run organized test suite
    if not any(
        [
            args.unit,
            args.integration,
            args.behavioral,
            args.system,
            args.performance,
            args.markers,
            args.pattern,
        ]
    ):
        print("🧪 AI-Powered Migration Validation System - Comprehensive Test Suite")
        print("=" * 80)

        # 1. Unit Tests
        unit_cmd = pytest_cmd.copy()
        if "-m" in unit_cmd:
            marker_idx = unit_cmd.index("-m") + 1
            unit_cmd[marker_idx] = "unit"
        else:
            unit_cmd.extend(["-m", "unit"])
        unit_cmd.append("tests/unit/")

        exit_codes.append(run_command(unit_cmd, "Unit Tests - Core Component Testing"))

        # 2. Integration Tests
        integration_cmd = pytest_cmd.copy()
        if "-m" in integration_cmd:
            marker_idx = integration_cmd.index("-m") + 1
            integration_cmd[marker_idx] = "integration"
        else:
            integration_cmd.extend(["-m", "integration"])
        integration_cmd.append("tests/integration/")

        exit_codes.append(
            run_command(
                integration_cmd, "Integration Tests - Component Interaction Testing"
            )
        )

        # 3. Behavioral Tests
        behavioral_cmd = pytest_cmd.copy()
        if "-m" in behavioral_cmd:
            marker_idx = behavioral_cmd.index("-m") + 1
            behavioral_cmd[marker_idx] = "behavioral"
        else:
            behavioral_cmd.extend(["-m", "behavioral"])
        behavioral_cmd.append("tests/")

        exit_codes.append(
            run_command(
                behavioral_cmd,
                "Behavioral Tests - CrewAI and Browser Automation Testing",
            )
        )

        # 4. System Tests (if not fast mode)
        if not args.fast:
            system_cmd = pytest_cmd.copy()
            if "-m" in system_cmd:
                marker_idx = system_cmd.index("-m") + 1
                system_cmd[marker_idx] = "system and not external"
            else:
                system_cmd.extend(["-m", "system and not external"])
            system_cmd.append("tests/system/")

            exit_codes.append(
                run_command(system_cmd, "System Tests - End-to-End Pipeline Testing")
            )

        # Generate final summary
        print("\n" + "=" * 80)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 80)

        test_categories = ["Unit Tests", "Integration Tests", "Behavioral Tests"]
        if not args.fast:
            test_categories.append("System Tests")

        for i, category in enumerate(test_categories):
            if i < len(exit_codes):
                status = "✅ PASSED" if exit_codes[i] == 0 else "❌ FAILED"
                print(f"{category:.<50} {status}")

        # Overall result
        overall_success = all(code == 0 for code in exit_codes)
        print("-" * 80)
        print(
            f"Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}"
        )

        if args.coverage:
            print("\n📈 Coverage report generated:")
            print("  - Terminal: displayed above")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")

        if args.html_report:
            print("\n📋 HTML test report generated: test_report.html")

        return 0 if overall_success else 1

    else:
        # Run specific test category
        exit_code = run_command(
            pytest_cmd,
            f"Running tests with markers: {' and '.join(markers) if markers else 'all'}",
        )

        if args.coverage:
            print("\n📈 Coverage report generated:")
            print("  - HTML: htmlcov/index.html")

        if args.html_report:
            print("\n📋 HTML test report generated: test_report.html")

        return exit_code


def validate_test_setup():
    """Validate test environment setup."""
    print("🔍 Validating test environment setup...")

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(
            f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}"
        )
        return False

    print(
        f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}"
    )

    # Check required packages
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "fastapi",
        "pydantic",
        "structlog",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")

    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print('Run: pip install -e ".[dev,quality]"')
        return False

    # Check optional packages
    optional_packages = {
        "playwright": "Browser automation (behavioral tests)",
        "browser_use": "AI browser automation (behavioral tests)",
        "crewai": "Multi-agent validation (behavioral tests)",
    }

    print("\n🔧 Optional packages (for full functionality):")
    for package, description in optional_packages.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"⚠️  {package} - {description} (not available)")

    print("\n✅ Test environment validation complete")
    return True


if __name__ == "__main__":
    print("🧪 AI-Powered Migration Validation System - Test Runner")
    print("=" * 80)

    # Validate environment
    if not validate_test_setup():
        print(
            "\n❌ Environment validation failed. Please install missing dependencies."
        )
        sys.exit(1)

    # Run tests
    exit_code = main()
    sys.exit(exit_code)
