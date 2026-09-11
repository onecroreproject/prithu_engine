#!/usr/bin/env python3
# ============================================================================
# PRITHU BACKEND - MAIN ENTRY POINT
# ============================================================================
# Start the recommendation engine API server
# ============================================================================

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from app.core.config import Config
from app.core.logger_setup import get_logger


logger = get_logger(__name__)


def main():
    """
    Start the FastAPI application.

    Environment variables:
        - ENVIRONMENT: development, staging, production
        - DEBUG: True/False
        - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR
        - UVICORN_HOST: Server host (default 0.0.0.0)
        - UVICORN_PORT: Server port (default 8000)
    """
    
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"   Environment: {Config.ENVIRONMENT}")
    logger.info(f"   Debug Mode: {Config.DEBUG}")
    logger.info("=" * 80)

    # Configuration
    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", "8000"))

    try:
        uvicorn.run(
            "app.api.routes:app",
            host=host,
            port=port,
            reload=Config.DEBUG,
            log_level=Config.LOG_LEVEL.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
