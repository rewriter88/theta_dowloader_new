#!/usr/bin/env python3
"""
Quick test of adaptive concurrency system with external SSD
"""

import asyncio
from bulk_options_downloader import ThetaBulkDownloader

async def test_adaptive_concurrency():
    """Test adaptive concurrency with a small date range."""
    print("🧪 Testing Adaptive Concurrency System")
    print("=" * 50)
    
    # Test with 3 recent trading days
    symbols = ["QQQ"]
    start_date = "2024-07-30"  # Tuesday
    end_date = "2024-08-01"    # Thursday (3 trading days)
    
    print(f"Test Configuration:")
    print(f"  Symbols: {symbols}")
    print(f"  Date Range: {start_date} to {end_date}")
    print(f"  Storage: External SSD")
    print(f"  Adaptive Concurrency: Enabled")
    print()
    
    async with ThetaBulkDownloader(
        max_concurrent=12,  # High max to let adaptive system find optimal
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        adaptive_concurrency=True
    ) as downloader:
        
        # Show initial status
        if downloader.adaptive_mode:
            status = downloader.concurrency_manager.get_status_summary()
            print(f"🧠 Initial Adaptive Status:")
            print(f"   Starting Concurrency: {status['current_concurrency']} workers")
            print(f"   Max Concurrency: {downloader.max_concurrent}")
            print()
        
        # Run download
        results = await downloader.download_multiple_symbols(
            symbols, start_date, end_date, "1m"
        )
        
        # Show final adaptive status
        if downloader.adaptive_mode:
            print(f"\n🎯 Final Adaptive Results:")
            downloader._print_adaptive_status()
        
        # Show download results
        print(f"📊 Download Results:")
        for symbol, symbol_results in results.items():
            success_count = sum(1 for success in symbol_results.values() if success)
            total_count = len(symbol_results)
            print(f"   {symbol}: {success_count}/{total_count} files successful")
        
        return results

if __name__ == "__main__":
    asyncio.run(test_adaptive_concurrency())
