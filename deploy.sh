#!/bin/bash

# Configuration du serveur
# Renseignez les variables via l'environnement ou répondez aux invites :
#   DEPLOY_USER, DEPLOY_IP, DEPLOY_PASSWORD (ou DEPLOY_SSH_KEY pour une clé SSH)
# Ne jamais committer de mot de passe dans ce fichier.
SERVER_USER="${DEPLOY_USER:-volt}"
SERVER_IP="${DEPLOY_IP:-192.168.1.87}" # Remplacez par l'IP de votre serveur
PROJECT_DIR="${DEPLOY_DIR:-~/investment-tools}"
SSH_KEY="${DEPLOY_SSH_KEY:-}"

if [ -z "$SSH_KEY" ]; then
    if [ -z "$DEPLOY_PASSWORD" ]; then
        read -s -p "Mot de passe SSH pour $SERVER_USER@$SERVER_IP : " PASSWORD
        echo
    else
        PASSWORD="$DEPLOY_PASSWORD"
    fi
    SSH_CMD="sshpass -p \"$PASSWORD\" ssh -o StrictHostKeyChecking=no"
    SSH_BASE="sshpass -p \"$PASSWORD\""
else
    SSH_CMD="ssh -i \"$SSH_KEY\" -o StrictHostKeyChecking=no"
    SSH_BASE="ssh -i \"$SSH_KEY\""
fi

echo "Déploiement du projet sur $SERVER_IP..."

# Utilisation de sshpass pour automatiser la connexion avec mot de passe
# Note : Si sshpass n'est pas installé, vous pouvez l'installer avec : sudo apt install sshpass
if [ -z "$SSH_KEY" ] && ! command -v sshpass &> /dev/null
then
    echo "sshpass is not installed. Installing..."
    sudo apt-get update && sudo apt-get install -y sshpass
fi

# 1. Création du répertoire cible sur le serveur
echo "Préparation du répertoire..."
eval $SSH_CMD $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"

# 2. Copie des fichiers vers le serveur
echo "Transfert des fichiers en cours..."
eval $SSH_BASE rsync -avz -e "'ssh -o StrictHostKeyChecking=no'" --exclude '.git' --exclude 'node_modules' --exclude 'venv' --exclude '.next' --exclude '__pycache__' --exclude 'whatsapp-bot' --exclude '*.db' --exclude 'chroma_db' --exclude 'backend-data' --exclude 'backend/models' ./ $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

# 3. Récupération de whatsapp-bot depuis GitHub
echo "Mise à jour de whatsapp-bot depuis GitHub..."
eval $SSH_CMD $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && if [ -d 'whatsapp-bot' ]; then cd whatsapp-bot && git pull && cd ..; else git clone https://github.com/wwebtvmedia/whatsapp-bot; fi"

# 4. Lancement de l'application via Docker Compose
echo "Démarrage des services sur le serveur..."
eval $SSH_CMD $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && docker compose down --remove-orphans || true && docker compose up -d --build"

echo "Déploiement terminé avec succès !"
