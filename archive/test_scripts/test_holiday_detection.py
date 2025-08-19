#!/usr/bin/env python3
"""
Test script to demonstrate Theta Data bulk downloader with intelligent holiday detection.

This script shows how the market calendar prevents unnecessary API calls on holidays
and weekends, making downloads more efficient.
"""

from bulk_options_downloader import ThetaBulkDownloader
from market_calendar import MarketCalendar
import asyncio

async def test_holiday_detection():
    """Demonstrate holiday detection capabilities."""
    
    print("🗓️  Testing Market Calendar Holiday Detection")
    print("=" * 50)
    
    # Test date range around Christmas/New Year holidays
    start_date = "2024-12-20"
    end_date = "2025-01-03"
    
    # Initialize market calendar
    calendar = MarketCalendar()
    
    # Show all days in range vs trading days
    print(f"📅 Date Range: {start_date} to {end_date}")
    
    # Get trading days
    trading_days = calendar.get_trading_days(start_date, end_date)
    print(f"\n✅ Trading Days Identified ({len(trading_days)}):")
    for day in trading_days:
        print(f"   {day}")
    
    # Show what was filtered out
    from datetime import datetime, timedelta
    all_weekdays = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    while current <= end:
        if current.weekday() < 5:  # Weekdays only
            all_weekdays.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    filtered_days = [day for day in all_weekdays if day not in trading_days]
    if filtered_days:
        print(f"\n❌ Holidays/Non-Trading Days Filtered ({len(filtered_days)}):")
        for day in filtered_days:
            print(f"   {day}")
    
    # Show efficiency gain
    holiday_summary = calendar.get_holiday_summary(start_date, end_date)
    print(f"\n💡 Efficiency Gain:")
    print(f"   Total weekdays: {holiday_summary['total_weekdays']}")
    print(f"   Trading days: {holiday_summary['trading_days']}")
    print(f"   API calls avoided: {holiday_summary['holidays_filtered']}")
    
    # Test with bulk downloader
    print(f"\n🚀 Testing Bulk Downloader Integration")
    print("-" * 40)
    
    downloader = ThetaBulkDownloader(
        symbols=['QQQ'], 
        start_date=start_date, 
        end_date=end_date
    )
    
    # Get resume status to see holiday filtering in action
    status = downloader.get_resume_status(['QQQ'], start_date, end_date, '1m')
    
    print(f"   Files to download: {status['total_files']} (instead of {len(all_weekdays)} without holiday filtering)")
    print(f"   Completion: {status['completion_percent']:.1f}%")
    
    if status['remaining_files'] > 0:
        print(f"   Ready to download {status['remaining_files']} files efficiently!")
    else:
        print(f"   All files already downloaded!")

if __name__ == "__main__":
    asyncio.run(test_holiday_detection())
