"""
Flask web server for TARS
Provides health check endpoint and will support Slack slash commands
"""
import os
import logging
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from pipeline.analyzer import TARSPipeline

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize TARS pipeline
pipeline = None

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


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Manually trigger analysis
    Can be called by Slack slash commands or external triggers
    """
    try:
        logger.info("Manual analysis triggered")
        
        # Get hours parameter (default 24)
        hours = request.json.get('hours', 24) if request.json else 24
        
        # Run analysis in foreground (for now)
        # TODO: Make this async with background worker
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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting TARS Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
