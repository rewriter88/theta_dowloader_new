#!/usr/bin/env python3
"""
Multi-Symbol Options Downloader
Downloads options data for multiple symbols sequentially
"""

import asyncio
import subprocess
import time
from pathlib import Path
from simple_config import BASE_URL, MAX_CONCURRENT
from simple_downloader import download_date_range

# List of symbols to download
SYMBOLS = [
    "SPY",     # S&P 500 ETF (currently running)
    "IWM",     # Russell 2000 ETF  
    "NVDA",    # Nvidia
    "MSFT",    # Microsoft
    "AAPL",    # Apple
    "AMZN",    # Amazon
    "GOOGL",   # Alphabet Class A
    "META",    # Meta Platforms
    "AVGO",    # Broadcom
    "TSLA",    # Tesla
    "NFLX",    # Netflix
    "COST",    # Costco
    "ETHA",    # ETH ETF (crypto exposure)
]

# Common settings
START_DATE = "2012-09-04"  # Earliest available
END_DATE = "2025-08-19"    # Today
INTERVAL = "1m"
BASE_OUTPUT_DIR = "/Volumes/SSD 4TB/Theta_Data/options"

async def download_symbol(symbol):
    """Download options data for a single symbol."""
    print(f"\n{'='*70}")
    print(f"🚀 Starting download for {symbol}")
    print(f"{'='*70}\n")
    
    # Create output directory
    output_dir = Path(BASE_OUTPUT_DIR) / f"{symbol}_1m" / f"{START_DATE}_to_{END_DATE}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if already complete by looking for recent files
    existing_files = list(output_dir.glob(f"{symbol}_options_*.csv"))
    if existing_files:
        print(f"📂 Found {len(existing_files)} existing files in {output_dir}")
        # Check if we have a recent file (within last 7 days)
        recent_dates = ["2025-08-19", "2025-08-16", "2025-08-15", "2025-08-14", "2025-08-13", "2025-08-12", "2025-08-09"]
        has_recent = any(output_dir / f"{symbol}_options_{date}_{INTERVAL}.csv" for date in recent_dates if (output_dir / f"{symbol}_options_{date}_{INTERVAL}.csv").exists())
        if has_recent:
            print(f"✅ {symbol} appears to be complete (has recent files)")
            return True
    
    try:
        # Download the data
        await download_date_range(symbol, START_DATE, END_DATE, INTERVAL, output_dir)
        print(f"✅ {symbol} download complete!")
        return True
    except Exception as e:
        print(f"❌ Error downloading {symbol}: {e}")
        return False

async def main():
    """Download all symbols sequentially."""
    print("🎯 Multi-Symbol Options Downloader")
    print(f"   Symbols: {', '.join(SYMBOLS)}")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Interval: {INTERVAL}")
    print(f"   Output Base: {BASE_OUTPUT_DIR}")
    print()
    
    results = {}
    
    # Skip SPY if it's already running
    start_idx = 0
    if SYMBOLS[0] == "SPY":
        print("⏭️  Skipping SPY (already running in separate process)")
        start_idx = 1
    
    # Download each symbol
    for symbol in SYMBOLS[start_idx:]:
        success = await download_symbol(symbol)
        results[symbol] = success
        
        if success:
            print(f"✅ {symbol}: Successfully downloaded")
        else:
            print(f"❌ {symbol}: Failed to download")
        
        # Brief pause between symbols
        if symbol != SYMBOLS[-1]:
            print(f"\n⏰ Waiting 5 seconds before next symbol...")
            await asyncio.sleep(5)
    
    # Print summary
    print(f"\n{'='*70}")
    print("📊 DOWNLOAD SUMMARY")
    print(f"{'='*70}")
    
    successful = [s for s, r in results.items() if r]
    failed = [s for s, r in results.items() if not r]
    
    if successful:
        print(f"✅ Successful ({len(successful)}): {', '.join(successful)}")
    if failed:
        print(f"❌ Failed ({len(failed)}): {', '.join(failed)}")
    
    print(f"\nTotal: {len(successful)}/{len(results)} symbols downloaded successfully")

if __name__ == "__main__":
    asyncio.run(main())