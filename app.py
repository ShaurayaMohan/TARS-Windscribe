"""
Flask web server for TARS
Provides health check endpoint, manual analysis trigger, and dashboard API
"""
import os
import logging
from flask import Flask, jsonify, request, send_from_directory, send_file
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
        _brand_raw = os.getenv('SUPPORTPAL_BRAND_ID', '').strip()
        pipeline = TARSPipeline(
            supportpal_api_key=os.getenv('SUPPORTPAL_API_KEY'),
            supportpal_api_url=os.getenv('SUPPORTPAL_API_URL'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            slack_bot_token=os.getenv('SLACK_BOT_TOKEN'),
            slack_channel_id=os.getenv('SLACK_CHANNEL_ID'),
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),  # legacy fallback
            mongodb_storage=storage,
            supportpal_brand_id=int(_brand_raw) if _brand_raw else None,
        )
    return pipeline


# Dashboard static files
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), 'dashboard', 'dist')

@app.route('/')
def home():
    """Serve React dashboard"""
    dashboard_index = os.path.join(DASHBOARD_DIR, 'index.html')
    if os.path.exists(dashboard_index):
        return send_file(dashboard_index)
    # Fallback if dashboard not built yet
    return jsonify({
        'name': 'TARS',
        'description': 'Ticket Analysis & Reporting System',
        'version': '1.0.0',
        'status': 'running',
        'note': 'Dashboard not built yet. Run: cd dashboard && npm run build'
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

@app.route('/assets/<path:filename>')
def serve_dashboard_assets(filename):
    """Serve dashboard static assets"""
    assets_dir = os.path.join(DASHBOARD_DIR, 'assets')
    if os.path.exists(assets_dir):
        return send_from_directory(assets_dir, filename)
    return jsonify({'error': 'Dashboard assets not found'}), 404

# SPA routing - serve index.html for all non-API routes
@app.route('/<path:path>')
def serve_dashboard(path):
    """Serve React dashboard for SPA routing"""
    # Don't interfere with API routes
    if path.startswith('api/') or path == 'health' or path == 'analyze':
        return jsonify({'error': 'Not found'}), 404
    
    dashboard_index = os.path.join(DASHBOARD_DIR, 'index.html')
    if os.path.exists(dashboard_index):
        return send_file(dashboard_index)
    return jsonify({'error': 'Dashboard not built'}), 404


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
            return jsonify({'count': 0, 'analyses': [], 'warning': 'MongoDB not configured'}), 200

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
            return jsonify({
                'period_days': 30,
                'total_analyses': 0,
                'total_tickets': 0,
                'total_clusters': 0,
                'avg_tickets_per_analysis': 0,
                'avg_clusters_per_analysis': 0,
                'daily_breakdown': {},
                'top_recurring_issues': [],
                'warning': 'MongoDB not configured'
            }), 200

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
            return jsonify({
                'latest_analysis': None,
                'today_analyses': 0,
                'total_analyses': 0,
                'last_7_days_tickets': 0,
                'warning': 'MongoDB not configured'
            }), 200

        stats = storage.get_dashboard_stats()

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/prompt', methods=['GET'])
def get_prompt():
    """Return the AI analysis prompt template.

    Returns the MongoDB-stored template if one exists, otherwise falls back
    to generating the default template from the hardcoded prompt (with
    {{TICKET_COUNT}} / {{ALL_TICKET_IDS}} / {{TICKETS_FORMATTED}} placeholders).
    """
    try:
        # 1. Try MongoDB first
        storage = get_mongodb_storage()
        if storage:
            stored = storage.get_prompt_template()
            if stored:
                return jsonify({'prompt': stored, 'source': 'mongodb'}), 200

        # 2. Fall back to building the default template from the hardcoded prompt
        from pipeline.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer("dummy-key-for-template-preview")

        # Build with a tiny sample, then replace the dynamic runtime values
        # with named placeholders so the user sees the editable template form.
        n = 3
        sample_tickets = [
            {
                'number': str(i), 'id': i,
                'subject': f'Sample ticket {i}',
                'first_message': 'Sample message...',
                'status': 'open', 'priority': 'normal',
            }
            for i in range(1, n + 1)
        ]
        raw_prompt = analyzer.build_analysis_prompt(sample_tickets)

        # Replace the runtime-substituted values with named placeholders
        sample_ids = list(range(1, n + 1))
        template = (
            raw_prompt
            .replace(str(n), "{{TICKET_COUNT}}", )          # ticket count
            .replace(str(sample_ids), "{{ALL_TICKET_IDS}}")  # id list
        )
        # Strip the actual ticket data block and replace with placeholder
        marker = "TICKETS TO CLASSIFY ({{TICKET_COUNT}} total):"
        if marker in template:
            before = template[:template.index(marker)].rstrip()
            template = (
                before
                + "\n\nTICKETS TO CLASSIFY ({{TICKET_COUNT}} total):\n{{TICKETS_FORMATTED}}\n\n"
                + "FINAL CHECK before outputting: verify sum of all cluster volumes == "
                + "{{TICKET_COUNT}} and every ID from {{ALL_TICKET_IDS}} appears exactly "
                + "once across all ticket_ids arrays."
            )

        return jsonify({'prompt': template, 'source': 'default'}), 200

    except Exception as e:
        logger.error(f"Error fetching prompt template: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/prompt', methods=['POST'])
def save_prompt():
    """Save a custom prompt template to MongoDB."""
    try:
        storage = get_mongodb_storage()
        if not storage:
            return jsonify({'error': 'MongoDB not configured'}), 503

        body = request.get_json(silent=True) or {}
        prompt_text = body.get('prompt', '').strip()

        if not prompt_text:
            return jsonify({'error': 'prompt field is required and cannot be empty'}), 400

        success = storage.save_prompt_template(prompt_text)
        if success:
            return jsonify({'status': 'saved'}), 200
        else:
            return jsonify({'error': 'Failed to save prompt'}), 500

    except Exception as e:
        logger.error(f"Error saving prompt template: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting TARS Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
