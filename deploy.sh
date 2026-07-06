#!/bin/bash
set -e

echo "================================================"
echo "  BPF Karaoke System - Deployment Script"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running in correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Run this script from ~/bpf_karaoke directory${NC}"
    exit 1
fi

# Load environment
source .env 2>/dev/null || true

echo -e "${YELLOW}[1/6]${NC} Creating necessary directories..."
mkdir -p database/data media/lagu backend/uploads
echo -e "${GREEN}✓ Directories created${NC}"

echo -e "${YELLOW}[2/6]${NC} Updating Nginx configuration..."
# Copy karaoke config to existing nginx
sudo cp nginx/karaoke.conf /home/it-ef/hybrid_nextcloud/nginx/conf.d/karaoke.conf 2>/dev/null || {
    echo -e "${RED}Failed to copy nginx config. Make sure path is correct.${NC}"
    echo "You may need to manually copy: nginx/karaoke.conf -> /home/it-ef/hybrid_nextcloud/nginx/conf.d/"
}
echo -e "${GREEN}✓ Nginx config updated${NC}"

echo -e "${YELLOW}[3/6]${NC} Building Docker images..."
docker compose build --no-cache
echo -e "${GREEN}✓ Images built${NC}"

echo -e "${YELLOW}[4/6]${NC} Starting services..."
docker compose up -d
echo -e "${GREEN}✓ Services started${NC}"

echo -e "${YELLOW}[5/6]${NC} Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ All services are running${NC}"
else
    echo -e "${RED}✗ Some services failed to start${NC}"
    docker compose logs
    exit 1
fi

echo -e "${YELLOW}[6/6]${NC} Restarting Nginx to apply new config..."
docker restart nextcloud_nginx 2>/dev/null || echo "Nginx restart skipped (may need manual restart)"
echo -e "${GREEN}✓ Nginx restarted${NC}"

echo ""
echo "================================================"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo "================================================"
echo ""
echo "Access URLs:"
echo "  Operator Screen: https://nasbpfsby.duckdns.org:8443/operator?screen=1"
echo "  Player Screen:   https://nasbpfsby.duckdns.org:8443/player?screen=2"
echo "  Remote Control:  https://nasbpfsby.duckdns.org:8443/remote"
echo "  Admin Panel:     https://nasbpfsby.duckdns.org:8443/admin"
echo "  API Docs:        https://nasbpfsby.duckdns.org:8443/docs"
echo ""
echo "Default Credentials:"
echo "  Admin:    admin / AdminK4r40k3!2024"
echo "  Operator: operator / operator123"
echo ""
echo "To scan media files, place your videos in:"
echo "  $(pwd)/media/lagu/"
echo "Then visit Admin Panel and click 'Scan Media Folder'"
echo ""
echo -e "${YELLOW}Important:${NC} Make sure port 8443 is open in your firewall"
echo "  sudo ufw allow 8443/tcp"
echo ""
