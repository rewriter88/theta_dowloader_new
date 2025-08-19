#!/usr/bin/env python3
"""
Bulk Options Downloader for Theta Data
Downloads QQQ options data from a specified date range using the bulk API endpoint.
"""

import asyncio
import aiohttp
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from typing import List

# Configuration
SYMBOL = "QQQ"
START_DATE = "2017-08-08"  # Target date (oldest)
END_DATE = "2022-08-21"     # Most recent date to download (working backwards)
INTERVAL = "1m"
OUTPUT_DIR = Path("/Volumes/SSD 4TB/Theta Terminal/QQQ/2025-08-08/QQQ/2017-08-08_to_2025-08-08")
BASE_URL = "http://localhost:25503"
MAX_CONCURRENT = 4  # Conservative concurrency

class ProgressTracker:
    def __init__(self, total_files):
        self.total_files = total_files
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        self.last_update = time.time()
        
    def update(self, status='completed'):
        if status == 'completed':
            self.completed += 1
        elif status == 'failed':
            self.failed += 1
        elif status == 'skipped':
            self.skipped += 1
            
        # Update every second or when done
        current_time = time.time()
        if current_time - self.last_update >= 1 or self.is_done():
            self.display()
            self.last_update = current_time
    
    def is_done(self):
        return (self.completed + self.failed + self.skipped) >= self.total_files
    
    def display(self):
        total_processed = self.completed + self.failed + self.skipped
        elapsed = time.time() - self.start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        
        # Calculate percentage
        percent = (total_processed / self.total_files) * 100
        
        # Progress bar
        bar_length = 30
        filled = int(bar_length * total_processed // self.total_files)
        bar = 'ˆ' * filled + '‘' * (bar_length - filled)
        
        # ETA calculation
        if rate > 0:
            remaining = self.total_files - total_processed
            eta_seconds = remaining / rate
            if eta_seconds < 60:
                eta = f"{eta_seconds:.0f}s"
            elif eta_seconds < 3600:
                eta = f"{eta_seconds/60:.1f}m"
            else:
                eta = f"{eta_seconds/3600:.1f}h"
        else:
            eta = "calculating..."
        
        # Status line
        status = f"\r[{bar}] {percent:.1f}% | "
        status += f" {self.completed} | í {self.skipped} | L {self.failed} | "
        status += f"Total: {total_processed}/{self.total_files} | "
        status += f"Rate: {rate:.1f}/s | ETA: {eta}"
        
        sys.stdout.write(status)
        sys.stdout.flush()
        
        if self.is_done():
            print()  # New line when done

async def download_single_date(session, date_str, semaphore, progress):
    """Download options data for a single date."""
    async with semaphore:
        try:
            # Format date for API (remove dashes)
            api_date = date_str.replace("-", "")
            
            # Create filename
            filename = f"{SYMBOL}_options_{date_str}_{INTERVAL}.csv"
            filepath = OUTPUT_DIR / filename
            
            # Skip if file already exists and has data
            if filepath.exists() and filepath.stat().st_size > 1000:
                progress.update('skipped')
                return True
            
            # Construct URL with the exact format specified
            url = f"{BASE_URL}/v3/option/history/quote"
            params = {
                'symbol': SYMBOL,
                'expiration': '*',
                'date': api_date,
                'interval': INTERVAL
            }
            
            async with session.get(url, params=params, timeout=60) as response:
                if response.status == 200:
                    content = await response.text()
                    if content and len(content) > 100:
                        # Save to file
                        filepath.write_text(content)
                        progress.update('completed')
                        return True
                    else:
                        progress.update('failed')
                        return False
                else:
                    progress.update('failed')
                    return False
                    
        except asyncio.TimeoutError:
            progress.update('failed')
            return False
        except Exception as e:
            progress.update('failed')
            return False

def get_trading_days(start_date, end_date):
    """Generate list of trading days (excluding weekends)."""
    trading_days = []
    current = datetime.strptime(end_date, "%Y-%m-%d")
    start = datetime.strptime(start_date, "%Y-%m-%d")
    
    while current >= start:
        # Skip weekends (5=Saturday, 6=Sunday)
        if current.weekday() < 5:
            trading_days.append(current.strftime("%Y-%m-%d"))
        current -= timedelta(days=1)
    
    return trading_days

async def main():
    """Main download function."""
    print(f"=Ê Theta Data Bulk Options Downloader")
    print(f"   Symbol: {SYMBOL}")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Interval: {INTERVAL}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Concurrency: {MAX_CONCURRENT}")
    print()
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get trading days
    trading_days = get_trading_days(START_DATE, END_DATE)
    print(f"=Å Found {len(trading_days)} potential trading days to process")
    
    # Check existing files
    existing = 0
    for date in trading_days:
        filepath = OUTPUT_DIR / f"{SYMBOL}_options_{date}_{INTERVAL}.csv"
        if filepath.exists() and filepath.stat().st_size > 1000:
            existing += 1
    
    print(f"=Á {existing} files already exist")
    print(f"=å {len(trading_days) - existing} files to download")
    print()
    
    # Initialize progress tracker
    progress = ProgressTracker(len(trading_days))
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        # Create download tasks
        tasks = []
        for date in trading_days:
            task = download_single_date(session, date, semaphore, progress)
            tasks.append(task)
        
        # Execute all tasks
        await asyncio.gather(*tasks)
    
    # Final summary
    print()
    print(f" Download complete!")
    print(f"   Completed: {progress.completed}")
    print(f"   Skipped: {progress.skipped}")
    print(f"   Failed: {progress.failed}")
    print(f"   Time: {time.time() - progress.start_time:.1f} seconds")

if __name__ == "__main__":
    asyncio.run(main())