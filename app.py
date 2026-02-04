"""
Flask web server for TARS
Provides health check endpoint and Slack slash command support
"""
import os
import logging
import requests
from threading import Thread
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
from pipeline.analyzer import TARSPipeline
from utils.slack_commands import SlackCommandHandler

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Initialize TARS pipeline
pipeline = None
command_handler = None

def get_pipeline():
    """Get or create TARS pipeline instance"""
    global pipeline
    if pipeline is None:
        pipeline = TARSPipeline(
            supportpal_api_key=os.getenv('SUPPORTPAL_API_KEY'),
            supportpal_api_url=os.getenv('SUPPORTPAL_API_URL'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL')
        )
    return pipeline

def get_command_handler():
    """Get or create Slack command handler instance"""
    global command_handler
    if command_handler is None:
        signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        # Get base URL for static files (use Render URL if available, fallback to localhost)
        base_url = os.getenv('RENDER_EXTERNAL_URL', f"http://localhost:{os.getenv('PORT', 5000)}")
        if signing_secret:
            command_handler = SlackCommandHandler(signing_secret, base_url)
    return command_handler


@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        'name': 'TARS',
        'description': 'Ticket Analysis & Reporting System',
        'version': '1.0.0',
        'status': 'running'
    })


@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'service': 'TARS'
    }), 200


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (like tars.gif)"""
    return send_from_directory('static', filename)


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Manually trigger analysis
    Can be called by external triggers (not for Slack - use /slack/command instead)
    """
    try:
        logger.info("Manual analysis triggered")
        
        # Get hours parameter (default 24)
        hours = request.json.get('hours', 24) if request.json else 24
        
        # Run analysis in foreground
        pipeline_instance = get_pipeline()
        success = pipeline_instance.run_analysis(hours=hours)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Analysis completed and posted to Slack'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Analysis failed - check logs'
            }), 500
            
    except Exception as e:
        logger.error(f"Analysis endpoint error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def run_analysis_background(hours: int, response_url: str):
    """
    Run analysis in background and post results to Slack
    
    Args:
        hours: Number of hours to analyze
        response_url: Slack response URL to post results to
    """
    try:
        logger.info(f"Background analysis started for {hours} hours")
        pipeline_instance = get_pipeline()
        
        # Run analysis (posts to webhook automatically)
        success = pipeline_instance.run_analysis(hours=hours)
        
        if not success:
            # Post error message to response URL
            error_msg = {
                "text": "❌ Analysis failed. Please check logs or contact support."
            }
            requests.post(response_url, json=error_msg)
            
    except Exception as e:
        logger.error(f"Background analysis error: {e}", exc_info=True)
        error_msg = {
            "text": f"❌ Analysis error: {str(e)}"
        }
        try:
            requests.post(response_url, json=error_msg)
        except:
            pass


@app.route('/slack/command', methods=['POST'])
def slack_command():
    """
    Handle Slack slash commands (/tars)
    """
    try:
        handler = get_command_handler()
        
        if not handler:
            logger.error("Slack command handler not initialized (missing signing secret)")
            return jsonify({
                'text': '❌ Slash commands not configured. Please contact admin.'
            }), 200
        
        # Get request data
        timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
        signature = request.headers.get('X-Slack-Signature', '')
        body = request.get_data(as_text=True)
        
        # Verify signature
        if not handler.verify_signature(timestamp, signature, body):
            logger.warning("Invalid Slack signature")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse form data
        text = request.form.get('text', '').strip()
        response_url = request.form.get('response_url', '')
        
        logger.info(f"Slash command received: /tars {text}")
        
        # Parse command
        command, hours = handler.parse_command(text)
        
        # Handle help command
        if command == "help":
            return jsonify(handler.format_help_response()), 200
        
        # Handle error in parsing
        if command == "error":
            return jsonify(handler.format_error_response("invalid")), 200
        
        # Handle unknown command
        if command == "unknown":
            return jsonify(handler.format_error_response("unknown")), 200
        
        # Handle analyze command
        if command == "analyze":
            # Respond immediately with "analyzing" message
            immediate_response = handler.format_analyzing_response(hours)
            
            # Start analysis in background thread
            thread = Thread(
                target=run_analysis_background,
                args=(hours, response_url)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify(immediate_response), 200
        
        # Fallback
        return jsonify(handler.format_error_response("unknown")), 200
            
    except Exception as e:
        logger.error(f"Slack command error: {e}", exc_info=True)
        return jsonify({
            'text': f'❌ An error occurred: {str(e)}'
        }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting TARS Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
