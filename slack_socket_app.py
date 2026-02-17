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

def get_pipeline():
    """Get or create TARS pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = TARSPipeline(
            supportpal_api_key=os.getenv('SUPPORTPAL_API_KEY'),
            supportpal_api_url=os.getenv('SUPPORTPAL_API_URL'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL')
        )
    return _pipeline

def get_command_handler():
    """Get or create command handler"""
    global _command_handler
    if _command_handler is None:
        base_url = "https://demerzel.ca3.dev.windscribe.org"  # For GIF URL
        _command_handler = SlackCommandHandler(signing_secret=None, base_url=base_url)
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
            response = handler.format_help_response()
            respond(response)
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
