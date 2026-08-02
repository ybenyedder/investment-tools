#!/bin/bash
# Raspberry Pi 5 Installation & Deployment Script for Investment Tools
# Target Domain: stock.tree4five.com

set -e

DOMAIN="stock.tree4five.com"
PROJECT_DIR="/opt/investmenttools"
USER_NAME=$USER

echo "============================================================"
echo "🚀 Starting Investment Tools Setup on Raspberry Pi 5..."
echo "Domain: $DOMAIN"
echo "============================================================"

# 1. Update and install system dependencies
echo "[1/8] Updating system and installing dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential python3 python3-venv python3-dev \
    python3-pip cmake nginx certbot python3-certbot-nginx curl git \
    libatlas-base-dev gfortran pkg-config

# Install Node.js (v20 for Next.js)
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# 2. Setup Project Directory
echo "[2/8] Setting up project directory..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Creating $PROJECT_DIR..."
    sudo mkdir -p $PROJECT_DIR
    sudo chown -R $USER_NAME:$USER_NAME $PROJECT_DIR
    # Assuming the code is currently in the current directory, copy it over
    cp -r ./* $PROJECT_DIR/
else
    echo "Directory $PROJECT_DIR already exists, syncing files..."
    rsync -a --exclude 'venv' --exclude 'node_modules' --exclude '.next' ./ $PROJECT_DIR/
fi

cd $PROJECT_DIR

# 3. Setup Python Backend
echo "[3/8] Configuring Python Backend..."
cd $PROJECT_DIR/backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip

# Install dependencies. (Llama-cpp-python needs cmake and build-essential which we installed)
pip install fastapi uvicorn yfinance pandas numpy scikit-learn PyPortfolioOpt statsmodels lxml requests bleach pytest huggingface_hub
CMAKE_ARGS="-DLLAMA_METAL=off" pip install --force-reinstall --no-cache-dir llama-cpp-python

# Download LLM
echo "Downloading TinyLlama Model..."
bash install_llm.sh
deactivate

# 4. Setup Node.js Frontend
echo "[4/8] Configuring Next.js Frontend..."
cd $PROJECT_DIR/frontend
npm install
npm run build

# 5. Create Systemd Services
echo "[5/8] Creating Systemd Services for automatic startup..."

# Backend Service
sudo bash -c "cat > /etc/systemd/system/investment-backend.service <<EOF
[Unit]
Description=Investment Tools FastAPI Backend
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR/backend
Environment=\"PATH=$PROJECT_DIR/backend/venv/bin\"
ExecStart=$PROJECT_DIR/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

# Frontend Service
sudo bash -c "cat > /etc/systemd/system/investment-frontend.service <<EOF
[Unit]
Description=Investment Tools Next.js Frontend
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR/frontend
Environment=\"PORT=3000\"
Environment=\"NODE_ENV=production\"
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd and start services
sudo systemctl daemon-reload
sudo systemctl enable investment-backend
sudo systemctl enable investment-frontend
sudo systemctl restart investment-backend
sudo systemctl restart investment-frontend

# 6. Configure Nginx Reverse Proxy
echo "[6/8] Configuring Nginx for $DOMAIN..."
sudo bash -c "cat > /etc/nginx/sites-available/$DOMAIN <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Route /api directly to the Python FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    # Route everything else to the Next.js Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
}
EOF"

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
# Remove default nginx config to prevent conflicts
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# 7. Setup SSL Certificate (Cloudflare Mode)
echo "[7/8] Cloudflare SSL Configuration..."
echo "Since you are using Cloudflare, you have two great options to secure your site:"
echo "Option A (Cloudflare Tunnels - HIGHLY RECOMMENDED):"
echo "   You do NOT need to port-forward your router. Install 'cloudflared' on this Pi,"
echo "   authenticate, and route traffic securely to localhost:80."
echo "Option B (Cloudflare Proxy):"
echo "   Ensure your Cloudflare SSL/TLS encryption mode is set to 'Flexible' (no certbot needed) "
echo "   or 'Full' (you can generate a Cloudflare Origin Pull Certificate and place it in Nginx)."

# 8. Verification & Health Check
echo "[8/8] Verifying internal services..."
sleep 5 # give services a moment to start
echo "Backend Status: \$(sudo systemctl is-active investment-backend)"
echo "Frontend Status: \$(sudo systemctl is-active investment-frontend)"
echo "Nginx Status: \$(sudo systemctl is-active nginx)"

echo "Testing Local Backend Endpoint..."
curl -s http://127.0.0.1:8000/api/universe | head -c 50 && echo " ... [OK]"

echo "Testing Local Frontend Endpoint..."
curl -s http://127.0.0.1:3000 | head -c 50 && echo " ... [OK]"

echo "============================================================"
echo "✅ Installation Complete!"
echo "Your app is now configured to run on a Raspberry Pi 5."
echo "Services:"
echo " - sudo systemctl status investment-backend"
echo " - sudo systemctl status investment-frontend"
echo " - sudo systemctl status nginx"
echo ""
echo "☁️  Cloudflare Next Steps:"
echo "1. If using Cloudflare Tunnels (Best for Pi):"
echo "   Run: curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
echo "   Run: sudo dpkg -i cloudflared.deb"
echo "   Run: cloudflared tunnel login"
echo "   Create a tunnel and route $DOMAIN to http://localhost:80"
echo "2. If using standard Cloudflare DNS Proxying:"
echo "   - Port forward port 80 on your router to this Pi."
echo "   - In your Cloudflare Dashboard, set SSL/TLS to 'Flexible'."
echo "============================================================"
