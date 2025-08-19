# Theta Data Options Downloader Instructions
**Date: August 19, 2025**

## Overview
This document describes the process for downloading historical options data from Theta Data using the simple downloader system.

## Prerequisites
1. **Theta Terminal v3** must be running on port 25503
   - Start: `./start_theta_terminal.sh`
   - Stop: `./stop_theta_terminal.sh`
2. Valid Theta Data subscription with historical options access
3. Sufficient disk space (1m interval data can be 200+ MB per day for liquid symbols)

## Programs Used
- **Primary Downloader**: `simple_downloader.py`
- **Configuration**: `simple_config.py`
- **Multi-Symbol Batch**: `multi_symbol_downloader.py`
- **Market Calendar**: `market_calendar.py` (for trading day validation)

## Download Process for a Single Symbol

### Step 1: Configure the Download
Edit `simple_config.py`:

```python
# Download settings
SYMBOL = "SPY"                      # Symbol to download
START_DATE = "2012-09-04"           # Earliest available options data
END_DATE = "2025-08-19"             # End date (use today's date)
INTERVAL = "1m"                     # Options: "1m" or "5m"

# API settings
BASE_URL = "http://localhost:25503"
MAX_CONCURRENT = 4                  # Max concurrent downloads (respect API limits)

# Output settings
OUTPUT_DIR = "/Volumes/SSD 4TB/Theta_Data/options/SPY_1m/2012-09-04_to_2025-08-19"
```

### Step 2: Run the Downloader
```bash
cd "/Users/ricardoellstein/code/theta_downloader_new copy 2"
python3 simple_downloader.py
```

### Step 3: Monitor Progress
The downloader displays:
- Progress bar with percentage complete
- Download rate (files/second)
- ETA for completion
- Real-time status updates

Example output:
```
🚀 Simple Theta Data Downloader
   Symbol: SPY
   Date Range: 2012-09-04 to 2025-08-19
   Output: /Volumes/SSD 4TB/Theta_Data/options/SPY_1m/2012-09-04_to_2025-08-19

🎯 SPY: 2012-09-04 to 2025-08-19 (3258 trading days)
📈 [████░░░░░░░░░░░░░░░░] 20.0% (651/3258) | 0.5 files/s | ETA: 1.4h | 🔄 DOWNLOADING
```

## Batch Download Multiple Symbols
Use `multi_symbol_downloader.py` to download multiple symbols sequentially:

1. Edit the SYMBOLS list in the script:
```python
SYMBOLS = [
    "SPY",     # S&P 500 ETF
    "IWM",     # Russell 2000 ETF  
    "NVDA",    # Nvidia
    "MSFT",    # Microsoft
    # ... add more symbols
]
```

2. Run the batch downloader:
```bash
python3 multi_symbol_downloader.py
```

## Output Format
- **File naming**: `{SYMBOL}_options_{YYYY-MM-DD}_{INTERVAL}.csv`
- **Example**: `SPY_options_2025-08-19_1m.csv`
- **Location**: Organized by symbol and date range in specified output directory

## Data Specifications
- **Earliest available data**: September 4, 2012 (for most liquid symbols)
- **Intervals available**: 1-minute (1m) or 5-minute (5m)
- **File sizes**: 
  - 2012 data: ~40-90 MB per day (1m interval)
  - 2025 data: ~200-400 MB per day (1m interval)
- **API endpoint**: `http://localhost:25503/v3/option/history/quote`

## Important Notes
1. **Trading days only**: The downloader automatically skips weekends and market holidays
2. **HTTP 472 errors**: Normal for market closure days (e.g., 9/11 memorial)
3. **Resume capability**: Files already downloaded are automatically skipped
4. **Concurrent limit**: Keep MAX_CONCURRENT at 4 to respect API limits
5. **Disk space**: Plan for ~500GB+ for complete history of liquid symbols at 1m intervals

## Troubleshooting
- **No data returned**: Check if Theta Terminal is running (`curl http://localhost:25503/v3/option/history/quote?symbol=SPY&expiration=*&date=20250819&interval=1m`)
- **Slow downloads**: Reduce MAX_CONCURRENT in config
- **Missing dates**: Some symbols may have limited historical data availability

## Example Complete Download Session
```bash
# 1. Start Theta Terminal
./start_theta_terminal.sh

# 2. Configure for QQQ
vi simple_config.py
# Set SYMBOL="QQQ", dates, and output path

# 3. Run download
python3 simple_downloader.py

# 4. Monitor until complete
# Downloads ~3,258 files over 1-2 hours

# 5. Verify data
ls -la /Volumes/SSD\ 4TB/Theta_Data/options/QQQ_1m/*/
```

## Tested Symbols
Successfully downloaded 1-minute interval data (2012-09-04 to 2025-08-19):
- SPY, IWM (ETFs)
- NVDA, MSFT, AAPL, AMZN, GOOGL, META, AVGO, TSLA (Tech giants)
- NFLX, COST (Consumer stocks)
- ASML (Semiconductor equipment - 11th largest Nasdaq 100)
- ETHA (ETH ETF for crypto exposure)

## Support
For issues with the downloader, check:
1. Theta Terminal logs
2. Network connectivity to localhost:25503
3. Available disk space
4. Valid subscription status