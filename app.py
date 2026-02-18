"""
Flask web server for TARS
Provides health check endpoint, manual analysis trigger, and dashboard API
"""
import os
import logging
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
from pipeline.analyzer import TARSPipeline
from storage.mongodb_client import MongoDBStorage

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

# Initialize globals
pipeline = None
mongodb_storage = None

def get_mongodb_storage():
    """Get or create MongoDB storage instance"""
    global mongodb_storage
    if mongodb_storage is None:
        mongodb_uri = os.getenv('MONGODB_URI')
        if mongodb_uri:
            try:
                mongodb_storage = MongoDBStorage(mongodb_uri)
                logger.info("MongoDB storage initialized")
            except Exception as e:
                logger.warning(f"MongoDB not available: {e}")
    return mongodb_storage

def get_pipeline():
    """Get or create TARS pipeline instance"""
    global pipeline
    if pipeline is None:
        storage = get_mongodb_storage()
        pipeline = TARSPipeline(
            supportpal_api_key=os.getenv('SUPPORTPAL_API_KEY'),
            supportpal_api_url=os.getenv('SUPPORTPAL_API_URL'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            mongodb_storage=storage
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


# ============================================================================
# Dashboard API Endpoints
# ============================================================================

@app.route('/api/analyses', methods=['GET'])
def get_analyses():
    """Get list of recent analyses"""
    try:
        storage = get_mongodb_storage()
        if not storage:
            return jsonify({'error': 'MongoDB not configured'}), 503
        
        limit = request.args.get('limit', default=30, type=int)
        analyses = storage.get_recent_analyses(limit=limit)
        
        return jsonify({
            'count': len(analyses),
            'analyses': analyses
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching analyses: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyses/<analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    """Get specific analysis by ID"""
    try:
        storage = get_mongodb_storage()
        if not storage:
            return jsonify({'error': 'MongoDB not configured'}), 503
        
        analysis = storage.get_analysis_by_id(analysis_id)
        
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Error fetching analysis: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/trends', methods=['GET'])
def get_trends():
    """Get trend data for charts"""
    try:
        storage = get_mongodb_storage()
        if not storage:
            return jsonify({'error': 'MongoDB not configured'}), 503
        
        days = request.args.get('days', default=30, type=int)
        trend_data = storage.get_trend_data(days=days)
        
        return jsonify(trend_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching trends: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard summary statistics"""
    try:
        storage = get_mongodb_storage()
        if not storage:
            return jsonify({'error': 'MongoDB not configured'}), 503
        
        stats = storage.get_dashboard_stats()
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting TARS Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
