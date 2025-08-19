# Theta Data Downloader & MCP Server

A clean, organized project for downloading Theta Data options and accessing it via Model Context Protocol (MCP).

## Project Structure

```
theta_downloader_new/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── creds.txt                    # Theta Data credentials
├── creds.txt.template          # Credentials template
├── start_theta_terminal.sh      # Start Theta Terminal with MCP
├── simple_downloader.py         # Main downloader script
├── simple_config.py            # Downloader configuration
├── config.py                   # Legacy config
├── market_calendar.py          # Trading day utilities
├── theta_terminal/             # Theta Terminal v3 with MCP
│   ├── ThetaTerminalv3.jar     # Latest Theta Terminal
│   ├── config.toml             # Terminal configuration
│   └── creds.txt               # Terminal credentials
├── archive/                    # Archived files
│   ├── old_downloaders/        # Previous downloader versions
│   ├── test_scripts/           # All test scripts
│   ├── logs/                   # Log files
│   └── theta_terminal_old/     # Old terminal versions
├── documents/                  # Documentation
├── results/                    # Download results
└── lib/                        # Library files
```

## Quick Start

### 1. Start Theta Terminal with MCP Support
```bash
./start_theta_terminal.sh
```

### 2. Set up Claude CLI (if not already done)
```bash
npm install -g @anthropic-ai/claude-code
claude mcp add --transport sse ThetaData http://localhost:25503/mcp/sse
```

### 3. Use Natural Language Queries
```bash
claude "Get the latest options data for QQQ"
claude "Download historical data for AAPL options from last week"
```

### 4. Or Use the Simple Downloader
```bash
# Edit simple_config.py for your settings
python3 simple_downloader.py
```

## Features

- ✅ **MCP Integration**: Natural language queries to Theta Data
- ✅ **Simple Downloader**: Clean, reliable options data downloader  
- ✅ **Trading Day Validation**: Automatic market calendar checking
- ✅ **Clean Organization**: All legacy code archived properly
- ✅ **Theta Terminal v3**: Latest version with full API support

## Theta Data Subscription

Current subscription: **STANDARD**
- Options data back to 2016-01-01 (theoretical)
- QQQ options available from 2022-08-22 (actual)
- 2 concurrent connections
- Real-time data access

## Setup

### Prerequisites
- Java 21 or higher
- Python 3.8+
- Theta Data Standard subscription

### Installation

1. Clone this repository
2. Install Java 21 if not already installed
3. Download Theta Terminal:
   ```bash
   cd ThetaTerminal
   curl -O https://download-unstable.thetadata.us/ThetaTerminalv3.jar
   ```
4. Create credentials file:
   ```bash
   echo "your-email@example.com" > creds.txt
   echo "your-password" >> creds.txt
   ```
5. Start Theta Terminal:
   ```bash
   java -jar ThetaTerminal/ThetaTerminalv3.jar
   ```

## Usage

The Theta Terminal runs a local HTTP server on `http://localhost:25503` that provides access to:
- Options data (Standard subscription - tick level from 2016)
- Stock data (Free tier - EOD data)
- Real-time market data

## API Access

With Standard subscription, you have access to:
- Historical options data from 2016-01-01
- Tick-level resolution
- Real-time options feeds
- 2 concurrent connections

## Project Structure

```
theta_downloader_new/
├── ThetaTerminal/          # Theta Terminal installation
│   ├── ThetaTerminalv3.jar # Theta Terminal application
│   └── config.toml         # Configuration (auto-generated)
├── creds.txt              # Credentials file (not in git)
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Security

- Credentials are stored in `creds.txt` and excluded from git
- The Theta Terminal JAR file is excluded from git (download separately)

## Documentation

- [Theta Data API Documentation](https://docs.thetadata.us/)
- [Getting Started Guide](https://docs.thetadata.us/Articles/Getting-Started/Getting-Started.html)
