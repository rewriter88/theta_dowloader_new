#!/usr/bin/env python3
"""
QQQ PUT Options Data Downloader using MCP ThetaData Tools
Downloads QQQ put options data from 2022-08-22 to 2025-08-07 with 1-minute resolution.
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from market_calendar import MarketCalendar
import subprocess
import json

# Configuration
SYMBOL = "QQQ"
START_DATE = "2022-08-22"
END_DATE = "2025-08-07"
INTERVAL = "1m"
OUTPUT_DIR = "/Volumes/SSD 4TB/Theta Terminal/QQQ/2025-08-08/"

class SimpleProgressBar:
    def __init__(self, total_files):
        self.total_files = total_files
        self.completed = 0
        self.start_time = time.time()
        
    def update(self, increment=1):
        self.completed += increment
        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed if elapsed > 0 else 0
        
        # Calculate percentage and progress bar
        percent = (self.completed / self.total_files) * 100
        bar_length = 20
        filled_length = int(bar_length * self.completed // self.total_files)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # ETA calculation
        if rate > 0:
            remaining = self.total_files - self.completed
            eta_seconds = remaining / rate
            if eta_seconds < 60:
                eta = f"{eta_seconds:.0f}s"
            elif eta_seconds < 3600:
                eta = f"{eta_seconds/60:.1f}m"
            else:
                eta = f"{eta_seconds/3600:.1f}h"
        else:
            eta = "Calculating..."
        
        # Print progress line
        sys.stdout.write(f"\r📈 [{bar}] {percent:.1f}% ({self.completed}/{self.total_files}) | {rate:.1f} files/s | ETA: {eta} | 🔄 DOWNLOADING PUTS (MCP)")
        sys.stdout.flush()

def download_single_date_mcp(symbol, date, interval, output_dir, expiration="*"):
    """Download PUT options data for a single date using MCP."""
    # Format date for API (remove dashes)
    api_date = date.replace("-", "")
    
    # Create filename with PUT designation
    filename = f"{symbol}_PUT_options_{date}_{interval}.csv"
    filepath = output_dir / filename
    
    # Skip if file already exists
    if filepath.exists():
        print(f"⏭️  {date}: File already exists")
        return True
    
    try:
        print(f"🔍 {date}: Downloading PUT options via MCP...")
        
        # This script is designed to be run within Claude Code environment
        # where MCP tools are available directly
        print(f"📡 {date}: This requires running within Claude Code with MCP access")
        print(f"⚠️  {date}: Please run this through Claude Code interface")
        return False
        
    except Exception as e:
        print(f"💥 {date}: Error - {str(e)}")
        return False

def download_date_range_mcp(symbol, start_date, end_date, interval, output_dir):
    """Download PUT options data for a date range using MCP."""
    # Get trading days
    market_cal = MarketCalendar()
    trading_days = market_cal.get_trading_days(start_date, end_date)
    
    print(f"🎯 {symbol} PUT OPTIONS (MCP): {start_date} to {end_date} ({len(trading_days)} trading days)")
    print(f"📁 Output directory: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize progress bar
    progress = SimpleProgressBar(len(trading_days))
    
    successful_downloads = 0
    
    # Process each date
    for i, date in enumerate(trading_days):
        print(f"\n📅 Processing {date} ({i+1}/{len(trading_days)})")
        
        result = download_single_date_mcp(symbol, date, interval, output_dir)
        if result is True:
            successful_downloads += 1
        
        progress.update(1)
    
    # Final summary
    print(f"\n✅ MCP Download complete! {successful_downloads} PUT options files downloaded to {output_dir}")
    print(f"📊 Success rate: {successful_downloads}/{len(trading_days)} ({successful_downloads/len(trading_days)*100:.1f}%)")

def main():
    """Main function."""
    print("🚀 QQQ PUT Options Data Downloader (MCP Version)")
    print(f"   Symbol: {SYMBOL} (PUT OPTIONS ONLY)")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Resolution: {INTERVAL}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Method: MCP ThetaData Tools")
    print()
    
    # Convert to Path object
    output_path = Path(OUTPUT_DIR)
    
    # Run the download
    download_date_range_mcp(SYMBOL, START_DATE, END_DATE, INTERVAL, output_path)

if __name__ == "__main__":
    main()