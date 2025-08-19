#!/bin/bash
# Theta Terminal v3 Startup Script
# Starts Theta Terminal with MCP support

echo "🚀 Starting Theta Terminal v3 with MCP support..."

# Kill any existing Theta Terminal processes
pkill -f ThetaTerminal 2>/dev/null

# Change to theta_terminal directory
cd theta_terminal

# Start Theta Terminal in background
nohup java -jar ThetaTerminalv3.jar --creds-file=creds.txt > ../archive/logs/theta_terminal_v3.log 2>&1 &

echo "⏳ Waiting for Theta Terminal to start..."
sleep 10

# Check if it's running
if curl -s http://localhost:25503/ > /dev/null 2>&1; then
    echo "✅ Theta Terminal is running at http://localhost:25503/"
    echo "✅ MCP server available at http://localhost:25503/mcp/sse"
    echo ""
    echo "To use with Claude CLI:"
    echo "  claude mcp add --transport sse ThetaData http://localhost:25503/mcp/sse"
    echo ""
    echo "Test API with:"
    echo "  curl -s \"http://localhost:25503/v3/list/stocks\" | head -5"
else
    echo "❌ Theta Terminal failed to start. Check logs in archive/logs/"
fi

cd ..
