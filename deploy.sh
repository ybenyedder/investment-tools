#!/bin/bash

# Configuration du serveur
# Remplacez les valeurs ci-dessous par vos véritables informations de connexion.
SERVER_USER="volt"
SERVER_IP="192.168.1.87" # Remplacez par l'IP de votre serveur
PASSWORD="Yosra3615@$" # Remplacez par votre mot de passe
PROJECT_DIR="~/investment-tools"

echo "Déploiement du projet sur $SERVER_IP..."

# Utilisation de sshpass pour automatiser la connexion avec mot de passe
# Note : Si sshpass n'est pas installé, vous pouvez l'installer avec : sudo apt install sshpass

# 1. Création du répertoire cible sur le serveur
echo "Préparation du répertoire..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"

# 2. Copie des fichiers vers le serveur
echo "Transfert des fichiers en cours..."
sshpass -p "$PASSWORD" rsync -avz -e "ssh -o StrictHostKeyChecking=no" --exclude '.git' --exclude 'node_modules' --exclude 'venv' --exclude '.next' --exclude '__pycache__' ./ $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

# 3. Lancement de l'application via Docker Compose
echo "Démarrage des services sur le serveur..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && docker compose up -d --build"

echo "Déploiement terminé avec succès !"
