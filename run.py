#!/usr/bin/env python3
"""Quick run script for AI-Powered Migration Validation System.

This provides a simple way to start the system without using the CLI.
"""

import uvicorn
from src.core.config import get_settings


def main():
    """Run the API server with default settings."""
    settings = get_settings()

    print("🚀 AI-Powered Migration Validation System")
    print(f"📡 Starting server at http://{settings.api_host}:{settings.api_port}")
    print(f"📖 API Documentation: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"🔧 Environment: {settings.environment}")

    uvicorn.run(
        "src.api.routes:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
