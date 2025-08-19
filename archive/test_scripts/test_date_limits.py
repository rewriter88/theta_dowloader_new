#!/usr/bin/env python3
"""
Test script to find the earliest available QQQ options data from Theta Data
"""

import asyncio
import aiohttp
from datetime import datetime

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
                # Check if we have actual data (not just headers)
                if content and len(content) > 500:  # More than just CSV headers
                    lines = content.strip().split('\n')
                    return True, len(lines) - 1  # Subtract header line
                else:
                    return False, 0
            else:
                return False, 0
    except Exception as e:
        print(f"Error testing {date_str}: {e}")
        return False, 0

async def find_earliest_date():
    """Find the earliest available date for QQQ options."""
    test_dates = [
        # Start with recent known working date
        "2017-08-08",  # We know this works
        
        # Test 2016 (your subscription supposedly goes back to 2016)
        "2016-12-30",
        "2016-07-01", 
        "2016-01-04",  # First trading day of 2016
        
        # Test 2015
        "2015-12-31",
        "2015-07-01",
        "2015-01-02",  # First trading day of 2015
        
        # Test 2014
        "2014-12-31",
        "2014-07-01",
        "2014-01-02",  # First trading day of 2014
        
        # Test 2013
        "2013-12-31",
        "2013-07-01",
        "2013-01-02",  # First trading day of 2013
        
        # Test 2012
        "2012-12-31",
        "2012-01-03",  # First trading day of 2012
        
        # Test 2011
        "2011-12-30",
        "2011-01-03",  # First trading day of 2011
        
        # Test 2010
        "2010-12-31",
        "2010-01-04",  # First trading day of 2010
    ]
    
    print("🔍 Testing Theta Data date limits for QQQ options...")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        for date_str in test_dates:
            has_data, line_count = await test_date(session, date_str)
            
            if has_data:
                print(f"✅ {date_str}: Data available ({line_count:,} records)")
                results.append((date_str, True, line_count))
            else:
                print(f"❌ {date_str}: No data available")
                results.append((date_str, False, 0))
            
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    
    # Find earliest date with data
    dates_with_data = [r for r in results if r[1]]
    if dates_with_data:
        dates_with_data.sort(key=lambda x: x[0])
        earliest = dates_with_data[0]
        latest = dates_with_data[-1]
        
        print(f"✅ Earliest available date: {earliest[0]} ({earliest[2]:,} records)")
        print(f"✅ Latest tested date: {latest[0]} ({latest[2]:,} records)")
        print(f"📈 Total dates with data: {len(dates_with_data)}")
        
        return earliest[0]
    else:
        print("❌ No data found for any tested dates")
        return None

async def test_year_range(start_year, end_year):
    """Test a specific year range more thoroughly."""
    print(f"\n🔬 Testing year range {start_year} to {end_year} in detail...")
    print("=" * 60)
    
    test_dates = []
    for year in range(start_year, end_year + 1):
        # Test first trading day of each month
        for month in [1, 4, 7, 10]:  # Quarterly
            if month == 1:
                day = 3 if year <= 2011 else 2  # Account for holidays
            else:
                day = 1
            test_dates.append(f"{year:04d}-{month:02d}-{day:02d}")
    
    async with aiohttp.ClientSession() as session:
        for date_str in test_dates:
            has_data, line_count = await test_date(session, date_str)
            
            if has_data:
                print(f"✅ {date_str}: Data available ({line_count:,} records)")
            else:
                print(f"❌ {date_str}: No data available")
            
            await asyncio.sleep(0.3)

if __name__ == "__main__":
    print("🚀 Theta Data Historical Limit Finder")
    print()
    
    # First, find the rough earliest date
    earliest = asyncio.run(find_earliest_date())
    
    if earliest:
        # If we found an early date, test that year more thoroughly
        year = int(earliest.split('-')[0])
        asyncio.run(test_year_range(year - 1, year + 1))