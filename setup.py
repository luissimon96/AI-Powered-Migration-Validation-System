#!/usr/bin/env python3
"""
Setup configuration for AI-Powered Migration Validation System.

Supports optional dependencies via extras_require.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "AI-Powered Migration Validation System"

# Core dependencies (always installed)
CORE_DEPS = [
    "fastapi>=0.104.0,<0.105.0",
    "uvicorn[standard]>=0.24.0,<0.25.0",
    "pydantic>=2.5.0,<3.0.0",
    "pydantic-settings>=2.1.0,<3.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
    "httpx>=0.25.0,<0.26.0",
    "aiohttp>=3.9.0,<4.0.0",
    "python-multipart>=0.0.6,<1.0.0",
    "Pillow>=10.1.0,<11.0.0",
    "structlog>=23.2.0,<24.0.0",
    "asyncio-throttle>=1.0.0,<2.0.0",
]

# Optional dependency groups
EXTRAS = {
    # AI & LLM Integration
    "ai": [
        "openai>=1.3.0,<2.0.0",
        "anthropic>=0.7.0,<1.0.0",
        "google-generativeai>=0.3.0,<1.0.0",
    ],

    # Multi-Agent AI Framework
    "crewai": [
        "crewai>=0.1.26,<1.0.0",
    ],

    # Browser Automation
    "browser": [
        "playwright>=1.40.0,<2.0.0",
        "browser-use>=0.1.4,<1.0.0",
    ],

    # Database & Persistence
    "database": [
        "sqlalchemy>=2.0.23,<3.0.0",
        "alembic>=1.13.0,<2.0.0",
        "asyncpg>=0.29.0,<1.0.0",
    ],

    # Caching & Performance
    "cache": [
        "redis>=5.0.0,<6.0.0",
    ],

    # Security & Authentication
    "security": [
        "passlib[bcrypt]>=1.7.4,<2.0.0",
        "python-jose[cryptography]>=3.3.0,<4.0.0",
    ],

    # Development & Testing
    "dev": [
        "pytest>=7.4.0,<8.0.0",
        "pytest-asyncio>=0.21.0,<1.0.0",
        "pytest-cov>=4.1.0,<5.0.0",
        "pytest-mock>=3.12.0,<4.0.0",
        "pytest-xdist>=3.5.0,<4.0.0",
    ],

    # Code Quality & Formatting
    "quality": [
        "black>=23.11.0,<24.0.0",
        "flake8>=6.1.0,<7.0.0",
        "isort>=5.12.0,<6.0.0",
        "mypy>=1.7.0,<2.0.0",
    ],

    # Security Scanning
    "security-scan": [
        "bandit>=1.7.5,<2.0.0",
        "safety>=2.3.0,<3.0.0",
    ],

    # Performance Testing
    "performance": [
        "locust>=2.17.0,<3.0.0",
        "memory-profiler>=0.61.0,<1.0.0",
    ],

    # Development Tools
    "tools": [
        "pre-commit>=3.6.0,<4.0.0",
        "jupyter>=1.0.0,<2.0.0",
        "ipython>=8.17.0,<9.0.0",
        "debugpy>=1.8.0,<2.0.0",
        "watchdog>=3.0.0,<4.0.0",
    ],

    # Documentation
    "docs": [
        "mkdocs>=1.5.0,<2.0.0",
        "mkdocs-material>=9.4.0,<10.0.0",
    ],

    # Type Stubs
    "types": [
        "types-requests>=2.31.0,<3.0.0",
        "types-redis>=4.6.0,<5.0.0",
    ],
}

# Convenience groups
EXTRAS["all"] = sum(EXTRAS.values(), [])
EXTRAS["full-dev"] = EXTRAS["dev"] + EXTRAS["quality"] + EXTRAS["tools"] + EXTRAS["types"]
EXTRAS["production"] = EXTRAS["ai"] + EXTRAS["database"] + EXTRAS["cache"] + EXTRAS["security"]

setup(
    name="ai-migration-validator",
    version="1.0.0",
    author="AI Migration Validation Team",
    author_email="contact@ai-migration-validator.com",
    description="AI-Powered system for validating software migration fidelity using LLMs and multi-agent frameworks",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/ai-migration-validator/ai-migration-validator",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
        "Framework :: Pytest",
    ],
    python_requires=">=3.8",
    install_requires=CORE_DEPS,
    extras_require=EXTRAS,
    entry_points={
        "console_scripts": [
            "migration-validator=src.main:main",
            "mv-cli=src.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["templates/*", "static/*"],
    },
    project_urls={
        "Bug Reports": "https://github.com/ai-migration-validator/ai-migration-validator/issues",
        "Source": "https://github.com/ai-migration-validator/ai-migration-validator",
        "Documentation": "https://ai-migration-validator.readthedocs.io/",
    },
)