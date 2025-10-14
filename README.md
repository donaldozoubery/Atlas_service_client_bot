# 🤖 Atlas Service Client Bot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0.svg)
![AI](https://img.shields.io/badge/AI-OpenAI%20%7C%20Groq%20%7C%20OpenRouter-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Bot de support client intelligent pour Atlas Signals avec IA intégrée**

[🚀 Déploiement](#-déploiement) • [⚙️ Configuration](#️-configuration) • [📚 Documentation](#-documentation) • [🛠️ Support](#️-support)

</div>

---

## 📋 Vue d'ensemble

**Atlas Service Client Bot** est un bot Telegram sophistiqué qui fournit un support client intelligent 24/7 pour Atlas Signals. Il utilise l'intelligence artificielle pour répondre automatiquement aux questions des utilisateurs, gérer les tickets de support, et fournir une assistance personnalisée.

### ✨ Fonctionnalités Principales

- 🤖 **Support IA Intelligent** - Réponses automatiques avec OpenAI, Groq, OpenRouter ou Ollama
- 🎫 **Système de Tickets** - Gestion complète des demandes de support
- 📚 **Base de Connaissances** - Apprentissage automatique depuis les documents métier
- 🔒 **Sécurité Avancée** - Contrôle d'accès et rate limiting
- 📊 **Analytics** - Suivi des performances et satisfaction client
- 🌍 **Multi-langue** - Support français avec détection automatique
- ⚡ **Haute Performance** - Cache intelligent et optimisations

---

## 🚀 Déploiement

### Option 1: VPS (Recommandé)

#### Prérequis
- VPS Ubuntu 20.04+ ou Debian 11+
- Python 3.11+
- Git
- Accès root ou sudo

#### Installation Automatique

```bash
# Cloner le repository
git clone https://github.com/votre-username/Atlas_service_client_bot.git
cd Atlas_service_client_bot

# Exécuter le script d'installation
chmod +x deploy.sh
sudo ./deploy.sh
```

#### Installation Manuelle

```bash
# 1. Mise à jour du système
sudo apt update && sudo apt upgrade -y

# 2. Installation de Python et dépendances
sudo apt install python3.11 python3.11-venv python3-pip git -y

# 3. Cloner le repository
git clone https://github.com/votre-username/Atlas_service_client_bot.git
cd Atlas_service_client_bot

# 4. Créer l'environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# 5. Installer les dépendances
pip install -r requirements.txt

# 6. Configurer les variables d'environnement
cp .env.example .env
nano .env  # Éditer avec vos valeurs

# 7. Créer le service systemd
sudo cp atlas-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable atlas-bot
sudo systemctl start atlas-bot

# 8. Vérifier le statut
sudo systemctl status atlas-bot
```

### Option 2: Docker

```bash
# Construire l'image
docker build -t atlas-bot .

# Lancer le conteneur
docker run -d \
  --name atlas-bot \
  --env-file .env \
  --restart unless-stopped \
  atlas-bot
```

### Option 3: Cloud (Fly.io, Railway, Render)

Voir les fichiers de configuration :
- `fly.toml` - Configuration Fly.io
- `railway.json` - Configuration Railway  
- `render.yaml` - Configuration Render

---

## ⚙️ Configuration

### Variables d'Environnement

Créez un fichier `.env` basé sur `.env.example` :

```env
# ===== OBLIGATOIRE =====
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# ===== CONFIGURATION IA =====
AI_PROVIDER=groq  # openai, openrouter, groq, ollama
AI_MODEL=llama-3.1-70b-versatile
AI_TEMPERATURE=0.2
AI_MAX_TOKENS=512

# Clés API selon le fournisseur
GROQ_API_KEY=gsk_...
# OU
OPENAI_API_KEY=sk-...
# OU
OPENROUTER_API_KEY=sk-or-...

# ===== ACCÈS AU BOT =====
ATLAS_ALLOW_ALL=true
ATLAS_MEMBER_IDS=123456789,987654321
ATLAS_ADMIN_IDS=123456789

# ===== BASE DE CONNAISSANCES =====
ATLAS_KB_PATH=kb
ATLAS_KB_MAX_CHARS=80000

# ===== CONFIGURATION SUPPORT =====
ADMIN_GROUP_ID=-1001234567890

# ===== LIMITES =====
RATE_LIMIT_PER_MIN=12
FAQ_CACHE_MAX=200

# ===== SITE WEB =====
ATLAS_SITE_URL=https://atlassignals.site
```

### Base de Connaissances

Placez vos documents métier dans le dossier `kb/` :
- Fichiers `.md` ou `.txt`
- Le bot apprendra automatiquement le contenu
- Limite configurable via `ATLAS_KB_MAX_CHARS`

---

## 📚 Documentation

### Commandes Utilisateur

| Commande | Description |
|----------|-------------|
| `/start` | Message d'accueil et instructions |
| `/help` | Liste des commandes disponibles |
| `/ask <question>` | Poser une question à l'IA |
| `/id` | Afficher votre ID Telegram |
| `/support` | Créer un ticket de support |

### Commandes Admin

| Commande | Description |
|----------|-------------|
| `/reloadkb` | Recharger la base de connaissances |
| `/tickets` | Lister les tickets récents |
| `/ticket <id>` | Détails d'un ticket |
| `/close <id>` | Fermer un ticket |
| `/assign <id> <admin>` | Assigner un ticket |

### API Endpoints

- `GET /healthz` - Statut du service (JSON)

---

## 🛠️ Support

### Logs et Monitoring

```bash
# Voir les logs en temps réel
sudo journalctl -u atlas-bot -f

# Vérifier le statut
sudo systemctl status atlas-bot

# Redémarrer le service
sudo systemctl restart atlas-bot
```

### Dépannage

1. **Bot ne répond pas**
   - Vérifiez `TELEGRAM_BOT_TOKEN`
   - Consultez les logs : `sudo journalctl -u atlas-bot`

2. **Erreurs IA**
   - Vérifiez les clés API
   - Testez avec `AI_PROVIDER=ollama` (local)

3. **Problèmes de permissions**
   - Vérifiez `ATLAS_MEMBER_IDS` et `ATLAS_ADMIN_IDS`
   - Activez `ATLAS_ALLOW_ALL=true` pour tester

### Mise à Jour

```bash
# Arrêter le service
sudo systemctl stop atlas-bot

# Mettre à jour le code
git pull origin main

# Redémarrer
sudo systemctl start atlas-bot
```

---

## 🏗️ Architecture

```
Atlas Service Client Bot
├── main.py                 # Bot principal
├── kb/                     # Base de connaissances
│   ├── atlas_business.md   # Contexte métier
│   └── DOCUMENTATION_*.md  # Documentation complète
├── requirements.txt        # Dépendances Python
├── .env.example           # Variables d'environnement
├── Dockerfile             # Configuration Docker
├── fly.toml              # Configuration Fly.io
├── railway.json          # Configuration Railway
├── render.yaml           # Configuration Render
└── deploy.sh             # Script de déploiement VPS
```

---

## 🔧 Développement

### Installation Locale

```bash
# Cloner et installer
git clone https://github.com/votre-username/Atlas_service_client_bot.git
cd Atlas_service_client_bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Éditer .env avec vos valeurs

# Lancer
python main.py
```

### Tests

```bash
# Tests unitaires (à implémenter)
python -m pytest tests/

# Test de l'API
curl http://localhost:8000/healthz
```

---

## 📈 Roadmap

- [ ] Interface web d'administration
- [ ] Analytics avancés
- [ ] Support multi-langue
- [ ] Intégration CRM
- [ ] Webhooks
- [ ] API REST complète

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci de :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📞 Contact

- **Site Web** : [atlassignals.site](https://atlassignals.site)
- **Email** : serviceclient@atlassignals.site
- **Support** : Via le bot Telegram

---

<div align="center">

**Fait avec ❤️ pour Atlas Signals**

*Dernière mise à jour : Décembre 2024*

</div>