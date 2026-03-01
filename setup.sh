#!/bin/bash
# =============================================================================
# NFC Payment System — Setup automatico (mkcert + HTTPS + docker-compose)
# Utilizzo: bash setup.sh
# =============================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════╗"
echo "║   NFC Payment System — Setup HTTPS       ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Controlla dipendenze ──────────────────────────────────────────────────
echo -e "${GREEN}[1/5] Controllo dipendenze...${NC}"

if ! command -v docker &>/dev/null; then
    echo -e "${RED}✗ Docker non trovato. Installalo da https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
    echo -e "${RED}✗ docker-compose non trovato.${NC}"
    exit 1
fi

echo -e "  ✓ Docker trovato: $(docker --version)"

# ── 2. Installa mkcert se mancante ───────────────────────────────────────────
echo -e "${GREEN}[2/5] Controllo mkcert...${NC}"

if ! command -v mkcert &>/dev/null; then
    echo -e "  ${YELLOW}mkcert non trovato, installo...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        MKCERT_VERSION=$(curl -s https://api.github.com/repos/FiloSottile/mkcert/releases/latest \
            | grep '"tag_name"' | cut -d'"' -f4)
        curl -Lo /tmp/mkcert \
            "https://github.com/FiloSottile/mkcert/releases/download/${MKCERT_VERSION}/mkcert-${MKCERT_VERSION}-linux-amd64"
        chmod +x /tmp/mkcert
        sudo mv /tmp/mkcert /usr/local/bin/mkcert
        sudo apt-get install -y libnss3-tools 2>/dev/null || true
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &>/dev/null; then
            brew install mkcert nss
        else
            echo -e "${RED}✗ Homebrew non trovato. Installa mkcert manualmente: https://github.com/FiloSottile/mkcert${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ OS non riconosciuto. Installa mkcert manualmente: https://github.com/FiloSottile/mkcert${NC}"
        exit 1
    fi
fi

echo -e "  ✓ mkcert trovato: $(mkcert --version)"

# ── 3. Installa CA locale e genera certificati ───────────────────────────────
echo -e "${GREEN}[3/5] Installo CA locale e genero certificati...${NC}"

mkcert -install

mkdir -p nginx/certs
pushd nginx/certs > /dev/null
mkcert localhost 127.0.0.1 ::1
mv localhost+2.pem     cert.pem 2>/dev/null || \
mv localhost+1.pem     cert.pem 2>/dev/null || \
mv localhost.pem       cert.pem 2>/dev/null || true
mv localhost+2-key.pem key.pem  2>/dev/null || \
mv localhost+1-key.pem key.pem  2>/dev/null || \
mv localhost-key.pem   key.pem  2>/dev/null || true
popd > /dev/null

if [ ! -f nginx/certs/cert.pem ] || [ ! -f nginx/certs/key.pem ]; then
    echo -e "${RED}✗ Generazione certificati fallita. Controlla i log di mkcert sopra.${NC}"
    exit 1
fi

echo -e "  ✓ Certificati generati in nginx/certs/"

# ── 4. Crea .env con HMAC_SECRET casuale se non esiste ───────────────────────
echo -e "${GREEN}[4/5] Configuro variabili d'ambiente...${NC}"

if [ ! -f .env ]; then
    HMAC_SECRET=$(openssl rand -hex 32)
    echo "HMAC_SECRET=${HMAC_SECRET}" > .env
    echo -e "  ✓ File .env creato con HMAC_SECRET casuale"
else
    echo -e "  ✓ File .env già esistente, non sovrascritto"
fi

# ── 5. Avvia docker-compose ──────────────────────────────────────────────────
echo -e "${GREEN}[5/5] Avvio i container...${NC}"

if docker compose version &>/dev/null 2>&1; then
    docker compose up --build
else
    docker-compose up --build
fi

echo -e ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Servizi disponibili                 ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║${NC}  Cassa    →  ${GREEN}https://localhost:5443${NC}           ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  Bar      →  ${GREEN}https://localhost:5444${NC}           ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  Vending  →  ${GREEN}https://localhost:5445${NC}           ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  Backend  →  ${GREEN}https://localhost:8443/api/stats${NC}  ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
