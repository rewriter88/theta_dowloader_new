"""
Configuration file for Theta Data Downloader
This file contains all configuration settings for the application
"""

from datetime import datetime, timedelta

# Download Configuration
DOWNLOAD_CONFIG = {
    # Symbols to download (add/remove as needed)
    "symbols": ["QQQ"],  # Testing with just QQQ first
    
    # Date range for download
    "start_date": "2024-11-01",  # YYYY-MM-DD format
    "end_date": "2024-11-04",    # YYYY-MM-DD format (4 trading days for test)
    
    # Time interval for data
    "interval": "1m",  # Options: 1m, 5m, 15m, 30m, 1h, 4h, 1d
    
    # Maximum concurrent connections (Standard subscription = 8)
    "max_concurrent": 8,
    
    # Theta Terminal URL
    "base_url": "http://localhost:25503"
}

# Output Configuration
OUTPUT_CONFIG = {
    # Directory where data will be stored
    "results_dir": "results",
    "options_dir": "results/options",
    
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

# Uncomment to use automatic recent trading days instead of fixed dates
# DOWNLOAD_CONFIG["start_date"], DOWNLOAD_CONFIG["end_date"] = get_recent_trading_days(4)
