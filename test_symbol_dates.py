#!/usr/bin/env python3
"""
Test earliest available dates for various symbols
"""

import asyncio
import aiohttp
from datetime import datetime

BASE_URL = "http://localhost:25503"

async def test_date(session, symbol, date_str):
    """Test if data is available for a specific symbol and date."""
    api_date = date_str.replace("-", "")
    url = f"{BASE_URL}/v3/option/history/quote"
    params = {
        'symbol': symbol,
        'expiration': '*',
        'date': api_date,
        'interval': '1m'
    }
    
    try:
        async with session.get(url, params=params, timeout=30) as response:
            if response.status == 200:
                content = await response.text()
                if content and len(content) > 500:
                    lines = content.strip().split('\n')
                    return True, len(lines) - 1
                else:
                    return False, 0
            else:
                return False, 0
    except Exception as e:
        return False, 0

async def find_earliest_for_symbol(symbol):
    """Find earliest available date for a symbol."""
    test_dates = [
        "2010-01-04",  # 2010
        "2011-01-03",  # 2011
        "2012-01-03",  # 2012
        "2012-09-04",  # Known QQQ start
        "2013-01-02",  # 2013
        "2014-01-02",  # 2014
        "2015-01-02",  # 2015
        "2016-01-04",  # 2016
        "2017-01-03",  # 2017
    ]
    
    print(f"\n🔍 Testing {symbol}...")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        earliest = None
        for date_str in test_dates:
            has_data, line_count = await test_date(session, symbol, date_str)
            
            if has_data:
                print(f"✅ {date_str}: Data available ({line_count:,} records)")
                if not earliest:
                    earliest = date_str
            else:
                print(f"❌ {date_str}: No data")
            
            await asyncio.sleep(0.3)
        
        if earliest:
            print(f"📊 Earliest date for {symbol}: {earliest}")
            return earliest
        else:
            print(f"❌ No data found for {symbol}")
            return None

async def main():
    """Test multiple symbols."""
    symbols = ["SPY", "IWM", "VYM", "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "ETH", "ETHA", "BITO"]
    
    print("🚀 Testing Symbol Date Availability")
    print("=" * 50)
    
    results = {}
    for symbol in symbols:
        earliest = await find_earliest_for_symbol(symbol)
        results[symbol] = earliest
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    for symbol, date in results.items():
        if date:
            print(f"✅ {symbol}: {date}")
        else:
            print(f"❌ {symbol}: No data available")

if __name__ == "__main__":
    asyncio.run(main())