#!/bin/bash
# Stop Theta Terminal Script

echo "🛑 Stopping Theta Terminal..."

# Kill Theta Terminal processes
pkill -f ThetaTerminal

echo "✅ Theta Terminal stopped"

# Check if any processes are still running
if pgrep -f ThetaTerminal > /dev/null; then
    echo "⚠️  Some Theta Terminal processes may still be running"
    echo "   Use 'ps aux | grep -i theta' to check"
else
    echo "✅ All Theta Terminal processes stopped"
fi
