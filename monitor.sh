#!/bin/bash
# BPF Karaoke System - Monitoring Script

echo "================================================"
echo "  BPF Karaoke System Monitor"
echo "================================================"
echo ""

# Check container status
echo "📦 Container Status:"
docker compose ps
echo ""

# Check health
echo "❤️  Health Check:"
HEALTH=$(curl -sk https://nasbpfsby.duckdns.org:8443/api/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo "❌ Cannot connect to API"
fi
echo ""

# Check disk usage
echo "💾 Disk Usage:"
df -h | grep -E "Filesystem|/media/lagu|/var/lib/docker"
echo ""

# Check memory
echo "🧠 Memory Usage:"
free -h | grep -E "Mem|Swap"
echo ""

# Check logs (last 10 lines)
echo "📋 Recent Backend Logs:"
docker compose logs --tail=10 karaoke_backend 2>/dev/null
echo ""

echo "================================================"
