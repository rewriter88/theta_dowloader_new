#!/usr/bin/env python3
"""
Simple Debug Theta Data Downloader - Sequential processing with detailed logging
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from market_calendar import MarketCalendar
from simple_config import *

async def download_single_date(session, symbol, date, interval, output_dir):
    """Download options data for a single date with detailed logging."""
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
        print(f"🔍 {date}: Requesting {url}")
        print(f"📋 {date}: Params {params}")
        
        async with session.get(url, params=params) as response:
            print(f"📡 {date}: Response status {response.status}")
            
            if response.status == 200:
                content = await response.text()
                content_size = len(content) if content else 0
                print(f"📦 {date}: Content size {content_size:,} bytes")
                
                if content and content_size > 100:  # Has actual data beyond just headers
                    # Save to file
                    with open(filepath, 'w') as f:
                        f.write(content)
                    print(f"✅ {date}: Saved {filename} ({content_size:,} bytes)")
                    return True
                else:
                    print(f"⚠️  {date}: No data available (content too small)")
                    # Show first 200 chars of response for debugging
                    if content:
                        print(f"📝 {date}: Content preview: {content[:200]}...")
                    return False
            else:
                error_text = await response.text()
                print(f"❌ {date}: HTTP {response.status} - {error_text[:200]}")
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
    print(f"📅 Trading days: {trading_days}")
    print()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create session with connection limits
    connector = aiohttp.TCPConnector(limit=1)  # Single connection for debugging
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        successful_downloads = 0
        
        # Process each date sequentially for debugging
        for i, date in enumerate(trading_days):
            print(f"\n📅 Processing {date} ({i+1}/{len(trading_days)})")
            print("=" * 50)
            
            result = await download_single_date(session, symbol, date, interval, output_dir)
            if result is True:
                successful_downloads += 1
            
            print("=" * 50)
        
        # Final summary
        print(f"\n✅ Download complete! {successful_downloads} files downloaded to {output_dir}")
        
        # Check what files exist
        existing_files = list(output_dir.glob(f"{symbol}_options_*_{interval}.csv"))
        print(f"📁 Files in directory: {len(existing_files)}")
        for file in existing_files:
            size = file.stat().st_size
            print(f"   📄 {file.name} ({size:,} bytes)")

def main():
    """Main function."""
    print("🚀 Simple Debug Theta Data Downloader")
    print(f"   Symbol: {SYMBOL}")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   API Base: {BASE_URL}")
    print()
    
    # Convert to Path object
    output_path = Path(OUTPUT_DIR)
    
    # Run the download
    asyncio.run(download_date_range(
        SYMBOL, START_DATE, END_DATE, INTERVAL, output_path
    ))

if __name__ == "__main__":
    main()
