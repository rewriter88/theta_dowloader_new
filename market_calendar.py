"""
Market Calendar Utility for Theta Data Downloader

Provides intelligent holiday detection and trading day filtering to avoid
unnecessary API calls on market holidays and weekends.
"""

import pandas as pd
import pandas_market_calendars as mcal
from datetime import datetime, timedelta
from typing import List, Set
import json
import os
import logging

logger = logging.getLogger(__name__)

class MarketCalendar:
    """
    Intelligent market calendar that filters out holidays and non-trading days.
    Uses pandas_market_calendars for accurate NYSE/NASDAQ holiday detection.
    """
    
    def __init__(self):
        # Use NYSE calendar (covers most US equity options trading)
        self.calendar = mcal.get_calendar('NYSE')
        self.cache_file = "results/market_holidays_cache.json"
        self.holiday_cache = self._load_holiday_cache()
    
    def _load_holiday_cache(self) -> dict:
        """Load cached holiday data to avoid repeated API calls."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load holiday cache: {e}")
        return {"known_holidays": [], "no_data_dates": []}
    
    def _save_holiday_cache(self):
        """Save holiday cache for future runs."""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.holiday_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save holiday cache: {e}")
    
    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """
        Get list of valid trading days between start_date and end_date.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of trading days in YYYY-MM-DD format
        """
        try:
            # Convert to pandas datetime
            start_dt = pd.Timestamp(start_date)
            end_dt = pd.Timestamp(end_date)
            
            # Get valid trading days from market calendar
            trading_schedule = self.calendar.schedule(
                start_date=start_dt,
                end_date=end_dt
            )
            
            # Extract just the dates (no times)
            trading_days = trading_schedule.index.date
            
            # Convert to string format
            trading_day_strings = [day.strftime('%Y-%m-%d') for day in trading_days]
            
            # Filter out any cached "no data" dates
            filtered_days = [
                day for day in trading_day_strings 
                if day not in self.holiday_cache.get("no_data_dates", [])
            ]
            
            logger.info(f"Found {len(filtered_days)} trading days between {start_date} and {end_date}")
            if len(trading_day_strings) - len(filtered_days) > 0:
                logger.info(f"Filtered out {len(trading_day_strings) - len(filtered_days)} known no-data dates")
            
            return filtered_days
            
        except Exception as e:
            logger.error(f"Error getting trading days: {e}")
            # Fallback: return all days and let API calls handle filtering
            return self._get_all_days_fallback(start_date, end_date)
    
    def _get_all_days_fallback(self, start_date: str, end_date: str) -> List[str]:
        """Fallback method if market calendar fails."""
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        days = []
        current = start_dt
        while current <= end_dt:
            # Skip weekends as basic filter
            if current.weekday() < 5:  # Monday=0, Friday=4
                days.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        logger.warning("Using fallback day calculation (weekends only filtered)")
        return days
    
    def mark_no_data_date(self, date: str):
        """
        Mark a date as having no data (discovered via API response).
        This prevents future attempts to download this date.
        
        Args:
            date: Date in YYYY-MM-DD format that returned no data
        """
        if date not in self.holiday_cache.get("no_data_dates", []):
            self.holiday_cache.setdefault("no_data_dates", []).append(date)
            self._save_holiday_cache()
            logger.info(f"Marked {date} as no-data date (likely holiday or early close)")
    
    def is_likely_trading_day(self, date: str) -> bool:
        """
        Quick check if a date is likely a trading day.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            True if likely a trading day, False otherwise
        """
        # Check cache first
        if date in self.holiday_cache.get("no_data_dates", []):
            return False
        
        # Check if it's a weekend
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        if date_obj.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Quick check against NYSE calendar for major holidays
        try:
            # Get single day schedule
            schedule = self.calendar.schedule(start_date=date, end_date=date)
            return len(schedule) > 0
        except:
            # Fallback to basic weekend check
            return True
    
    def get_holiday_summary(self, start_date: str, end_date: str) -> dict:
        """
        Get summary of holidays and non-trading days in date range.
        
        Returns:
            Dict with holiday analysis for the date range
        """
        all_days = self._get_all_days_fallback(start_date, end_date)
        trading_days = self.get_trading_days(start_date, end_date)
        
        total_weekdays = len([d for d in all_days])
        total_trading_days = len(trading_days)
        holidays_filtered = total_weekdays - total_trading_days
        
        return {
            "total_weekdays": total_weekdays,
            "trading_days": total_trading_days,
            "holidays_filtered": holidays_filtered,
            "efficiency_gain": f"{holidays_filtered} unnecessary API calls avoided"
        }


def test_market_calendar():
    """Test function to verify market calendar functionality."""
    print("Testing Market Calendar...")
    
    calendar = MarketCalendar()
    
    # Test with a range that includes known holidays
    start_date = "2024-12-20"  # Around Christmas/New Year
    end_date = "2025-01-03"
    
    print(f"\nTesting date range: {start_date} to {end_date}")
    
    trading_days = calendar.get_trading_days(start_date, end_date)
    print(f"Trading days found: {trading_days}")
    
    summary = calendar.get_holiday_summary(start_date, end_date)
    print(f"Holiday summary: {summary}")
    
    # Test individual date checking
    test_dates = ["2024-12-25", "2024-12-26", "2025-01-01", "2024-12-23"]
    for date in test_dates:
        is_trading = calendar.is_likely_trading_day(date)
        print(f"{date}: {'Trading day' if is_trading else 'Non-trading day'}")


if __name__ == "__main__":
    test_market_calendar()
