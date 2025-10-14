#!/bin/bash

# Atlas Service Client Bot - Script de déploiement VPS
# Usage: sudo ./deploy.sh

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier si on est root
if [ "$EUID" -ne 0 ]; then
    error "Ce script doit être exécuté en tant que root (sudo)"
    exit 1
fi

log "🚀 Démarrage du déploiement d'Atlas Service Client Bot"

# 1. Mise à jour du système
log "📦 Mise à jour du système..."
apt update && apt upgrade -y
success "Système mis à jour"

# 2. Installation des dépendances système
log "🔧 Installation des dépendances système..."
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip git curl wget build-essential
success "Dépendances système installées"

# 3. Créer l'utilisateur atlas-bot
log "👤 Création de l'utilisateur atlas-bot..."
if ! id "atlas-bot" &>/dev/null; then
    useradd -m -s /bin/bash atlas-bot
    success "Utilisateur atlas-bot créé"
else
    warning "Utilisateur atlas-bot existe déjà"
fi

# 4. Créer le répertoire de l'application
log "📁 Configuration du répertoire de l'application..."
APP_DIR="/opt/atlas-bot"
mkdir -p $APP_DIR
chown atlas-bot:atlas-bot $APP_DIR

# 5. Cloner ou mettre à jour le repository
log "📥 Téléchargement du code source..."
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR
    sudo -u atlas-bot git pull origin main
    success "Code source mis à jour"
else
    cd /opt
    sudo -u atlas-bot git clone https://github.com/votre-username/Atlas_service_client_bot.git atlas-bot
    success "Code source téléchargé"
fi

cd $APP_DIR

# 6. Créer l'environnement virtuel Python
log "🐍 Configuration de l'environnement Python..."
sudo -u atlas-bot python3.11 -m venv venv
sudo -u atlas-bot $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u atlas-bot $APP_DIR/venv/bin/pip install -r requirements.txt
success "Environnement Python configuré"

# 7. Configuration des variables d'environnement
log "⚙️  Configuration des variables d'environnement..."
if [ ! -f "$APP_DIR/.env" ]; then
    sudo -u atlas-bot cp .env.example .env
    warning "Fichier .env créé depuis .env.example"
    warning "⚠️  IMPORTANT: Éditez $APP_DIR/.env avec vos vraies valeurs avant de démarrer le bot"
else
    warning "Fichier .env existe déjà"
fi

# 8. Créer le service systemd
log "🔧 Configuration du service systemd..."
cat > /etc/systemd/system/atlas-bot.service << EOF
[Unit]
Description=Atlas Service Client Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=atlas-bot
Group=atlas-bot
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=atlas-bot

# Sécurité
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

# 9. Recharger systemd et activer le service
log "🔄 Configuration du service systemd..."
systemctl daemon-reload
systemctl enable atlas-bot
success "Service systemd configuré"

# 10. Configuration des logs
log "📝 Configuration des logs..."
mkdir -p /var/log/atlas-bot
chown atlas-bot:atlas-bot /var/log/atlas-bot

# 11. Configuration du firewall (optionnel)
log "🔥 Configuration du firewall..."
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow ssh
    ufw allow 8000/tcp  # Port pour healthcheck
    success "Firewall configuré"
else
    warning "UFW non installé, configuration du firewall ignorée"
fi

# 12. Créer un script de gestion
log "📜 Création des scripts de gestion..."
cat > /usr/local/bin/atlas-bot << 'EOF'
#!/bin/bash
case "$1" in
    start)
        sudo systemctl start atlas-bot
        echo "Bot démarré"
        ;;
    stop)
        sudo systemctl stop atlas-bot
        echo "Bot arrêté"
        ;;
    restart)
        sudo systemctl restart atlas-bot
        echo "Bot redémarré"
        ;;
    status)
        sudo systemctl status atlas-bot
        ;;
    logs)
        sudo journalctl -u atlas-bot -f
        ;;
    update)
        cd /opt/atlas-bot
        sudo -u atlas-bot git pull origin main
        sudo systemctl restart atlas-bot
        echo "Bot mis à jour et redémarré"
        ;;
    *)
        echo "Usage: atlas-bot {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/atlas-bot
success "Scripts de gestion créés"

# 13. Afficher les informations finales
log "📋 Résumé de l'installation"
echo ""
success "🎉 Installation terminée avec succès !"
echo ""
echo "📁 Répertoire de l'application: $APP_DIR"
echo "👤 Utilisateur: atlas-bot"
echo "🔧 Service: atlas-bot"
echo ""
echo "📝 Prochaines étapes:"
echo "1. Éditez $APP_DIR/.env avec vos vraies valeurs"
echo "2. Démarrez le bot: atlas-bot start"
echo "3. Vérifiez le statut: atlas-bot status"
echo "4. Consultez les logs: atlas-bot logs"
echo ""
echo "🛠️  Commandes utiles:"
echo "  atlas-bot start    - Démarrer le bot"
echo "  atlas-bot stop     - Arrêter le bot"
echo "  atlas-bot restart  - Redémarrer le bot"
echo "  atlas-bot status   - Voir le statut"
echo "  atlas-bot logs     - Voir les logs en temps réel"
echo "  atlas-bot update   - Mettre à jour et redémarrer"
echo ""
warning "⚠️  N'oubliez pas de configurer $APP_DIR/.env avant de démarrer !"
