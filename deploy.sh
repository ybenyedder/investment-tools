#!/bin/bash

# Configuration du serveur
SERVER_USER="volt"
SERVER_IP="192.168.1.87"
PASSWORD="Yosra3615@$"
PROJECT_DIR="~/investment-tools"

echo "Déploiement du projet sur $SERVER_IP..."

# Verify sshpass is installed
if ! command -v sshpass &> /dev/null
then
    echo "sshpass is not installed. Installing..."
    sudo apt-get update && sudo apt-get install -y sshpass
fi

# 1. Création du répertoire cible sur le serveur
echo "Préparation du répertoire..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"

# 2. Copie des fichiers vers le serveur (including Docker files)
echo "Transfert des fichiers en cours..."
sshpass -p "$PASSWORD" rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude 'venv' \
    --exclude '.next' \
    --exclude '__pycache__' \
    --exclude '*.db' \
    --exclude 'chroma_db' \
    ./ $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

# 3. Récupération de whatsapp-bot depuis GitHub (for company information fetching)
echo "Mise à jour de whatsapp-bot depuis GitHub..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && if [ -d 'whatsapp-bot' ]; then cd whatsapp-bot && git pull && cd ..; else git clone https://github.com/wwebtvmedia/whatsapp-bot; fi"

# 4. Lancement de l'application via Docker Compose
echo "Démarrage des services sur le serveur..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && docker compose down --remove-orphans; docker rm -f \$(docker ps -q -f expose=8000 2>/dev/null) 2>/dev/null || true; docker compose up -d --build"

echo "Déploiement terminé avec succès !"
