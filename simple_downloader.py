#!/usr/bin/env python3
"""
Simple Theta Data Downloader - Bare Bones Version

Downloads QQQ options data from start to end date.
One CSV file per trading day, directly in the QQQ folder.
Shows progress bar. No complex logic.
"""

import asyncio
import aiohttp
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from market_calendar import MarketCalendar
from simple_config import *

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
        sys.stdout.write(f"\r📈 [{bar}] {percent:.1f}% ({self.completed}/{self.total_files}) | {rate:.1f} files/s | ETA: {eta} | 🔄 DOWNLOADING")
        sys.stdout.flush()

async def download_single_date(session, symbol, date, interval, output_dir):
    """Download options data for a single date."""
    # Format date for API (remove dashes)
    api_date = date.replace("-", "")
    
    # Create filename
    filename = f"{symbol}_options_{date}_{interval}.csv"
    filepath = output_dir / filename
    
    # Skip if file already exists
    if filepath.exists():
        print(f"⏭️  {date}: File already exists")
        return True
    
    # Construct URL
    url = f"{BASE_URL}/v3/option/history/quote"
    params = {
        'symbol': symbol,
        'expiration': '*',
        'date': api_date,
        'interval': interval
    }
    
    try:
        print(f"🔍 {date}: Requesting {url}?{params}")
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
                    print(f"⚠️  {date}: No data available (content too small)")
                    return False
            else:
                print(f"❌ {date}: HTTP {response.status}")
                return False
    except Exception as e:
        print(f"💥 {date}: Error - {str(e)}")
        return False

async def download_date_range(symbol, start_date, end_date, interval, output_dir):
    """Download options data for a date range."""
    # Get trading days
    market_cal = MarketCalendar()
    trading_days = market_cal.get_trading_days(start_date, end_date)
    
    print(f"🎯 {symbol}: {start_date} to {end_date} ({len(trading_days)} trading days)")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize progress bar
    progress = SimpleProgressBar(len(trading_days))
    
    # Create session with connection limits
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Process dates in chunks to respect concurrency limits
        chunk_size = MAX_CONCURRENT
        successful_downloads = 0
        
        for i in range(0, len(trading_days), chunk_size):
            chunk_dates = trading_days[i:i + chunk_size]
            
            # Create tasks for this chunk
            tasks = [
                download_single_date(session, symbol, date, interval, output_dir)
                for date in chunk_dates
            ]
            
            # Execute chunk
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update progress for each completed download
            for result in results:
                if result is True:
                    successful_downloads += 1
                progress.update(1)
        
        # Final newline and summary
        print(f"\n✅ Download complete! {successful_downloads} files downloaded to {output_dir}")

def main():
    """Main function."""
    print("🚀 Simple Theta Data Downloader")
    print(f"   Symbol: {SYMBOL}")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Output: {OUTPUT_DIR}")
    print()
    
    # Convert to Path object
    output_path = Path(OUTPUT_DIR)
    
    # Run the download
    asyncio.run(download_date_range(
        SYMBOL, START_DATE, END_DATE, INTERVAL, output_path
    ))

if __name__ == "__main__":
    main()
