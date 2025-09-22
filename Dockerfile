FROM python:3.11-slim

# Empêcher Python d'écrire des .pyc et buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installer dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer deps Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Exposer le port health (optionnel, Fly ne l'utilisera pas pour un worker)
EXPOSE 8000

# Commande par défaut (overridable par fly.toml process group)
CMD ["python", "main.py"] 