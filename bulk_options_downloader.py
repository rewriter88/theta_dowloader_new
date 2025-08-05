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
import logging
import json
from config import DOWNLOAD_CONFIG, OUTPUT_CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('theta_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
import json
import time
import sys
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


class ProgressTracker:
    """Real-time progress tracker with ETA calculation."""
    
    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.start_time = time.time()
        self.last_update = self.start_time
        
    def update(self, increment: int = 1):
        """Update progress and display current status."""
        self.completed_tasks += increment
        current_time = time.time()
        
        # Calculate progress percentage
        progress_percent = (self.completed_tasks / self.total_tasks) * 100
        
        # Calculate ETA
        elapsed_time = current_time - self.start_time
        if self.completed_tasks > 0:
            avg_time_per_task = elapsed_time / self.completed_tasks
            remaining_tasks = self.total_tasks - self.completed_tasks
            eta_seconds = remaining_tasks * avg_time_per_task
            eta_str = self._format_time(eta_seconds)
        else:
            eta_str = "Calculating..."
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * self.completed_tasks // self.total_tasks)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Display progress (overwrite previous line)
        progress_line = f"\r📊 Progress: [{bar}] {progress_percent:.1f}% ({self.completed_tasks}/{self.total_tasks}) | ETA: {eta_str}"
        sys.stdout.write(progress_line)
        sys.stdout.flush()
        
        # Add newline when complete
        if self.completed_tasks >= self.total_tasks:
            print()  # New line after completion
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into human-readable time."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def finish(self):
        """Mark progress as complete."""
        if self.completed_tasks < self.total_tasks:
            self.completed_tasks = self.total_tasks
            self.update(0)


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
    
    def __init__(self, base_url: str = "http://localhost:25503", max_concurrent: int = 4, output_dir: str = None):
        """
        Initialize the bulk downloader.
        
        Args:
            base_url: Theta Terminal base URL
            max_concurrent: Maximum concurrent connections (Standard = 4)
            output_dir: Output directory for storing data (uses config if None)
        """
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Use output directory from config or default
        if output_dir is None:
            from config import OUTPUT_CONFIG
            output_dir = OUTPUT_CONFIG['options_dir']
        
        # Create results directory structure
        self.options_dir = Path(output_dir)
        self.options_dir.mkdir(parents=True, exist_ok=True)
        
        # Results dir for tracking files (keeping separate from data)
        self.results_dir = Path("results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
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
                # Log only at debug level to keep progress display clean
                logger.debug(f"Downloading {symbol} options data for {date} ({interval}) - URL: {url}")
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        # Stream data directly to file
                        with open(output_file, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        # Verify file has data (more than just header)
                        if output_file.stat().st_size > 100:  # At least 100 bytes
                            self.downloaded_files.add(file_key)
                            
                            # Quick stats (but don't log individual completions during bulk download)
                            with open(output_file, 'r') as f:
                                line_count = sum(1 for line in f) - 1  # Subtract header
                            
                            # Only log individual downloads in debug mode
                            logger.debug(f"✓ Downloaded {symbol} {date} ({interval}): {line_count:,} records, {output_file.stat().st_size:,} bytes")
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
                                  interval: str = "1m", progress_tracker: Optional[ProgressTracker] = None) -> Dict[str, bool]:
        """
        Download options data for a symbol across a date range.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval
            progress_tracker: Optional progress tracker for UI updates
            
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
        
        # Log at debug level only
        logger.debug(f"Downloading {symbol} options data for {len(dates)} trading days from {start_date} to {end_date}")
        
        # Create download tasks
        tasks = []
        for date in dates:
            task = self._download_with_progress(symbol, date, interval, progress_tracker)
            tasks.append(task)
        
        # Execute downloads concurrently
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
        logger.debug(f"Completed {symbol}: {success_count}/{len(dates)} days successful")
        
        return date_results
    
    async def _download_with_progress(self, symbol: str, date: str, interval: str, 
                                    progress_tracker: Optional[ProgressTracker] = None) -> bool:
        """Download with progress tracking wrapper."""
        result = await self.download_options_data(symbol, date, interval)
        
        # Update progress if tracker is provided
        if progress_tracker:
            progress_tracker.update()
        
        return result
    
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
        
        # Calculate total number of trading days for progress tracking
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:  # Only count weekdays
                total_days += 1
            current += timedelta(days=1)
        
        total_tasks = len(symbols) * total_days
        progress_tracker = ProgressTracker(total_tasks)
        
        print(f"📅 Downloading {total_days} trading days for {len(symbols)} symbol(s) - {total_tasks} total files")
        print()  # Space for progress bar
        
        all_results = {}
        for symbol in symbols:
            symbol_results = await self.download_symbol_range(
                symbol, start_date, end_date, interval, progress_tracker
            )
            all_results[symbol] = symbol_results
            
            # Small delay between symbols to be respectful
            if len(symbols) > 1:
                await asyncio.sleep(1)
        
        # Ensure progress is complete
        progress_tracker.finish()
        print()  # Space after progress completion
        
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
async def main():
    """Main function to run the bulk downloader."""
    print("=" * 60)
    print("THETA DATA BULK OPTIONS DOWNLOADER")
    print("=" * 60)
    
    # Display configuration
    print(f"📊 Configuration:")
    print(f"   Symbols: {', '.join(DOWNLOAD_CONFIG['symbols'])}")
    print(f"   Date Range: {DOWNLOAD_CONFIG['start_date']} to {DOWNLOAD_CONFIG['end_date']}")
    print(f"   Interval: {DOWNLOAD_CONFIG['interval']}")
    print(f"   Max Concurrent: {DOWNLOAD_CONFIG['max_concurrent']}")
    print(f"   Data Storage: {OUTPUT_CONFIG['options_dir']}")
    print()
    
    try:
        # Create downloader instance and use as async context manager
        async with ThetaBulkDownloader(
            max_concurrent=DOWNLOAD_CONFIG['max_concurrent'],
            output_dir=OUTPUT_CONFIG['options_dir']
        ) as downloader:
            # Show existing data summary
            summary = downloader.get_download_summary()
            
            if summary['total_files'] > 0:
                print(f"📁 Found {summary['total_files']} existing files ({summary['total_size_bytes']:,} bytes)")
                print(f"   Symbols: {', '.join(summary['symbols'])}")
                if summary['date_range']['min']:
                    print(f"   Date Range: {summary['date_range']['min']} to {summary['date_range']['max']}")
                print()
            
            # Download data
            print("🚀 Starting download...")
            
            results = await downloader.download_multiple_symbols(
                DOWNLOAD_CONFIG['symbols'], 
                DOWNLOAD_CONFIG['start_date'], 
                DOWNLOAD_CONFIG['end_date'], 
                DOWNLOAD_CONFIG['interval']
            )
            
            # Show final results
            final_summary = downloader.get_download_summary()
            print(f"✅ Download complete! Data stored in: {OUTPUT_CONFIG['options_dir']}")
            print(f"📊 Final Summary:")
            print(f"   Total Files: {final_summary['total_files']}")
            print(f"   Total Size: {final_summary['total_size_bytes']:,} bytes")
            print(f"   Symbols: {', '.join(final_summary['symbols'])}")
            if final_summary['date_range']['min']:
                print(f"   Date Range: {final_summary['date_range']['min']} to {final_summary['date_range']['max']}")
            
            return results
        
    except Exception as e:
        import traceback
        logger.error(f"Download failed: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        print(f"\n❌ Error during download: {e}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
