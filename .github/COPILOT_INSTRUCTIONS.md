# GitHub Copilot Instructions for Theta Data Downloader

## Project Overview
This is a Python application for downloading financial data from Theta Data using their Standard subscription. The project integrates with Theta Terminal, which runs a local HTTP server providing access to market data.

## Current Setup Status ✅
- **Theta Terminal**: Running on `http://localhost:25503`
- **Subscription**: Options STANDARD, Stock FREE, Index FREE
- **Authentication**: Configured via `creds.txt` (excluded from git)
- **Java Version**: 21.0.7 (required for Theta Terminal)

## Key Project Information

### Architecture
- **Theta Terminal**: Java application that must run locally to access data
- **API Access**: REST API endpoints via local HTTP server
- **Data Types**: Historical and real-time options data (primary), limited stock data
- **Subscription Level**: STANDARD - tick-level options data from 2016, 2 concurrent connections

### File Structure
```
theta_downloader_new/
├── .github/                    # GitHub configuration
│   └── COPILOT_INSTRUCTIONS.md # This file
├── .gitignore                  # Excludes credentials and JAR files
├── README.md                   # Project documentation
├── creds.txt.template          # Template for credentials
├── creds.txt                   # Real credentials (NEVER commit)
└── ThetaTerminal/              # Theta Terminal installation
    ├── ThetaTerminalv3.jar     # Terminal application (excluded from git)
    └── config.toml             # Auto-generated config
```

### Security & Credentials
- **CRITICAL**: `creds.txt` contains real credentials and is excluded from git
- **Template**: Use `creds.txt.template` for setup instructions
- **JAR File**: Theta Terminal JAR is excluded from git (users download separately)

### Development Guidelines

#### When Building the Python Application:
1. **API Base URL**: Always use `http://localhost:25503/v3/`
2. **Data Formats**: Support CSV, JSON, and NDJSON formats
3. **Error Handling**: Implement comprehensive error handling for all Theta Data error codes
4. **Rate Limiting**: Respect subscription limits (2 concurrent connections for STANDARD)
5. **Dependencies**: Use `requests` for HTTP calls, `pandas` for data handling

#### Key API Endpoints to Implement:
- `/v3/stock/list/symbols` - Get all stock symbols
- `/v3/option/list/expirations` - Get option expiration dates
- `/v3/option/ohlc` - Historical options OHLC data
- `/v3/option/trade` - Historical options trades
- `/v3/option/quote` - Historical options quotes

#### Error Codes to Handle:
- 200: Success
- 429: Rate limit (OS throttling)
- 471: Permission denied
- 472: No data found
- 474: Disconnected from Theta Data
- 570: Request too large

### Python Environment Setup
```bash
# Recommended virtual environment setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install requests pandas numpy
```

### Testing Strategy
- **Unit Tests**: Test API response parsing
- **Integration Tests**: Test with live Theta Terminal
- **Mock Tests**: Use mock responses for offline testing
- **Validation**: Verify data integrity and completeness

### Deployment Considerations
- **Theta Terminal**: Must be running before any data requests
- **Credentials**: Users must set up their own `creds.txt`
- **Java Requirement**: Users must have Java 21+ installed
- **Network**: Local-only access (no external API calls)

### Future Development Priorities
1. **Core Data Downloader**: Options data download with date ranges
2. **Data Storage**: Efficient storage format (Parquet/CSV)
3. **Scheduling**: Automated data collection
4. **Monitoring**: Health checks for Theta Terminal
5. **UI/CLI**: User-friendly interface for data requests

### Repository Information
- **GitHub**: https://github.com/rewriter88/theta_dowloader_new
- **Branch**: main
- **Owner**: rewriter88 (Ricardo Ellstein)
- **Email**: ricardo@figment.com.mx

### Common Commands for Development
```bash
# Start Theta Terminal (from project root)
java -jar ThetaTerminal/ThetaTerminalv3.jar

# Test API connectivity
curl "http://localhost:25503/v3/stock/list/symbols?format=json"

# Git workflow
git add .
git commit -m "Description"
git push origin main
```

### Notes for AI Assistant
- Always check if Theta Terminal is running before suggesting API calls
- Prioritize options data functionality (it's the main subscription)
- Security is critical - never suggest committing credentials
- Focus on robust error handling and data validation
- Consider performance for large data downloads
