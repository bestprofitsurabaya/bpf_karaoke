#!/bin/bash
set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}>>> [1/4] Preparing Environments...${NC}"
mkdir -p database/data media/lagu backend/uploads

echo -e "${YELLOW}>>> [2/4] Injecting Config into nextcloud_nginx shared volume...${NC}"
sudo cp nginx/karaoke.conf /home/it-ef/hybrid_nextcloud/nginx/conf.d/karaoke.conf

echo -e "${YELLOW}>>> [3/4] Starting Karaoke Stack Services via Docker Compose...${NC}"
docker compose build --no-cache
docker compose up -d

echo -e "${YELLOW}>>> [4/4] Restarting Reverse Proxy to Apply Configurations...${NC}"
docker restart nextcloud_nginx

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN} BPF KARAOKE SYSTEM DEPLOYED SUCCESSFULLY! ${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "Access Point: https://nasbpfsby.duckdns.org:8443/"
echo -e "API Docs:     https://nasbpfsby.duckdns.org:8443/docs"
