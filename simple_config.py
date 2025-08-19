"""
Simple Configuration for Bare-Bones Theta Data Downloader
"""

# Download settings
SYMBOL = "SPY"
START_DATE = "2012-09-04"  # Earliest available options data
END_DATE = "2025-08-19"    # Latest date to download (today)
INTERVAL = "1m"            # 1-minute interval for maximum resolution

# API settings
BASE_URL = "http://localhost:25503"
MAX_CONCURRENT = 4

# Output settings
OUTPUT_DIR = "/Volumes/SSD 4TB/Theta_Data/options/SPY_1m/2012-09-04_to_2025-08-19"
