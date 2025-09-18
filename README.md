# Service Client Bot Atlas (Telegram + IA)

## Prérequis
- Python 3.10+
- Compte Telegram (créer un bot via @BotFather)
- Clé d'API pour votre fournisseur IA (OpenAI, OpenRouter, Groq) — ou utilisez Ollama en local (gratuit)

## Installation
```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

## Configuration
1. Créez un fichier `.env` à la racine avec:
   - `TELEGRAM_BOT_TOKEN`
   - `ATLAS_ALLOW_ALL` (optionnel) — si `true`, tout le monde peut utiliser le bot
   - `ATLAS_MEMBER_IDS` (requis si `ATLAS_ALLOW_ALL` n'est pas activé)
   - `ATLAS_ADMIN_IDS` (optionnel, CSV d'IDs autorisés à /reloadkb)
   - `ATLAS_KB_PATH` (optionnel, chemin vers un dossier ou fichier `.md/.txt`)
   - `ATLAS_KB_MAX_CHARS` (optionnel, limite de caractères chargés, défaut `100000`)
   - `AI_PROVIDER` (options: `openai` [défaut], `openrouter`, `ollama`, `groq`)
   - `AI_MODEL` (optionnel)
   - `AI_TEMPERATURE` (optionnel, défaut `0.2` — plus bas = réponses plus précises)
   - `AI_MAX_TOKENS` (optionnel, défaut `512` — longueur max de réponse)
   - Si `AI_PROVIDER=openai`: `OPENAI_API_KEY`
   - Si `AI_PROVIDER=openrouter`: `OPENROUTER_API_KEY` (+ optionnel `OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME`)
   - Si `AI_PROVIDER=groq`: `GROQ_API_KEY`

Exemple (Public + Groq + KB):
```env
TELEGRAM_BOT_TOKEN=123456:ABC...
ATLAS_ALLOW_ALL=true
ATLAS_ADMIN_IDS=123456789
ATLAS_KB_PATH=kb
ATLAS_KB_MAX_CHARS=80000
AI_PROVIDER=groq
GROQ_API_KEY=groq-...
AI_MODEL=llama-3.1-70b-versatile
AI_TEMPERATURE=0.2
AI_MAX_TOKENS=512
```

Placez vos documents métier dans un dossier `kb/` (fichiers `.md` ou `.txt`). Ils seront résumés et injectés au prompt.

## Lancement
```bash
python main.py
```

## Déploiement sur Render
- Le service est configuré comme `web` avec un endpoint `/healthz`.
- Étapes:
  1. Poussez ce repo sur GitHub.
  2. Sur Render, “New +” → “Blueprint” → repo avec `render.yaml`.
  3. Renseignez les variables d’environnement (`TELEGRAM_BOT_TOKEN`, `AI_PROVIDER`, `GROQ_API_KEY`, `ATLAS_ADMIN_IDS`, etc.).
  4. Déployez. Render pingera `/healthz` (200 OK) pour veiller et redémarrer si besoin.
- 24/7: sur plans payants, le service reste actif en continu. Sur free, Render peut stopper l’instance; préférez Starter pour disponibilité constante.

## Endpoints
- `/healthz`: JSON `{ status, uptime_s, tickets_open, faq_cache }`.

## Utilisation
- `/start` et `/help`: informations d'accueil
- Envoyez un message privé au bot; il répondra avec l'IA
- `/ask <question>`: poser une question explicite
- `/id`: afficher votre ID Telegram
- `/reloadkb`: recharger la base de connaissances (admins uniquement)

## Améliorer la précision des réponses
- Baissez `AI_TEMPERATURE` (ex. `0.1`) pour des réponses plus directes.
- Ajoutez vos procédures, FAQ et politiques dans `kb/` (format `.md/.txt`).
- Le bot suit un format: reformulation du problème, 2-5 étapes, puis alternatives.

## Sécurité
- En mode public (`ATLAS_ALLOW_ALL=true`), tout le monde peut accéder au bot. Ajoutez des limites (rate-limit) ou surveillez vos coûts API.
- Le bot refuse l'accès aux utilisateurs dont l'ID n'est pas listé dans `ATLAS_MEMBER_IDS` si le mode public n'est pas activé. 