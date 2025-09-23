#!/usr/bin/env python3
"""Quick setup script for AI-Powered Migration Validation System.
This handles dependency installation and basic configuration.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command."""
    print(f"🔧 Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def install_minimal_deps():
    """Install minimal dependencies."""
    print("📦 Installing minimal dependencies...")

    deps = [
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.20.0",
        "pydantic>=2.0.0",
        "structlog>=23.0.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.24.0",
        "python-multipart>=0.0.6",
        "click>=8.0.0",
    ]

    for dep in deps:
        if not run_command(f"pip install '{dep}'", check=False):
            print(f"⚠️  Failed to install {dep}, continuing...")

    print("✅ Basic dependencies installed!")


def install_pydantic_settings():
    """Install pydantic-settings separately."""
    print("📦 Installing pydantic-settings...")
    if not run_command("pip install 'pydantic-settings>=2.0.0'", check=False):
        print("⚠️  pydantic-settings failed, will use fallback")


def setup_env():
    """Setup environment file."""
    env_example = Path(".env.example")
    env_file = Path(".env")

    if env_example.exists() and not env_file.exists():
        print("📄 Creating .env file from template...")
        env_content = env_example.read_text()
        env_file.write_text(env_content)
        print("✅ .env file created! Please edit it with your API keys.")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  No .env.example found")


def test_basic_import():
    """Test if basic imports work."""
    print("🧪 Testing basic imports...")

    try:
        # Test core imports
        import fastapi
        import pydantic
        import uvicorn

        print("✅ Core web framework imports work")

        try:
            import structlog

            print("✅ Logging imports work")
        except ImportError:
            print("⚠️  structlog not available, will use fallbacks")

        try:
            from pydantic_settings import BaseSettings

            print("✅ pydantic-settings available")
        except ImportError:
            print("⚠️  pydantic-settings not available, using pydantic BaseSettings")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def create_simple_test():
    """Create a simple test file."""
    test_content = '''#!/usr/bin/env python3
"""Simple test to verify the system works."""

def test_basic_import():
    """Test basic imports."""
    try:
        from src.core.config import get_settings
        settings = get_settings()
        print(f"✅ Configuration loaded: {settings.environment}")
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_api_creation():
    """Test API creation."""
    try:
        from src.api.routes import app
        print("✅ API app created successfully")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running basic tests...")

    if test_basic_import():
        print("1/2 ✅ Config test passed")
    else:
        print("1/2 ❌ Config test failed")
        exit(1)

    if test_api_creation():
        print("2/2 ✅ API test passed")
        print("\\n🎉 Basic system is working!")
    else:
        print("2/2 ❌ API test failed")
        exit(1)
'''

    Path("test_basic.py").write_text(test_content)
    print("✅ Created test_basic.py")


def main():
    """Main setup function."""
    print("🚀 AI-Powered Migration Validation System - Quick Setup")
    print("=" * 60)

    # Check if we're in a virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print("✅ Virtual environment detected")
    else:
        print("⚠️  No virtual environment detected. Consider using one.")

    # Install dependencies
    install_minimal_deps()
    install_pydantic_settings()

    # Setup environment
    setup_env()

    # Test imports
    if test_basic_import():
        print("✅ All basic imports successful!")
    else:
        print("❌ Some imports failed, but continuing...")

    # Create test file
    create_simple_test()

    print("\n" + "=" * 60)
    print("🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python test_basic.py")
    print("3. Run: python run.py")
    print("4. Visit: http://localhost:8000/docs")
    print('\n🔧 For full setup: pip install -e ".[dev,ai,browser]"')


if __name__ == "__main__":
    main()
