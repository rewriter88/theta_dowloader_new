"""
Configuration file for Theta Data Downloader
This file contains all configuration settings for the application
"""

from datetime import datetime, timedelta

# Download Configuration
DOWNLOAD_CONFIG = {
    # Symbols to download (QQQ only as requested)
    "symbols": ["QQQ"],
    
    # Date range for download (QQQ historical data from subscription limit to existing data)
    "start_date": "2016-01-01",  # Standard subscription limit - earliest available date
    "end_date": "2022-08-21",    # Day before existing data starts (you have 2022-08-22 onwards)
    
    # Time interval for data
    "interval": "1m",  # Options: 1m, 5m, 15m, 30m, 1h, 4h
    
    # Maximum concurrent connections (simple fixed limit)
    "max_concurrent": 4,  # Simple fixed concurrency
    
    # Theta Terminal URL
    "base_url": "http://localhost:25503",
    
    # Smart download settings
    "work_backwards": False,  # Use simple forward chronological order
    "max_consecutive_failures": 5,  # Low limit - just skip missing dates
    "chunk_size": 10,  # Small chunks for simple processing
    
    # Adaptive Concurrency Settings
    "adaptive_concurrency": False,  # Disable complex adaptive features
    
    # Simple Mode Settings
    "skip_existing_check": True,  # Skip scanning for existing files - just download requested dates
}

# Output Configuration
OUTPUT_CONFIG = {
    # Base directory where data will be stored on external SSD
    "base_dir": "/Volumes/SSD 4TB/Theta_Data",
    
    # Directory structure: base_dir/options/SYMBOL/YYYY-MM-DD_to_YYYY-MM-DD/
    "options_base_dir": "/Volumes/SSD 4TB/Theta_Data/options",
    
    # File naming format
    "filename_format": "{symbol}_options_{date}_{interval}.csv",
    
    # Logging configuration
    "log_file": "bulk_downloader.log",
    "log_level": "INFO"
}

# Helper function to get date range automatically
def get_recent_trading_days(days=4):
    """Get the last N trading days (excluding weekends)."""
    end_date = datetime.now()
    dates = []
    current = end_date
    
    while len(dates) < days:
        # Only include weekdays (Monday=0, Friday=4)
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current -= timedelta(days=1)
    
    return dates[-1], dates[0]  # start_date, end_date

def get_organized_output_dir(symbol, start_date, end_date):
    """Generate organized output directory path."""
    # Create path: base_dir/options/SYMBOL/YYYY-MM-DD_to_YYYY-MM-DD/
    date_range = f"{start_date}_to_{end_date}"
    organized_path = f"{OUTPUT_CONFIG['options_base_dir']}/{symbol}/{date_range}"
    return organized_path

# Uncomment to use automatic recent trading days instead of fixed dates
# DOWNLOAD_CONFIG["start_date"], DOWNLOAD_CONFIG["end_date"] = get_recent_trading_days(4)
