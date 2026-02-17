"""
Main entry point for TARS
Starts Flask server, scheduler, and Slack Socket Mode together
"""
import os
import sys
import logging
from threading import Thread
from dotenv import load_dotenv
from app import app
from scheduler import TARSScheduler
from config import Config

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info("Starting TARS - Ticket Analysis & Reporting System")
        logger.info("=" * 60)
        
        # Validate configuration
        logger.info("Validating configuration...")
        try:
            Config.validate()
            logger.info("✅ Configuration validated")
        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            sys.exit(1)
        
        # Initialize scheduler
        logger.info("Initializing scheduler...")
        scheduler = TARSScheduler()
        
        # Get cron schedule from environment
        cron_schedule = os.getenv('SCHEDULE_CRON', '0 9 * * *')
        scheduler.start(cron_schedule)
        
        # Start Slack Socket Mode (if tokens are available)
        slack_app_token = os.getenv('SLACK_APP_TOKEN')
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        
        if slack_app_token and slack_bot_token:
            logger.info("Starting Slack Socket Mode...")
            from slack_socket_app import start_socket_mode
            
            # Run Socket Mode in separate thread
            socket_thread = Thread(target=start_socket_mode, daemon=True)
            socket_thread.start()
            logger.info("✅ Slack Socket Mode started")
        else:
            logger.warning("⚠️  Slack Socket Mode disabled (tokens not configured)")
        
        # Start Flask server (blocking)
        port = int(os.getenv('PORT', 5000))
        host = os.getenv('HOST', '0.0.0.0')
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        logger.info("=" * 60)
        logger.info("✅ TARS is now running")
        logger.info(f"   - Web server: http://{host}:{port}")
        logger.info(f"   - Scheduled runs: {cron_schedule}")
        if slack_app_token and slack_bot_token:
            logger.info(f"   - Slack Socket Mode: enabled")
        logger.info("=" * 60)
        
        # Run Flask (this blocks until interrupted)
        app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down TARS...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
