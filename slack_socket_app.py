"""
Slack Socket Mode app for TARS slash commands
Handles /tars commands via WebSocket connection (no public IP needed)
"""
import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from pipeline.analyzer import TARSPipeline
from utils.slack_commands import SlackCommandHandler
from storage.mongodb_client import MongoDBStorage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Slack Bolt app with Socket Mode
app = App(token=os.getenv('SLACK_BOT_TOKEN'))

# Initialize TARS pipeline (lazy loading)
_pipeline = None
_command_handler = None
_mongodb_storage = None

def get_mongodb_storage():
    """Get or create MongoDB storage instance"""
    global _mongodb_storage
    if _mongodb_storage is None:
        mongodb_uri = os.getenv('MONGODB_URI')
        if mongodb_uri:
            try:
                _mongodb_storage = MongoDBStorage(mongodb_uri)
                logger.info("MongoDB storage initialized")
            except Exception as e:
                logger.warning(f"MongoDB not available: {e}")
    return _mongodb_storage

def get_pipeline():
    """Get or create TARS pipeline instance"""
    global _pipeline
    if _pipeline is None:
        storage = get_mongodb_storage()
        _pipeline = TARSPipeline(
            supportpal_api_key=os.getenv('SUPPORTPAL_API_KEY'),
            supportpal_api_url=os.getenv('SUPPORTPAL_API_URL'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            mongodb_storage=storage
        )
    return _pipeline

def get_command_handler():
    """Get or create command handler"""
    global _command_handler
    if _command_handler is None:
        static_url = "https://demerzel.ca3.dev.windscribe.org"  # For GIF URL
        _command_handler = SlackCommandHandler(signing_secret="", static_url=static_url)
    return _command_handler


@app.command("/tars")
def handle_tars_command(ack, command, respond):
    """
    Handle /tars slash command
    
    Args:
        ack: Acknowledge function (must be called within 3 seconds)
        command: Command payload from Slack
        respond: Function to send delayed responses
    """
    # Acknowledge command immediately
    ack()
    
    try:
        text = command.get('text', '').strip()
        logger.info(f"Received /tars command: {text}")
        
        handler = get_command_handler()
        cmd, hours = handler.parse_command(text)
        
        # Handle help command
        if cmd == "help":
            logger.info("Sending help response...")
            try:
                # Simplified help without GIF
                response = {
                    "text": "🦇 *TARS - Your Robin to the Support Team's Batman*\n\n"
                            "📚 *Commands:*\n"
                            "• `/tars analyze` - Analyzes tickets from last 24 hours\n"
                            "• `/tars analyze [hours]` - Custom time range (e.g., `/tars analyze 6`)\n"
                            "• `/tars analyze [days]d` - Custom time range in days (e.g., `/tars analyze 7d`)\n"
                            "• `/tars help` - Shows this message\n\n"
                            "⚡ Analysis takes 30-60 seconds | 🤖 Powered by OpenAI GPT-4o"
                }
                respond(response)
                logger.info("Help response sent successfully")
            except Exception as e:
                logger.error(f"Error sending help response: {e}", exc_info=True)
            return
        
        # Handle errors
        if cmd in ["error", "unknown"]:
            response = handler.format_error_response("invalid" if cmd == "error" else "unknown")
            respond(response)
            return
        
        # Handle analyze command
        if cmd == "analyze":
            # Send immediate acknowledgment
            respond(handler.format_analyzing_response(hours))
            
            # Run analysis
            try:
                logger.info(f"Starting analysis for {hours} hours")
                pipeline = get_pipeline()
                success = pipeline.run_analysis(hours=hours)
                
                if not success:
                    respond({
                        "text": "❌ Analysis failed. No tickets found or an error occurred. Check logs for details."
                    })
                    
            except Exception as e:
                logger.error(f"Analysis error: {e}", exc_info=True)
                respond({
                    "text": f"❌ Analysis error: {str(e)}"
                })
        
    except Exception as e:
        logger.error(f"Command handler error: {e}", exc_info=True)
        respond({
            "text": f"❌ An error occurred: {str(e)}"
        })


def start_socket_mode():
    """Start the Socket Mode handler"""
    socket_token = os.getenv('SLACK_APP_TOKEN')
    
    if not socket_token:
        logger.error("SLACK_APP_TOKEN not found in environment variables!")
        raise ValueError("SLACK_APP_TOKEN is required for Socket Mode")
    
    logger.info("🚀 Starting TARS Slack Socket Mode...")
    handler = SocketModeHandler(app, socket_token)
    handler.start()  # This blocks and keeps the connection alive


if __name__ == "__main__":
    start_socket_mode()
