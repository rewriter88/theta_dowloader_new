"""
Theta Data Bulk Options Downloader

This module implements efficient bulk downloading of options data from Theta Data
using the Standard subscription tier with concurrent requests.

Based on the bulk download method provided by Theta Data support:
- URL: http://localhost:25503/v3/option/history/quote?symbol=SYMBOL&expiration=*&date=DATE&interval=INTERVAL
- Supports all expirations with expiration=*
- Available intervals: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- Standard subscription allows 4 concurrent connections
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
import csv
import os
from pathlib import Path
import json
import time
from typing import List, Dict, Optional, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ThetaBulkDownloader:
    """
    Bulk downloader for Theta Data options history using concurrent requests.
    
    Features:
    - Respects Standard subscription limit of 4 concurrent connections
    - Bulk download using expiration=* for all option chains
    - CSV output format for efficient storage
    - Progress tracking and error handling
    - Resumable downloads with duplicate detection
    """
    
    def __init__(self, base_url: str = "http://localhost:25503", max_concurrent: int = 4):
        """
        Initialize the bulk downloader.
        
        Args:
            base_url: Theta Terminal base URL
            max_concurrent: Maximum concurrent connections (Standard = 4)
        """
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create results directory structure
        self.results_dir = Path("results")
        self.options_dir = self.results_dir / "options"
        self.options_dir.mkdir(parents=True, exist_ok=True)
        
        # Track downloaded files to avoid duplicates
        self.downloaded_files: Set[str] = set()
        self._load_download_history()
    
    def _load_download_history(self):
        """Load history of already downloaded files."""
        history_file = self.results_dir / "download_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    self.downloaded_files = set(history.get('downloaded_files', []))
                logger.info(f"Loaded {len(self.downloaded_files)} previously downloaded files")
            except Exception as e:
                logger.warning(f"Could not load download history: {e}")
    
    def _save_download_history(self):
        """Save history of downloaded files."""
        history_file = self.results_dir / "download_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump({
                    'downloaded_files': list(self.downloaded_files),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save download history: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),  # 5 minute timeout
            connector=aiohttp.TCPConnector(limit=self.max_concurrent)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def generate_file_key(self, symbol: str, date: str, interval: str) -> str:
        """Generate unique key for downloaded file tracking."""
        return f"{symbol}_{date}_{interval}"
    
    def get_output_filename(self, symbol: str, date: str, interval: str) -> Path:
        """Generate output filename for the data."""
        return self.options_dir / f"{symbol}_options_{date}_{interval}.csv"
    
    async def download_options_data(self, symbol: str, date: str, interval: str = "1m") -> bool:
        """
        Download bulk options data for a specific symbol and date.
        
        Args:
            symbol: Stock symbol (e.g., "QQQ", "SPY", "AAPL")
            date: Date in YYYY-MM-DD format
            interval: Time interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            
        Returns:
            bool: True if successful, False otherwise
        """
        file_key = self.generate_file_key(symbol, date, interval)
        
        # Skip if already downloaded
        if file_key in self.downloaded_files:
            logger.info(f"Skipping {file_key} - already downloaded")
            return True
        
        # Format date for API (remove dashes)
        api_date = date.replace("-", "")
        
        # Construct URL using bulk download method
        url = f"{self.base_url}/v3/option/history/quote"
        params = {
            "symbol": symbol,
            "expiration": "*",  # All expirations - this is the key for bulk download
            "date": api_date,
            "interval": interval,
            "format": "csv"  # CSV format for efficiency
        }
        
        output_file = self.get_output_filename(symbol, date, interval)
        
        async with self.semaphore:  # Limit concurrent connections
            try:
                logger.info(f"Downloading {symbol} options data for {date} ({interval}) - URL: {url}")
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        # Stream data directly to file
                        with open(output_file, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        # Verify file has data (more than just header)
                        if output_file.stat().st_size > 100:  # At least 100 bytes
                            self.downloaded_files.add(file_key)
                            
                            # Quick stats
                            with open(output_file, 'r') as f:
                                line_count = sum(1 for line in f) - 1  # Subtract header
                            
                            logger.info(f"✓ Downloaded {symbol} {date} ({interval}): {line_count:,} records, {output_file.stat().st_size:,} bytes")
                            return True
                        else:
                            logger.warning(f"Downloaded file too small for {symbol} {date}, removing")
                            output_file.unlink()
                            return False
                    
                    elif response.status == 404:
                        logger.warning(f"No data available for {symbol} on {date}")
                        return False
                    else:
                        logger.error(f"HTTP {response.status} for {symbol} {date}: {await response.text()}")
                        return False
                        
            except Exception as e:
                logger.error(f"Error downloading {symbol} {date}: {e}")
                if output_file.exists():
                    output_file.unlink()
                return False
    
    async def download_symbol_range(self, symbol: str, start_date: str, end_date: str, 
                                  interval: str = "1m") -> Dict[str, bool]:
        """
        Download options data for a symbol across a date range.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval
            
        Returns:
            Dict mapping date to success status
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        while current <= end:
            # Only include weekdays (skip weekends)
            if current.weekday() < 5:
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        logger.info(f"Downloading {symbol} options data for {len(dates)} trading days from {start_date} to {end_date}")
        
        # Download dates concurrently
        tasks = [self.download_options_data(symbol, date, interval) for date in dates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        date_results = {}
        for date, result in zip(dates, results):
            if isinstance(result, Exception):
                logger.error(f"Exception for {symbol} {date}: {result}")
                date_results[date] = False
            else:
                date_results[date] = result
        
        # Save progress
        self._save_download_history()
        
        success_count = sum(1 for success in date_results.values() if success)
        logger.info(f"Completed {symbol}: {success_count}/{len(dates)} days successful")
        
        return date_results
    
    async def download_multiple_symbols(self, symbols: List[str], start_date: str, 
                                      end_date: str, interval: str = "1m") -> Dict[str, Dict[str, bool]]:
        """
        Download options data for multiple symbols across a date range.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval
            
        Returns:
            Dict mapping symbol to date results
        """
        logger.info(f"Starting bulk download for {len(symbols)} symbols: {', '.join(symbols)}")
        
        all_results = {}
        for symbol in symbols:
            logger.info(f"Processing symbol {symbol}...")
            all_results[symbol] = await self.download_symbol_range(symbol, start_date, end_date, interval)
            
            # Small delay between symbols to be respectful
            await asyncio.sleep(1)
        
        self._save_download_history()
        return all_results
    
    def get_download_summary(self) -> Dict:
        """Get summary of downloaded data."""
        summary = {
            "total_files": len(self.downloaded_files),
            "total_size_bytes": 0,
            "symbols": set(),
            "date_range": {"min": None, "max": None},
            "files": []
        }
        
        for file_path in self.options_dir.glob("*.csv"):
            if file_path.exists():
                size = file_path.stat().st_size
                summary["total_size_bytes"] += size
                
                # Parse filename to extract info
                name_parts = file_path.stem.split("_")
                if len(name_parts) >= 4:
                    symbol = name_parts[0]
                    date = name_parts[2]
                    interval = name_parts[3]
                    
                    summary["symbols"].add(symbol)
                    
                    if summary["date_range"]["min"] is None or date < summary["date_range"]["min"]:
                        summary["date_range"]["min"] = date
                    if summary["date_range"]["max"] is None or date > summary["date_range"]["max"]:
                        summary["date_range"]["max"] = date
                    
                    summary["files"].append({
                        "symbol": symbol,
                        "date": date,
                        "interval": interval,
                        "size_bytes": size,
                        "file": str(file_path)
                    })
        
        summary["symbols"] = list(summary["symbols"])
        summary["total_size_mb"] = round(summary["total_size_bytes"] / (1024 * 1024), 2)
        
        return summary


async def main():
    """Example usage of the bulk downloader."""
    
    # Popular symbols for options trading
    symbols = ["QQQ", "SPY", "AAPL", "TSLA", "NVDA"]
    
    # Date range - last 5 trading days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    async with ThetaBulkDownloader() as downloader:
        # Download 1-minute options data for all symbols
        results = await downloader.download_multiple_symbols(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval="1m"
        )
        
        # Print results summary
        print("\n" + "="*60)
        print("DOWNLOAD RESULTS SUMMARY")
        print("="*60)
        
        for symbol, date_results in results.items():
            success_count = sum(1 for success in date_results.values() if success)
            total_count = len(date_results)
            print(f"{symbol}: {success_count}/{total_count} days successful")
        
        # Get overall summary
        summary = downloader.get_download_summary()
        print(f"\nTotal files downloaded: {summary['total_files']}")
        print(f"Total data size: {summary['total_size_mb']} MB")
        print(f"Symbols: {', '.join(summary['symbols'])}")
        print(f"Date range: {summary['date_range']['min']} to {summary['date_range']['max']}")


if __name__ == "__main__":
    asyncio.run(main())
