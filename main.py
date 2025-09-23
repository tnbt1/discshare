import asyncio
import uvicorn
from threading import Thread
import signal
import sys
from config import Config, setup_logging
from bot.discord_bot import run_bot
from api.server import app

logger = setup_logging()

def run_fastapi():
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=Config.API_PORT,
        log_level="info"
    )

def signal_handler(sig, frame):
    logger.info("Shutting down...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== File Sharing Service Starting ===")
    logger.info(f"API URL: http://0.0.0.0:{Config.API_PORT}")
    logger.info(f"Service URL: {Config.SERVICE_URL}")
    
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    
    logger.info("Starting Discord Bot...")
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
