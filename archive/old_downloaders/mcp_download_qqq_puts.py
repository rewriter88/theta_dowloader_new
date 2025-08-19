#!/usr/bin/env python3
"""
Direct MCP client for Theta Data
Downloads QQQ puts data via Theta's MCP server
"""

import requests
import json
import time
import os

# Configuration
MCP_URL = "http://localhost:25503/mcp/sse"
OUTPUT_DIR = "/Volumes/SSD 4TB/Theta Terminal/QQQ/2025-08-08"

def create_output_dir():
    """Create output directory if it doesn't exist"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_DIR}")

def send_mcp_request(prompt):
    """Send a request to Theta's MCP server"""
    print(f"🔄 Sending MCP request: {prompt}")
    
    try:
        # Connect to MCP SSE endpoint
        response = requests.get(MCP_URL, stream=True, timeout=30)
        
        if response.status_code == 200:
            print("✅ Connected to Theta MCP server")
            
            # Parse SSE stream
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"📡 MCP Response: {line}")
                    if "data:" in line:
                        return line.replace("data: ", "")
        else:
            print(f"❌ MCP connection failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ MCP error: {e}")
        return None

def main():
    """Main function to download QQQ puts via MCP"""
    print("🚀 Theta Data MCP Client")
    print("=" * 50)
    
    # Create output directory
    create_output_dir()
    
    # MCP request for QQQ puts data
    mcp_request = """
    Download historical QQQ put options data with these parameters:
    - Symbol: QQQ
    - Rights: PUT only
    - Date range: 2017-08-08 to 2025-08-08
    - Interval: 5 minutes
    - Format: CSV
    - Save to: /Volumes/SSD 4TB/Theta Terminal/QQQ/2025-08-08/
    
    Use the Theta Data API v3 option history quote endpoint to get all put options data.
    """
    
    # Send request to MCP
    result = send_mcp_request(mcp_request)
    
    if result:
        print(f"✅ MCP request sent successfully")
        print(f"📝 Result: {result}")
    else:
        print("❌ MCP request failed")

if __name__ == "__main__":
    main()
