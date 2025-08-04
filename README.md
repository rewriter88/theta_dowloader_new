# Theta Data Downloader

A Python application for downloading financial data from Theta Data using their Standard subscription.

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
