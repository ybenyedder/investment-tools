#!/bin/bash
set -euo pipefail

# Configuration du serveur
# Renseignez les variables via l'environnement ou répondez aux invites :
#   DEPLOY_USER, DEPLOY_IP, DEPLOY_DIR, DEPLOY_PASSWORD (ou DEPLOY_SSH_KEY pour une clé SSH)
# Ne jamais committer de mot de passe dans ce fichier.
SERVER_USER="${DEPLOY_USER:-volt}"
SERVER_IP="${DEPLOY_IP:-192.168.1.87}" # Remplacez par l'IP de votre serveur
PROJECT_DIR="${DEPLOY_DIR:-~/investment-tools}"
SSH_KEY="${DEPLOY_SSH_KEY:-}"

if [ -n "$SSH_KEY" ]; then
    run_remote() { ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"; }
    RSYNC_EH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no"
else
    if [ -z "${DEPLOY_PASSWORD:-}" ]; then
        read -s -p "Mot de passe SSH pour $SERVER_USER@$SERVER_IP : " PASSWORD
        echo
    else
        PASSWORD="$DEPLOY_PASSWORD"
    fi
    # Note : Si sshpass n'est pas installé : sudo apt install sshpass
    if ! command -v sshpass &> /dev/null; then
        echo "sshpass is not installed. Installing..."
        sudo apt-get update && sudo apt-get install -y sshpass
    fi
    run_remote() { sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"; }
    RSYNC_EH="ssh -o StrictHostKeyChecking=no"
fi

echo "Déploiement du projet sur $SERVER_IP..."

# 1. Création du répertoire cible sur le serveur
echo "Préparation du répertoire..."
run_remote "mkdir -p $PROJECT_DIR"

# 2. Copie des fichiers vers le serveur
echo "Transfert des fichiers en cours..."
if [ -n "$SSH_KEY" ]; then
    rsync -avz -e "$RSYNC_EH" \
        --exclude '.git' --exclude 'node_modules' --exclude 'venv' --exclude '.next' \
        --exclude '__pycache__' --exclude '*.db' \
        --exclude 'chroma_db' --exclude 'backend-data' --exclude 'backend/models' \
        ./ "$SERVER_USER@$SERVER_IP:$PROJECT_DIR/"
else
    sshpass -p "$PASSWORD" rsync -avz -e "$RSYNC_EH" \
        --exclude '.git' --exclude 'node_modules' --exclude 'venv' --exclude '.next' \
        --exclude '__pycache__' --exclude '*.db' \
        --exclude 'chroma_db' --exclude 'backend-data' --exclude 'backend/models' \
        ./ "$SERVER_USER@$SERVER_IP:$PROJECT_DIR/"
fi

# 3. Récupération de whatsapp-bot depuis GitHub (Désactivé : on déploie la version locale)
echo "Mise à jour de whatsapp-bot ignorée depuis GitHub (copie locale utilisée)..."
# run_remote "cd $PROJECT_DIR && if [ ! -d 'whatsapp-bot' ]; then git clone https://github.com/wwebtvmedia/whatsapp-bot; elif [ -d 'whatsapp-bot/.git' ]; then (cd whatsapp-bot && git pull); else T=\$(mktemp -d) && git clone --depth 1 https://github.com/wwebtvmedia/whatsapp-bot \$T/src && rsync -a --exclude 'data/' --exclude 'auth/' --exclude 'downloads/' --exclude '.env' --exclude 'embedding-service/cache/' --exclude '.dockerignore' \$T/src/ whatsapp-bot/ && rm -rf \$T; fi; [ -f whatsapp-bot/.dockerignore ] || printf 'data/\nauth/\ndownloads/\nembedding-service/cache/\nnode_modules/\n.git/\n' > whatsapp-bot/.dockerignore; [ -f whatsapp-bot/.dockerignore ] && grep -q '^data/' whatsapp-bot/.dockerignore || printf 'data/\nauth/\ndownloads/\nembedding-service/cache/\nnode_modules/\n.git/\n' > whatsapp-bot/.dockerignore"

# 4. Lancement de l'application via Docker Compose
echo "Démarrage des services sur le serveur..."
run_remote "cd $PROJECT_DIR && docker compose down --remove-orphans || true && docker compose up -d --build"

# 5. Vérification finale
echo "Vérification des conteneurs..."
run_remote "cd $PROJECT_DIR && docker compose ps"

echo "Déploiement terminé avec succès !"
