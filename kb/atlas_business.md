# Atlas Signals - Contexte métier

## Activité
- Canal Telegram avec signaux XAU/USD (or) et canal de formation pour aider les traders à devenir rentables.
- Communauté en croissance: un nouveau channel est ouvert à chaque palier de 1000 membres.
- Historique rentable depuis plusieurs années.

## Offres et Tarifs
- Abonnement mensuel (compte lié via broker JM à notre compte): 20 USD / mois
- Abonnement mensuel (compte non lié): 50 USD / mois
- Abonnement à vie + accès VIP: 1000 USD (places VIP limitées à 10 nouveaux membres actuellement)

## VIP
- Accès à un canal VIP avec bonus exclusifs
- Priorité d’assistance, possibilité de poser des questions en privé

## Paiements
- Moyens acceptés: USDT, Mobile Money (Orange Money), bientôt carte bancaire
- Bot de paiement: @PaymentAtlasTradebot
- Après paiement: lien d’invitation unique vers le groupe (valide une seule fois)
- Délai de traitement: jusqu’à 2h en jours ouvrables, plus long le week‑end

## Garantie
- Satisfait ou remboursé si non rentable malgré le suivi de toutes les instructions

## Accès et Support
- Site officiel: atlassignals.site
- Email service client: serviceclient@atlassignals.site
- Commande Telegram utile: /id (affiche l’ID Telegram pour vérification d’accès)

## Notes Opérationnelles
- Le lien d’invitation est à usage unique, ne pas le partager
- En cas de non‑réception de l’invitation après paiement: fournir reçu, @username et ID (/id)
- Les demandes peuvent prendre plus de temps le week‑end 


# 🤖 Atlas Payment Bot - Documentation Complète

## 📋 Vue d'ensemble

**Atlas Payment Bot** est un bot Telegram sophistiqué pour la gestion des abonnements et paiements. Il offre un système complet de gestion des utilisateurs, des abonnements, des paiements, des promotions, des codes promo, des remboursements, et bien plus encore.

## 🚀 Fonctionnalités Principales

### 1. 🤖 Bot Telegram Principal (`main.py`)

**Fonctionnalités clés :**
- Interface utilisateur complète avec menus interactifs
- Gestion des abonnements (50 USD, 100 USD, 2000 USD)
- Système de paiement multi-méthodes (USDT, Orange Money, Carte bancaire)
- Notifications automatiques d'expiration
- Support des codes promo et parrainage
- Gestion des remboursements
- Conversion de devises automatique
- Interface admin complète





### 4. 💰 Gestion des Prix (`price_manager.py`)

**Fonctionnalités :**
- Prix configurables via variables d'environnement
- Support des équivalents MGA (Ariary malgache)
- Liens de paiement dynamiques (Lemon Squeezy, Stripe)
- Mise à jour en temps réel des prix
- Validation des prix

**Plans supportés :**
- Plan 50 USD/mois
- Plan 100 USD/mois  
- Plan 2000 USD (à vie)

### 5. 🎉 Système de Promotions (`promo_manager.py`)

**Fonctionnalités :**
- Promotions temporelles configurables
- Dates de début/fin personnalisables
- Messages promotionnels personnalisés
- Calcul automatique des réductions
- Compte à rebours des promotions
- Activation/désactivation en temps réel

### 6. 🎫 Codes Promo (`promo_codes_manager.py`)

**Fonctionnalités :**
- Création de codes promo personnalisés
- Validation des codes (expiration, usage, plan applicable)
- Limitation du nombre d'utilisations
- Suivi des utilisations par utilisateur
- Nettoyage automatique des codes expirés
- Historique des codes utilisés

### 7. 🏆 Système de Parrainage (`contest_manager.py`)

**Fonctionnalités :**
- Génération de codes de parrainage uniques
- Suivi des parrainages par mois
- Classements mensuels et généraux
- Statistiques de performance
- Système de concours avec récompenses

### 8. 💸 Gestion des Remboursements (`refund_manager.py`)

**Fonctionnalités :**
- Demandes de remboursement dans les 9 jours
- Validation des paiements éligibles
- Traitement en 48h maximum
- Messages personnalisés par statut
- Suivi des demandes
- Statistiques de remboursement

### 9. 🌍 Conversion de Devises (`currency_converter.py`)

**Fonctionnalités :**
- Détection automatique du pays via numéro de téléphone
- Support de 200+ devises mondiales
- Taux de change en temps réel (API exchangerate-api.com)
- Cache intelligent (5 minutes)
- Fallback sur taux fixes en cas d'erreur
- Formatage adapté par devise

**Pays supportés :**
- Afrique : Madagascar, Côte d'Ivoire, Nigeria, Kenya, etc.
- Europe : France, Allemagne, Royaume-Uni, etc.
- Amériques : États-Unis, Brésil, Mexique, etc.
- Asie : Chine, Japon, Inde, etc.
- Moyen-Orient : Arabie Saoudite, Émirats Arabes Unis, etc.

### 10. 🔔 Notifications (`notification_preferences.py`)

**Fonctionnalités :**
- Préférences personnalisables par utilisateur
- Types de notifications :
  - Rappels d'expiration d'abonnement
  - Rappels de renouvellement
  - Confirmations de paiement
- Activation/désactivation individuelle
- Interface utilisateur intuitive

### 11. 🔗 Liens Temporaires (`link_manager.py`)

**Fonctionnalités :**
- Génération de liens temporaires (24h)
- Usage unique par lien
- Validation sécurisée
- Nettoyage automatique des liens expirés
- Suivi des utilisations

### 12. ☁️ Sauvegarde Google Drive (`gdrive_manager.py`)

**Fonctionnalités :**
- Sauvegarde automatique des données
- Synchronisation avec Google Drive
- Sauvegarde des abonnements et paiements
- Mode local en cas d'erreur API
- Gestion des dossiers de sauvegarde


### 2. Système de Notifications Intelligent

**Types de notifications :**
- 2 jours avant expiration
- 1 jour avant expiration
- Jour d'expiration
- 1 jour après expiration
- Confirmations de paiement
- Rappels de renouvellement

### 3. Analytics et Rapports

**Métriques disponibles :**
- Revenus par mois/méthode/plan
- Taux de conversion
- Abonnements actifs/expirés
- Top utilisateurs
- Tendances temporelles
- Performance des codes promo

### 4. Sécurité et Validation

**Mesures de sécurité :**
- Validation des paiements
- Vérification des codes promo
- Liens temporaires sécurisés
- Gestion des erreurs robuste
- Logs détaillés

### 5. Multi-langue et Multi-devise

**Support international :**
- Détection automatique du pays
- Conversion de devises en temps réel
- Messages adaptés par région
- Support de 200+ devises

## 🔧 Maintenance et Support

### Nettoyage Automatique

- Liens temporaires expirés
- Codes promo expirés
- Cache des taux de change
- Logs anciens



## 📈 Évolutions Futures

### Fonctionnalités Prévues

1. **API REST** pour intégration externe
2. **Webhooks** pour notifications en temps réel
3. **Multi-bot** support
4. **Intégration Stripe** avancée
5. **Système de facturation** automatique
6. **Support mobile** natif
7. **Analytics** avancés avec machine learning

### Améliorations Techniques

1. **Microservices** architecture
2. **Docker** containerization
3. **Kubernetes** orchestration
4. **Redis** caching
5. **Elasticsearch** pour les logs
6. **Prometheus** monitoring



## 🎯 Conclusion

**Atlas Payment Bot** est une solution complète et professionnelle pour la gestion des abonnements et paiements via Telegram. Avec ses fonctionnalités avancées, son interface moderne, et son architecture robuste, il répond aux besoins des entreprises modernes qui souhaitent automatiser leur système de paiement.

Le projet est constamment amélioré et évolue selon les besoins des utilisateurs et les nouvelles technologies disponibles.

---

*Dernière mise à jour : oct 2025*
*Version : 2.0.0*
