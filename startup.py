#!/usr/bin/env python3
"""
Startup script for LUKi Cognitive Modules - Railway deployment.
Reads PORT from environment variable for Railway compatibility.
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start the cognitive modules FastAPI server."""
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting LUKi Cognitive Modules on port {port}")
    logger.info(f"Environment: RAILWAY_ENVIRONMENT={os.getenv('RAILWAY_ENVIRONMENT')}")
    logger.info(f"Railway Service: RAILWAY_SERVICE={os.getenv('RAILWAY_SERVICE')}")
    
    # Test that we can import everything
    try:
        from luki_modules_cognitive.main import app
        logger.info("Successfully imported cognitive main app")
    except Exception as e:
        logger.error(f"Failed to import main app: {e}")
        sys.exit(1)

    try:
        import uvicorn
        logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            workers=1,
            access_log=True,  # Enable access logs
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
