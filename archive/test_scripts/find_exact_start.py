#!/usr/bin/env python3
"""
Find the exact earliest date for QQQ options data
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta

BASE_URL = "http://localhost:25503"

async def test_date(session, date_str):
    """Test if data is available for a specific date."""
    api_date = date_str.replace("-", "")
    url = f"{BASE_URL}/v3/option/history/quote"
    params = {
        'symbol': 'QQQ',
        'expiration': '*',
        'date': api_date,
        'interval': '5m'
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

async def find_exact_start():
    """Binary search to find exact start date between Sept and Oct 2012."""
    print("🔍 Finding exact earliest date for QQQ options...")
    print("=" * 60)
    
    # Test September and early October 2012
    test_dates = []
    
    # September 2012
    for day in range(1, 31):
        date = datetime(2012, 9, day)
        if date.weekday() < 5:  # Weekdays only
            test_dates.append(date.strftime("%Y-%m-%d"))
    
    # October 2012 
    for day in range(1, 15):
        date = datetime(2012, 10, day)
        if date.weekday() < 5:  # Weekdays only
            test_dates.append(date.strftime("%Y-%m-%d"))
    
    async with aiohttp.ClientSession() as session:
        first_available = None
        
        for date_str in test_dates:
            has_data, line_count = await test_date(session, date_str)
            
            if has_data:
                print(f"✅ {date_str}: Data available ({line_count:,} records)")
                if not first_available:
                    first_available = date_str
            else:
                print(f"❌ {date_str}: No data available")
            
            await asyncio.sleep(0.2)
    
    print("\n" + "=" * 60)
    if first_available:
        print(f"🎯 EARLIEST AVAILABLE DATE: {first_available}")
        return first_available
    else:
        print("❌ No data found in tested range")
        return None

if __name__ == "__main__":
    earliest = asyncio.run(find_exact_start())