#!/usr/bin/env python3
"""
QQQ PUT Options Data Downloader
Downloads QQQ put options data from 2016-01-01 to 2025-08-07 with 1-minute resolution.
Saves data to /Volumes/SSD 4TB/Theta Terminal/QQQ/2025-08-08/ directory.
"""

import asyncio
import aiohttp
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from market_calendar import MarketCalendar

# Configuration
SYMBOL = "QQQ"
START_DATE = "2022-08-22"
END_DATE = "2025-08-07"
INTERVAL = "1m"
BASE_URL = "http://localhost:25503"
MAX_CONCURRENT = 4
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
        sys.stdout.write(f"\r📈 [{bar}] {percent:.1f}% ({self.completed}/{self.total_files}) | {rate:.1f} files/s | ETA: {eta} | 🔄 DOWNLOADING PUTS")
        sys.stdout.flush()

async def download_single_date(session, symbol, date, interval, output_dir):
    """Download PUT options data for a single date."""
    # Format date for API (remove dashes)
    api_date = date.replace("-", "")
    
    # Create filename with PUT designation
    filename = f"{symbol}_PUT_options_{date}_{interval}.csv"
    filepath = output_dir / filename
    
    # Skip if file already exists
    if filepath.exists():
        print(f"⏭️  {date}: File already exists")
        return True
    
    # Construct URL for PUT options only
    url = f"{BASE_URL}/v3/option/history/quote"
    params = {
        'symbol': symbol,
        'expiration': '*',
        'right': 'P',  # P = PUT options only
        'date': api_date,
        'interval': interval
    }
    
    try:
        print(f"🔍 {date}: Requesting PUT options {url}?{params}")
        async with session.get(url, params=params) as response:
            print(f"📡 {date}: Response status {response.status}")
            if response.status == 200:
                content = await response.text()
                content_size = len(content) if content else 0
                print(f"📦 {date}: Content size {content_size} bytes")
                if content and content_size > 100:  # Has actual data beyond just headers
                    # Save to file
                    with open(filepath, 'w') as f:
                        f.write(content)
                    print(f"✅ {date}: Saved {filename} ({content_size:,} bytes)")
                    return True
                else:
                    print(f"⚠️  {date}: No PUT data available (content too small)")
                    return False
            else:
                print(f"❌ {date}: HTTP {response.status}")
                return False
    except Exception as e:
        print(f"💥 {date}: Error - {str(e)}")
        return False

async def check_available_data():
    """Check what data is actually available for QQQ options."""
    print("🔍 Checking available QQQ options data...")
    
    # Check available expirations
    url = f"{BASE_URL}/v3/option/list/expirations"
    params = {'symbol': 'QQQ'}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    print(f"📅 Available expirations sample: {content[:200]}...")
                    return True
                else:
                    print(f"❌ Failed to get expirations: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"💥 Error checking available data: {e}")
        return False

async def download_date_range(symbol, start_date, end_date, interval, output_dir):
    """Download PUT options data for a date range."""
    # First check if we can access the API
    if not await check_available_data():
        print("❌ Cannot access Theta Data API. Is Theta Terminal running?")
        return
    
    # Get trading days
    market_cal = MarketCalendar()
    trading_days = market_cal.get_trading_days(start_date, end_date)
    
    print(f"🎯 {symbol} PUT OPTIONS: {start_date} to {end_date} ({len(trading_days)} trading days)")
    print(f"📁 Output directory: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize progress bar
    progress = SimpleProgressBar(len(trading_days))
    
    # Create session with connection limits
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        successful_downloads = 0
        
        # Process each date sequentially for debugging
        for i, date in enumerate(trading_days):
            print(f"\n📅 Processing {date} ({i+1}/{len(trading_days)})")
            
            result = await download_single_date(session, symbol, date, interval, output_dir)
            if result is True:
                successful_downloads += 1
            
            progress.update(1)
        
        # Final newline and summary
        print(f"\n✅ Download complete! {successful_downloads} PUT options files downloaded to {output_dir}")
        print(f"📊 Success rate: {successful_downloads}/{len(trading_days)} ({successful_downloads/len(trading_days)*100:.1f}%)")

def main():
    """Main function."""
    print("🚀 QQQ PUT Options Data Downloader")
    print(f"   Symbol: {SYMBOL} (PUT OPTIONS ONLY)")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Resolution: {INTERVAL}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Max Concurrent: {MAX_CONCURRENT}")
    print()
    
    # Convert to Path object
    output_path = Path(OUTPUT_DIR)
    
    # Run the download
    asyncio.run(download_date_range(
        SYMBOL, START_DATE, END_DATE, INTERVAL, output_path
    ))

if __name__ == "__main__":
    main()