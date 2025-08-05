#!/usr/bin/env python3
"""
Simple test script to demonstrate where data is stored and download a small sample.
"""

import asyncio
from bulk_options_downloader import ThetaBulkDownloader
from datetime import datetime, timedelta

async def test_download():
    """Test downloading a single day of data for QQQ to show where files are stored."""
    
    print("=" * 60)
    print("THETA DATA BULK DOWNLOADER TEST")
    print("=" * 60)
    
    # Test with just QQQ for one recent trading day
    symbol = "QQQ"
    test_date = "2024-11-04"  # A recent trading day we know has data
    
    print(f"Testing download for {symbol} on {test_date}")
    print(f"Data will be stored in: results/options/")
    print(f"Filename format: {symbol}_options_{test_date}_1m.csv")
    print(f"Full path: results/options/{symbol}_options_{test_date}_1m.csv")
    print()
    
    async with ThetaBulkDownloader() as downloader:
        # Show where files will be created
        print(f"Results directory: {downloader.results_dir}")
        print(f"Options directory: {downloader.options_dir}")
        print(f"Max concurrent connections: {downloader.max_concurrent}")
        print()
        
        # Download single day of data
        print(f"Starting download of {symbol} for {test_date}...")
        success = await downloader.download_options_data(symbol, test_date, "1m")
        
        if success:
            print(f"✅ Successfully downloaded {symbol} data!")
            
            # Show file info
            output_file = downloader.get_output_filename(symbol, test_date, "1m")
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                print(f"📁 File location: {output_file}")
                print(f"📊 File size: {size_mb:.2f} MB")
                
                # Count lines
                with open(output_file, 'r') as f:
                    line_count = sum(1 for line in f) - 1  # Subtract header
                print(f"📈 Records: {line_count:,}")
                
                # Show first few lines
                print(f"\n📋 First 3 data rows:")
                with open(output_file, 'r') as f:
                    lines = f.readlines()
                    print(lines[0].strip())  # Header
                    for i in range(1, min(4, len(lines))):
                        print(lines[i].strip())
            else:
                print("❌ File was not created")
        else:
            print(f"❌ Failed to download {symbol} data")
        
        # Show summary
        summary = downloader.get_download_summary()
        print(f"\n📊 DOWNLOAD SUMMARY:")
        print(f"Total files: {summary['total_files']}")
        print(f"Total size: {summary['total_size_mb']} MB")

if __name__ == "__main__":
    asyncio.run(test_download())
