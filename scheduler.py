"""
Scheduler for automated TARS analysis runs
Uses APScheduler to run analysis on a cron schedule
"""
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from pipeline.analyzer import TARSPipeline
from storage.mongodb_client import MongoDBStorage

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TARSScheduler:
    """Scheduler for automated TARS analysis runs"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.scheduler = BackgroundScheduler()
        self.pipeline = None
        self.mongodb_storage = None
        
    def init_storage(self):
        """Initialize MongoDB storage"""
        if self.mongodb_storage is None:
            mongodb_uri = os.getenv('MONGODB_URI')
            if mongodb_uri:
                try:
                    self.mongodb_storage = MongoDBStorage(mongodb_uri)
                    logger.info("MongoDB storage initialized for scheduler")
                except Exception as e:
                    logger.warning(f"MongoDB not available: {e}")
        
    def init_pipeline(self):
        """Initialize TARS pipeline"""
        if self.pipeline is None:
            self.init_storage()
            _brand_raw = os.getenv('SUPPORTPAL_BRAND_ID', '').strip()
            self.pipeline = TARSPipeline(
                supportpal_api_key=os.getenv('SUPPORTPAL_API_KEY'),
                supportpal_api_url=os.getenv('SUPPORTPAL_API_URL'),
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                slack_bot_token=os.getenv('SLACK_BOT_TOKEN'),
                slack_channel_id=os.getenv('SLACK_CHANNEL_ID'),
                slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),  # legacy fallback
                mongodb_storage=self.mongodb_storage,
                supportpal_brand_id=int(_brand_raw) if _brand_raw else None,
            )
    
    def run_scheduled_analysis(self):
        """Run the analysis (called by scheduler)"""
        try:
            logger.info("🕐 Scheduled analysis triggered")
            self.init_pipeline()
            success = self.pipeline.run_analysis(hours=24)
            
            if success:
                logger.info("✅ Scheduled analysis completed successfully")
            else:
                logger.error("❌ Scheduled analysis failed")
                
        except Exception as e:
            logger.error(f"Scheduled analysis error: {e}", exc_info=True)
    
    def start(self, cron_expression: str = "0 9 * * *"):
        """
        Start the scheduler
        
        Args:
            cron_expression: Cron expression for schedule (default: 9 AM daily)
                Format: minute hour day month day_of_week
                Examples:
                    "0 9 * * *"    = Daily at 9 AM
                    "0 */6 * * *"  = Every 6 hours
                    "0 0 * * *"    = Daily at midnight
        """
        try:
            # Parse cron expression
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}")
            
            minute, hour, day, month, day_of_week = parts
            
            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            # Add job to scheduler
            self.scheduler.add_job(
                self.run_scheduled_analysis,
                trigger=trigger,
                id='tars_analysis',
                name='TARS Automated Analysis',
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            
            logger.info(f"✅ Scheduler started with cron: {cron_expression}")
            logger.info(f"   Next run: {self.scheduler.get_job('tars_analysis').next_run_time}")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
