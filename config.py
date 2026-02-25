"""
Configuration module for Project TARS
Loads and validates environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # SupportPal API Configuration
    SUPPORTPAL_API_KEY = os.getenv('SUPPORTPAL_API_KEY')
    SUPPORTPAL_API_URL = os.getenv('SUPPORTPAL_API_URL')
    # Optional: numeric brand ID to restrict ticket fetching to Windscribe only.
    # Leave blank to fetch all brands. Find the ID by running: python3 -c
    # "from pipeline.supportpal_client import SupportPalClient; ..."
    # or by checking the SupportPal admin panel Settings > Brands.
    _brand_id_raw = os.getenv('SUPPORTPAL_BRAND_ID', '').strip()
    SUPPORTPAL_BRAND_ID: 'Optional[int]' = int(_brand_id_raw) if _brand_id_raw else None
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Slack Configuration
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
    SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')  # Optional - only for webhook mode
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')  # For Socket Mode + chat.postMessage
    SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')  # Socket Mode app-level token
    SLACK_CHANNEL_ID = os.getenv('SLACK_CHANNEL_ID')  # Channel for TARS daily reports
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI')  # Optional - for historical data storage
    
    # Schedule Configuration (optional)
    SCHEDULE_CRON = os.getenv('SCHEDULE_CRON', '0 9 * * *')  # Default: Daily at 9 AM
    
    # Server Configuration
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    @classmethod
    def validate(cls):
        """
        Validate that all required configuration is present
        Raises ValueError if any required config is missing
        """
        required_vars = {
            'SUPPORTPAL_API_KEY': cls.SUPPORTPAL_API_KEY,
            'SUPPORTPAL_API_URL': cls.SUPPORTPAL_API_URL,
            'OPENAI_API_KEY': cls.OPENAI_API_KEY,
            'SLACK_BOT_TOKEN': cls.SLACK_BOT_TOKEN,
            'SLACK_CHANNEL_ID': cls.SLACK_CHANNEL_ID,
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file or environment configuration."
            )
        
        # Validate URL formats
        if not cls.SUPPORTPAL_API_URL.startswith(('http://', 'https://')):
            raise ValueError("SUPPORTPAL_API_URL must start with http:// or https://")
        
        if cls.SLACK_WEBHOOK_URL and not cls.SLACK_WEBHOOK_URL.startswith('https://'):
            raise ValueError("SLACK_WEBHOOK_URL must start with https://")
        
        if not cls.OPENAI_API_KEY.startswith('sk-'):
            raise ValueError("OPENAI_API_KEY appears to be invalid (should start with 'sk-')")
        
        return True
    
    @classmethod
    def get_summary(cls):
        """Return a safe summary of current configuration (without secrets)"""
        return {
            'supportpal_url': cls.SUPPORTPAL_API_URL,
            'openai_configured': bool(cls.OPENAI_API_KEY),
            'slack_configured': bool(cls.SLACK_BOT_TOKEN),
            'slack_channel_id': cls.SLACK_CHANNEL_ID,
            'schedule': cls.SCHEDULE_CRON,
            'port': cls.PORT,
            'debug': cls.DEBUG,
        }


# Create a singleton instance
config = Config()
