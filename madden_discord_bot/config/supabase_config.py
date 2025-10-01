"""
Supabase configuration for the Franchise Player Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # For admin operations

# Database table names
TABLES = {
    'users': 'users',
    'player_cards': 'player_cards',
    'gotw': 'gotw',
    'nfl_schedule': 'nfl_schedule',
    'stream_links': 'stream_links',
    'server_settings': 'server_settings'
}

# Validation
def validate_supabase_config():
    """Validate that required Supabase configuration is present"""
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL environment variable is required")
    
    if not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_ANON_KEY environment variable is required")
    
    return True

# Connection settings
CONNECTION_SETTINGS = {
    'timeout': 30,  # seconds
    'retry_attempts': 3,
    'retry_delay': 1,  # seconds
}
