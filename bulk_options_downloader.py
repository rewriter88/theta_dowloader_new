"""
Theta Data Bulk Options Downloader

This module implements efficient bulk downloading of options data from Theta Data
using the Standard subscription tier with concurrent requests.

Based on the bulk download method provided by Theta Data support:
- URL: http://localhost:25503/v3/option/history/quote?symbol=SYMBOL&expiration=*&date=DATE&interval=INTERVAL
- Supports all expirations with expiration=*
- Available intervals: 1m, 5m, 15m, 30m, 1h, 4h (daily intervals not supported for options)
- Standard subscription allows 8 concurrent connections
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
from market_calendar import MarketCalendar

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
    - Respects Standard subscription limit of 8 concurrent connections
    - Bulk download using expiration=* for all option chains
    - CSV output format for efficient storage
    - Progress tracking and error handling
    - Resumable downloads with duplicate detection
    """
    
    def __init__(self, base_url: str = "http://localhost:25503", max_concurrent: int = 8, 
                 symbols: List[str] = None, start_date: str = None, end_date: str = None, output_dir: str = None):
        """
        Initialize the bulk downloader.
        
        Args:
            base_url: Theta Terminal base URL
            max_concurrent: Maximum concurrent connections (Standard = 8)
            symbols: List of symbols for organized folder structure
            start_date: Start date for organized folder structure
            end_date: End date for organized folder structure
            output_dir: Output directory for storing data (uses organized structure if None)
        """
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Initialize market calendar for holiday detection
        self.market_calendar = MarketCalendar()
        
        # Use organized directory structure
        if output_dir is None and symbols and start_date and end_date:
            from config import get_organized_output_dir
            # For single symbol, use organized structure
            if len(symbols) == 1:
                output_dir = get_organized_output_dir(symbols[0], start_date, end_date)
            else:
                # For multiple symbols, use base options directory
                from config import OUTPUT_CONFIG
                output_dir = f"{OUTPUT_CONFIG['options_base_dir']}/multi_symbol_{start_date}_to_{end_date}"
        elif output_dir is None:
            # Fallback to base options directory
            from config import OUTPUT_CONFIG
            output_dir = OUTPUT_CONFIG['options_base_dir']
        
        # Create output directory structure
        self.options_dir = Path(output_dir)
        self.options_dir.mkdir(parents=True, exist_ok=True)
        
        # Results dir for tracking files (keeping separate from data)
        self.results_dir = Path("results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Track downloaded files to avoid duplicates
        self.downloaded_files: Set[str] = set()
        self._load_download_history()
    
    def _load_download_history(self):
        """Load history of already downloaded files and validate existing files."""
        history_file = self.results_dir / "download_history.json"
        self.downloaded_files = set()
        
        # First, scan actual files on disk and validate them
        existing_files = self._scan_and_validate_existing_files()
        
        # Load history file if it exists
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    history_files = set(history.get('downloaded_files', []))
                    
                # Only keep files that both exist in history AND on disk
                self.downloaded_files = existing_files.intersection(history_files)
                
                # If there's a mismatch, update the history
                if existing_files != history_files:
                    logger.info(f"Updating download history to match existing files")
                    self._save_download_history()
                    
            except Exception as e:
                logger.warning(f"Could not load download history: {e}")
                # Fall back to just the validated existing files
                self.downloaded_files = existing_files
        else:
            # No history file, use validated existing files
            self.downloaded_files = existing_files
            if self.downloaded_files:
                self._save_download_history()
        
        logger.info(f"Resume: Found {len(self.downloaded_files)} valid previously downloaded files")
    
    def _scan_and_validate_existing_files(self) -> Set[str]:
        """Scan the output directory and validate existing files."""
        validated_files = set()
        
        if not self.options_dir.exists():
            return validated_files
            
        # Scan for CSV files matching our naming pattern
        for file_path in self.options_dir.glob("*_options_*_*.csv"):
            try:
                # Parse filename to extract components
                name_parts = file_path.stem.split("_")
                if len(name_parts) >= 4:
                    symbol = name_parts[0]
                    date = name_parts[2]  # Skip "options" part
                    interval = name_parts[3]
                    
                    # Validate file has reasonable size (more than just header)
                    if file_path.stat().st_size > 200:  # At least 200 bytes
                        # Quick validation: check if file has data rows
                        try:
                            with open(file_path, 'r') as f:
                                lines = [next(f) for _ in range(2)]  # Read first 2 lines
                                if len(lines) >= 2:  # Header + at least one data row
                                    file_key = self.generate_file_key(symbol, date, interval)
                                    validated_files.add(file_key)
                                    logger.debug(f"Validated existing file: {file_path.name}")
                                else:
                                    logger.warning(f"File too small, removing: {file_path.name}")
                                    file_path.unlink()
                        except Exception as e:
                            logger.warning(f"Invalid file, removing: {file_path.name} - {e}")
                            file_path.unlink()
                    else:
                        logger.warning(f"File too small, removing: {file_path.name}")
                        file_path.unlink()
                        
            except Exception as e:
                logger.warning(f"Error processing file {file_path}: {e}")
        
        return validated_files
    
    def get_resume_status(self, symbols: List[str], start_date: str, end_date: str, interval: str) -> Dict:
        """Get detailed resume status for the requested download job."""
        # Get trading days using market calendar
        trading_days = self.market_calendar.get_trading_days(start_date, end_date)
        
        # Show holiday filtering summary
        holiday_summary = self.market_calendar.get_holiday_summary(start_date, end_date)
        logger.info(f"📅 Market Calendar: {holiday_summary['efficiency_gain']}")
        
        # Build list of required files based on trading days only
        required_files = []
        for date_str in trading_days:
            for symbol in symbols:
                file_key = self.generate_file_key(symbol, date_str, interval)
                required_files.append({
                    'key': file_key,
                    'symbol': symbol,
                    'date': date_str,
                    'downloaded': file_key in self.downloaded_files
                })
        
        downloaded_count = sum(1 for f in required_files if f['downloaded'])
        total_count = len(required_files)
        
        return {
            'total_files': total_count,
            'downloaded_files': downloaded_count,
            'remaining_files': total_count - downloaded_count,
            'completion_percent': (downloaded_count / total_count * 100) if total_count > 0 else 0,
            'files': required_files,
            'can_resume': downloaded_count > 0 and downloaded_count < total_count
        }
    
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
            interval: Time interval (1m, 5m, 15m, 30m, 1h, 4h)
            
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
                            logger.warning(f"Downloaded file too small for {symbol} {date} - likely holiday or no trading")
                            output_file.unlink()
                            self.market_calendar.mark_no_data_date(date)
                            return False
                    
                    elif response.status == 404:
                        # No data available - could be a holiday or early market close
                        logger.warning(f"No data available for {symbol} on {date} - likely holiday or non-trading day")
                        self.market_calendar.mark_no_data_date(date)
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
                                  interval: str = "1m", progress_tracker: Optional[ProgressTracker] = None,
                                  files_to_download: Optional[List] = None) -> Dict[str, bool]:
        """
        Download options data for a symbol across a date range with resume support.
        
        Args:
            symbol: Stock symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval
            progress_tracker: Optional progress tracker for UI updates
            files_to_download: Optional list of specific files to download (for resume)
            
        Returns:
            Dict mapping date to success status
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get trading days using market calendar (avoiding holidays and weekends)
        trading_days = self.market_calendar.get_trading_days(start_date, end_date)
        
        # Filter dates if specific files are provided (for resume)
        if files_to_download is not None:
            dates_to_download = []
            for file_info in files_to_download:
                if file_info['symbol'] == symbol and file_info['date'] in trading_days:
                    dates_to_download.append(file_info['date'])
        else:
            dates_to_download = trading_days
        
        # Log at debug level only
        logger.debug(f"Downloading {symbol} options data for {len(dates_to_download)} trading days from {start_date} to {end_date}")
        
        # Create download tasks only for dates that need downloading
        tasks = []
        for date in dates_to_download:
            task = self._download_with_progress(symbol, date, interval, progress_tracker)
            tasks.append(task)
        
        # Execute downloads concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
        
        # Process results - include both downloaded and already-existing files
        date_results = {}
        download_index = 0
        
        # Process each trading day
        for date in dates_to_download:
            file_key = self.generate_file_key(symbol, date, interval)
            
            if date in dates_to_download:
                # This date was downloaded in this session
                result = results[download_index]
                download_index += 1
                
                if isinstance(result, Exception):
                    logger.error(f"Exception for {symbol} {date}: {result}")
                    date_results[date] = False
                else:
                    date_results[date] = result
            else:
                # This date was already downloaded (resume case)
                date_results[date] = file_key in self.downloaded_files
        
        # Save progress
        self._save_download_history()
        
        success_count = sum(1 for success in date_results.values() if success)
        logger.debug(f"Completed {symbol}: {success_count}/{len(dates_to_download)} days successful")
        
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
        Download options data for multiple symbols across a date range with intelligent resume.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval
            
        Returns:
            Dict mapping symbol to date results
        """
        from config import DOWNLOAD_CONFIG
        
        # Check if we should work backwards
        if DOWNLOAD_CONFIG.get('work_backwards', False):
            return await self.download_backwards_with_boundary_detection(
                symbols, start_date, end_date, interval
            )
        
        logger.info(f"Starting bulk download for {len(symbols)} symbols: {', '.join(symbols)}")
        
        # Get resume status
        resume_status = self.get_resume_status(symbols, start_date, end_date, interval)
        
        # Display resume information
        if resume_status['can_resume']:
            print(f"📂 Resume Status:")
            print(f"   Previously Downloaded: {resume_status['downloaded_files']}/{resume_status['total_files']} files")
            print(f"   Completion: {resume_status['completion_percent']:.1f}%")
            print(f"   Remaining: {resume_status['remaining_files']} files to download")
            print()
        elif resume_status['downloaded_files'] > 0:
            print(f"📂 All {resume_status['total_files']} files already downloaded - nothing to do!")
            print()
            # Return success status for all files
            all_results = {}
            for symbol in symbols:
                symbol_results = {}
                for file_info in resume_status['files']:
                    if file_info['symbol'] == symbol:
                        symbol_results[file_info['date']] = True
                all_results[symbol] = symbol_results
            return all_results
        
        # Calculate what needs to be downloaded
        files_to_download = [f for f in resume_status['files'] if not f['downloaded']]
        total_tasks = len(files_to_download)
        
        if total_tasks == 0:
            print("✅ All files already downloaded!")
            return {}
        
        # Show download plan
        trading_days = len(set(f['date'] for f in files_to_download))
        print(f"📅 Downloading {trading_days} trading days for {len(symbols)} symbol(s) - {total_tasks} total files")
        if resume_status['can_resume']:
            print(f"🔄 Resuming from {resume_status['completion_percent']:.1f}% completion")
        print()
        
        # Initialize progress tracker for remaining files
        progress_tracker = ProgressTracker(total_tasks)
        
        # Group files by symbol for organized downloading
        all_results = {}
        for symbol in symbols:
            symbol_files = [f for f in files_to_download if f['symbol'] == symbol]
            
            if not symbol_files:
                # All files for this symbol already downloaded
                symbol_results = {}
                for file_info in resume_status['files']:
                    if file_info['symbol'] == symbol:
                        symbol_results[file_info['date']] = True
                all_results[symbol] = symbol_results
                continue
            
            # Download missing files for this symbol
            symbol_dates = [f['date'] for f in symbol_files]
            min_date = min(symbol_dates)
            max_date = max(symbol_dates)
            
            symbol_results = await self.download_symbol_range(
                symbol, min_date, max_date, interval, progress_tracker, files_to_download
            )
            all_results[symbol] = symbol_results
            
            # Small delay between symbols to be respectful
            if len(symbols) > 1:
                await asyncio.sleep(1)
        
        # Ensure progress is complete
        progress_tracker.finish()
        print()
        
        self._save_download_history()
        return all_results
    
    async def download_backwards_with_boundary_detection(self, symbols: List[str], start_date: str, 
                                                       end_date: str, interval: str = "1m") -> Dict[str, Dict[str, bool]]:
        """
        Download data working backwards from end_date, stopping when we hit data boundary.
        
        Args:
            symbols: List of stock symbols
            start_date: Earliest date to try (boundary)
            end_date: Start from this date and work backwards
            interval: Time interval
            
        Returns:
            Dict mapping symbol to date results
        """
        from config import DOWNLOAD_CONFIG
        
        max_consecutive_failures = DOWNLOAD_CONFIG.get('max_consecutive_failures', 20)
        chunk_size = DOWNLOAD_CONFIG.get('chunk_size', 50)
        
        logger.info(f"Starting BACKWARDS download for {len(symbols)} symbols: {', '.join(symbols)}")
        print(f"🔄 Working backwards from {end_date} to find data coverage boundary")
        print(f"   Will stop after {max_consecutive_failures} consecutive failures")
        print(f"   Processing in chunks of {chunk_size} trading days")
        print()
        
        # Get all trading days in the range
        all_trading_days = self.market_calendar.get_trading_days(start_date, end_date)
        # Reverse to work backwards
        all_trading_days.reverse()
        
        all_results = {}
        for symbol in symbols:
            print(f"📊 Processing {symbol}...")
            symbol_results = {}
            consecutive_failures = 0
            successful_downloads = 0
            
            # Process in chunks to detect boundary faster
            for chunk_start in range(0, len(all_trading_days), chunk_size):
                chunk_end = min(chunk_start + chunk_size, len(all_trading_days))
                chunk_dates = all_trading_days[chunk_start:chunk_end]
                
                print(f"   Chunk {chunk_start//chunk_size + 1}: {chunk_dates[0]} to {chunk_dates[-1]} ({len(chunk_dates)} days)")
                
                # Download chunk
                chunk_progress = ProgressTracker(len(chunk_dates))
                chunk_failures = 0
                
                for date in chunk_dates:
                    file_key = self.generate_file_key(symbol, date, interval)
                    
                    # Skip if already downloaded
                    if file_key in self.downloaded_files:
                        symbol_results[date] = True
                        chunk_progress.update()
                        continue
                    
                    # Log what we're trying
                    print(f"   Trying {date}...")
                    
                    # Download this date
                    success = await self.download_options_data(symbol, date, interval)
                    symbol_results[date] = success
                    chunk_progress.update()
                    
                    if success:
                        successful_downloads += 1
                        consecutive_failures = 0
                        print(f"   ✓ {symbol} {date}: SUCCESS")
                    else:
                        consecutive_failures += 1
                        chunk_failures += 1
                        print(f"   ✗ {symbol} {date}: FAILED (consecutive: {consecutive_failures})")
                        
                        # Check if we should stop
                        if consecutive_failures >= max_consecutive_failures:
                            chunk_progress.finish()
                            print(f"\n🛑 Stopping {symbol}: {consecutive_failures} consecutive failures")
                            print(f"   Data boundary likely reached around {date}")
                            print(f"   Successfully downloaded {successful_downloads} files")
                            break
                    
                    # Small delay to be respectful
                    await asyncio.sleep(0.1)
                
                chunk_progress.finish()
                
                # If we hit the boundary in this chunk, stop processing this symbol
                if consecutive_failures >= max_consecutive_failures:
                    break
                
                # If the entire chunk failed, we're likely past the boundary
                if chunk_failures == len(chunk_dates):
                    consecutive_failures += chunk_failures
                    print(f"\n🛑 Entire chunk failed for {symbol}")
                    print(f"   Data boundary likely reached around {chunk_dates[-1]}")
                    print(f"   Successfully downloaded {successful_downloads} files")
                    break
                
                print(f"   Chunk complete: {chunk_failures} failures, continuing...")
                
                # Small delay between chunks
                await asyncio.sleep(1)
            
            all_results[symbol] = symbol_results
            
            print(f"✅ {symbol} complete: {successful_downloads} files downloaded")
            print(f"   Data coverage appears to start around: {self._find_earliest_success(symbol_results)}")
            print()
        
        # Save progress
        self._save_download_history()
        
        return all_results
    
    def _find_earliest_success(self, symbol_results: Dict[str, bool]) -> str:
        """Find the earliest date with successful download."""
        successful_dates = [date for date, success in symbol_results.items() if success]
        if successful_dates:
            return min(successful_dates)
        return "No successful downloads"
    
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
    
    # Calculate organized output directory
    from config import get_organized_output_dir
    if len(DOWNLOAD_CONFIG['symbols']) == 1:
        organized_dir = get_organized_output_dir(
            DOWNLOAD_CONFIG['symbols'][0], 
            DOWNLOAD_CONFIG['start_date'], 
            DOWNLOAD_CONFIG['end_date']
        )
    else:
        from config import OUTPUT_CONFIG
        date_range = f"{DOWNLOAD_CONFIG['start_date']}_to_{DOWNLOAD_CONFIG['end_date']}"
        organized_dir = f"{OUTPUT_CONFIG['options_base_dir']}/multi_symbol_{date_range}"
    
    # Display configuration
    print(f"📊 Configuration:")
    print(f"   Symbols: {', '.join(DOWNLOAD_CONFIG['symbols'])}")
    print(f"   Date Range: {DOWNLOAD_CONFIG['start_date']} to {DOWNLOAD_CONFIG['end_date']}")
    print(f"   Interval: {DOWNLOAD_CONFIG['interval']}")
    print(f"   Max Concurrent: {DOWNLOAD_CONFIG['max_concurrent']}")
    print(f"   Data Storage: {organized_dir}")
    print()
    
    try:
        # Create downloader instance with organized folder structure
        async with ThetaBulkDownloader(
            max_concurrent=DOWNLOAD_CONFIG['max_concurrent'],
            symbols=DOWNLOAD_CONFIG['symbols'],
            start_date=DOWNLOAD_CONFIG['start_date'],
            end_date=DOWNLOAD_CONFIG['end_date']
        ) as downloader:
            # Show resume status
            resume_status = downloader.get_resume_status(
                DOWNLOAD_CONFIG['symbols'],
                DOWNLOAD_CONFIG['start_date'],
                DOWNLOAD_CONFIG['end_date'],
                DOWNLOAD_CONFIG['interval']
            )
            
            if resume_status['downloaded_files'] > 0:
                print(f"📁 Found {resume_status['downloaded_files']} existing files")
                if resume_status['can_resume']:
                    print(f"   Progress: {resume_status['completion_percent']:.1f}% complete")
                    print(f"   Remaining: {resume_status['remaining_files']} files to download")
                elif resume_status['downloaded_files'] == resume_status['total_files']:
                    print(f"   Status: All files complete! ✅")
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
            print(f"✅ Download complete! Data stored in: {organized_dir}")
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
