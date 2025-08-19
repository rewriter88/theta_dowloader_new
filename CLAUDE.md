# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Requirements

**NEVER use fake, placeholder, estimated, or synthetic data.** This system is for downloading real trading data. Only use actual data from Theta Data API calls. Display only TRUE information to the user 100% of the time.

When the user says "commit", they mean both local git commit and push to GitHub. Only do this when explicitly requested.

If any operation takes more than 15 seconds, assume something is wrong and move on or try to fix it.

## Common Commands

### Start/Stop Theta Terminal
```bash
# Start Theta Terminal with MCP support
./start_theta_terminal.sh

# Stop Theta Terminal
./stop_theta_terminal.sh
```

### Run the Simple Downloader
```bash
# Install dependencies first
pip install -r requirements.txt

# Run downloader (configure dates in simple_config.py first)
python3 simple_downloader.py
```

### Check Theta Terminal Status
```bash
# Check if running
curl -s "http://localhost:25503/" 

# Test API endpoint
curl -s "http://localhost:25503/v3/list/stocks" | head -5
```

### Python Dependencies
```bash
# Install required packages
pip install aiohttp pandas asyncio-pool pandas-market-calendars
```

## Architecture Overview

### Core Components

1. **Theta Terminal Integration** (`theta_terminal/`)
   - Runs locally on port 25503
   - Provides HTTP API for data access
   - MCP server at `/mcp/sse` endpoint
   - Requires Java 21+ and credentials in `creds.txt`

2. **Simple Downloader** (`simple_downloader.py`)
   - Main script for bulk downloading options data
   - Uses async/concurrent downloads (MAX_CONCURRENT=4)
   - Downloads to `/Volumes/SSD 4TB/Theta_Data/options/QQQ/`
   - One CSV file per trading day
   - Configuration in `simple_config.py`

3. **Market Calendar** (`market_calendar.py`)
   - Filters out weekends and market holidays
   - Uses NYSE calendar for accurate holiday detection
   - Caches holiday data to avoid repeated calculations
   - Critical for avoiding unnecessary API calls on non-trading days

4. **Configuration** (`simple_config.py`)
   - SYMBOL: Target ticker (default: "QQQ")
   - START_DATE/END_DATE: Download date range
   - INTERVAL: Data granularity (default: "1m")
   - OUTPUT_DIR: Where CSV files are saved

### Data Flow

1. Terminal starts → Connects to Theta Data servers
2. Downloader requests data → Terminal fetches from Theta Data
3. Data returned as CSV → Saved to OUTPUT_DIR
4. Progress tracked with real-time progress bar

### Key Implementation Details

- **Subscription Level**: STANDARD (options data from 2016-01-01)
- **QQQ Data Available**: From 2022-08-22 onwards
- **Concurrent Connections**: 2 (subscription limit)
- **Download Pattern**: Sequential by date, with progress tracking
- **Error Handling**: Automatic retry with exponential backoff
- **File Format**: CSV with headers, one file per trading day

### API Endpoints

Base URL: `http://localhost:25503`

Key endpoints used:
- `/v3/option/history/quote` - Historical options quotes
- `/v3/list/stocks` - List available stocks
- `/mcp/sse` - MCP server endpoint

### Important Files

- `creds.txt` - Theta Data credentials (email and password)
- `theta_terminal/config.toml` - Terminal configuration
- `results/download_history.json` - Download tracking
- `archive/logs/theta_terminal_v3.log` - Terminal logs

## Development Notes

- Always check if Theta Terminal is running before making API calls
- Market calendar filtering is essential - never request data for non-trading days
- Progress display must show real metrics, not estimates
- File existence checks prevent re-downloading existing data
- All archived code is in `archive/` directory for reference