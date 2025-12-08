#!/usr/bin/env python3
"""
Startup script for LUKi Cognitive Modules - Railway deployment.
Reads PORT from environment variable for Railway compatibility.
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start the cognitive modules FastAPI server."""
    # Railway requires using their PORT variable - no defaults
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting LUKi Cognitive Modules on port {port}")
    
    try:
        import uvicorn
        
        uvicorn.run(
            "luki_modules_cognitive.main:app",
            host="0.0.0.0",
            port=port,
            log_level="info",
            workers=1,
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
