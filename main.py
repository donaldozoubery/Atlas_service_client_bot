import os
import logging
import asyncio
from typing import List

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from openai import OpenAI
import httpx
from collections import deque, OrderedDict
import time
import threading
from aiohttp import web


# ---------------------- Configuration & Utils ----------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

BUSINESS_KB: str = ""

# Conversation states for /support
ASK_NAME, ASK_JM, ASK_CATEGORY, ASK_DESCRIPTION, ASK_SCREENSHOT, CONFIRM_SEND = range(6)

# Admin reply conversation states
ADMIN_REPLY_INPUT = range(1)

# In-memory ticket store: ticket_id -> dict
TICKETS: dict[str, dict] = {}

# Map user_id -> last open ticket_id
USER_ACTIVE_TICKET: dict[int, str] = {}

# In-memory per-user short session memory (last N exchanges)
SESSION_HISTORY: dict[int, deque] = {}
SESSION_MAX_MESSAGES = 6

# Simple per-user rate limit (timestamps per command)
RATE_TRACK: dict[tuple[str,int], deque] = {}
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "12"))

# Simple FAQ cache (normalized prompt -> reply)
FAQ_CACHE: OrderedDict[str, str] = OrderedDict()
FAQ_CACHE_MAX = int(os.getenv("FAQ_CACHE_MAX", "200"))
FAQ_MIN_LEN = 12

# Start time for health
START_TIME = time.time()


def get_ai_provider() -> str:
    provider = os.getenv("AI_PROVIDER", "openai").strip().lower()
    if provider not in {"openai", "openrouter", "ollama", "groq"}:
        raise RuntimeError("AI_PROVIDER doit être 'openai', 'openrouter', 'ollama' ou 'groq'")
    return provider


def get_ai_model(provider: str) -> str:
    model = os.getenv("AI_MODEL", "").strip()
    if model:
        return model
    # Defaults per provider
    if provider == "openrouter":
        return "openai/gpt-4o-mini"
    if provider == "ollama":
        return "llama3.1:8b-instruct"
    if provider == "groq":
        return "llama-3.1-70b-versatile"
    return "gpt-4o-mini"


def get_gen_config() -> tuple[float, int]:
    try:
        temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))
    except ValueError:
        temperature = 0.2
    try:
        max_tokens = int(os.getenv("AI_MAX_TOKENS", "512"))
    except ValueError:
        max_tokens = 512
    return temperature, max_tokens


def allow_all_users() -> bool:
    value = os.getenv("ATLAS_ALLOW_ALL", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_admin_ids() -> List[int]:
    raw = os.getenv("ATLAS_ADMIN_IDS", "")
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                logger.warning("ID non valide dans ATLAS_ADMIN_IDS: %s", part)
    return ids


def user_is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids() or user_id in get_allowed_member_ids()


def load_environment() -> None:
    load_dotenv()
    missing: List[str] = []
    # Always required
    for key in ("TELEGRAM_BOT_TOKEN",):
        if not os.getenv(key):
            missing.append(key)

    # Member IDs required only if not public
    if not allow_all_users():
        if not os.getenv("ATLAS_MEMBER_IDS"):
            missing.append("ATLAS_MEMBER_IDS")

    provider = get_ai_provider()
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            missing.append("OPENAI_API_KEY")
    elif provider == "openrouter":
        if not os.getenv("OPENROUTER_API_KEY"):
            missing.append("OPENROUTER_API_KEY")
    elif provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            missing.append("GROQ_API_KEY")
    # ollama: no API key required (local server)

    if missing:
        raise RuntimeError(f"Variables d'environnement manquantes: {', '.join(missing)}")


def get_allowed_member_ids() -> List[int]:
    raw = os.getenv("ATLAS_MEMBER_IDS", "")
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                logger.warning("ID non valide dans ATLAS_MEMBER_IDS: %s", part)
    return ids


def user_is_authorized(user_id: int) -> bool:
    if allow_all_users():
        return True
    return user_id in get_allowed_member_ids()


def build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY manquant")
    return OpenAI(api_key=api_key)


def _read_kb_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Impossible de lire %s: %s", path, e)
        return ""


def load_business_kb() -> tuple[int, int]:
    """Load business KB from ATLAS_KB_PATH (file or directory). Returns (files_count, chars_kept)."""
    global BUSINESS_KB
    kb_path = os.getenv("ATLAS_KB_PATH", "").strip()
    if not kb_path:
        BUSINESS_KB = ""
        return (0, 0)

    max_chars_env = os.getenv("ATLAS_KB_MAX_CHARS", "100000").strip()
    try:
        max_chars = int(max_chars_env)
    except ValueError:
        max_chars = 100000

    collected: List[str] = []
    files_count = 0

    if os.path.isdir(kb_path):
        for root, _dirs, files in os.walk(kb_path):
            for name in files:
                if name.lower().endswith((".md", ".txt")):
                    content = _read_kb_file(os.path.join(root, name))
                    if content:
                        collected.append(f"\n\n# {name}\n{content}")
                        files_count += 1
    elif os.path.isfile(kb_path):
        collected.append(_read_kb_file(kb_path))
        files_count = 1
    else:
        logger.warning("ATLAS_KB_PATH introuvable: %s", kb_path)
        BUSINESS_KB = ""
        return (0, 0)

    kb_full = "\n\n".join(collected)
    if len(kb_full) > max_chars:
        kb_full = kb_full[:max_chars]
    BUSINESS_KB = kb_full
    logger.info("KB chargée: %d fichiers, %d caractères", files_count, len(BUSINESS_KB))
    return (files_count, len(BUSINESS_KB))


async def ask_ai(prompt: str) -> str:
    context_header = "\n\nContexte entreprise (résumé, ne pas répéter mot pour mot):\n"
    kb_section = (context_header + BUSINESS_KB) if BUSINESS_KB else ""

    system_prompt = (
        "Tu es l'assistant de support officiel d'Atlas Signals.\n"
        "Rôles et exigences:\n"
        "- Réponds en français, ton professionnel, empathique, avec quelques emojis adaptés (😊➡️✅❗).\n"
        "- Réponses courtes et actionnables, étapes numérotées si utile.\n"
        "- Toujours: reformuler le problème en 1 ligne, proposer 2-5 étapes concrètes,\n"
        "  et ajouter 'Si ça ne marche pas' avec 1-2 alternatives.\n"
        "- Domaines: accès groupe, abonnement/paiement, signaux/stratégies, usage Telegram.\n"
        "- Hors périmètre: indiquer poliment la limite et proposer une ressource.\n"
        f"{kb_section}"
    )

    # Few-shot examples to steer style
    examples = [
        {
            "role": "user",
            "content": "Je n'arrive pas à accéder au groupe privé Telegram après mon paiement."
        },
        {
            "role": "assistant",
            "content": (
                "Problème: accès au groupe privé après paiement.\n"
                "1) Vérifiez que votre ID Telegram est bien celui fourni lors de l'inscription. 🙂\n"
                "2) Redémarrez l'app Telegram puis réessayez l'invitation. 🔄\n"
                "3) Si vous n'avez pas reçu l'invitation, envoyez votre reçu et votre @username. 🧾\n"
                "Si ça ne marche pas: répondez avec votre ID (/id) pour vérification. ✅"
            )
        },
    ]

    provider = get_ai_provider()
    model = get_ai_model(provider)
    temperature, max_tokens = get_gen_config()

    # prepend session history
    user_id = None
    try:
        # will be filled by caller appending; here we just read from context via global not provided, so skip
        pass
    except Exception:
        pass

    try:
        # FAQ cache hit
        key = prompt.strip().lower()
        if len(key) >= FAQ_MIN_LEN and key in FAQ_CACHE:
            reply = FAQ_CACHE[key]
            # move to end LRU
            FAQ_CACHE.move_to_end(key)
            return reply

        if provider == "openai":
            client = build_openai_client()
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *examples,
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return chat.choices[0].message.content or "Désolé, je n'ai pas de réponse pour l'instant."

        if provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "Atlas Support Bot"),
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *examples,
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=60) as client_http:
                resp = await client_http.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )
                return content or "Désolé, je n'ai pas de réponse pour l'instant."

        if provider == "groq":
            headers = {
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *examples,
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=60) as client_http:
                resp = await client_http.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                if resp.status_code >= 400:
                    text = resp.text
                    try:
                        err = resp.json().get("error")
                    except Exception:
                        err = None
                    logger.error("Groq error %s: %s", resp.status_code, err or text)
                    fallback_model = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
                    if fallback_model and fallback_model != model:
                        payload["model"] = fallback_model
                        resp = await client_http.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )
                return content or "Désolé, je n'ai pas de réponse pour l'instant."

        # ollama (local)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *examples,
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=120) as client_http:
            resp = await client_http.post(f"{base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = (
                (data.get("message") or {}).get("content")
                or (data.get("choices", [{}])[0].get("message", {}).get("content"))
            )
            return content or "Désolé, je n'ai pas de réponse pour l'instant."

        # After success, store in FAQ cache
    except Exception as e:
        logger.exception("Erreur IA (%s): %s", provider, e)
        return "Une erreur est survenue avec le service IA. Réessayez plus tard."


def satisfaction_keyboard() -> InlineKeyboardMarkup:
    site = os.getenv("ATLAS_SITE_URL", "https://atlassignals.site")
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="👍 Résolu", callback_data="SAT_OK"),
            InlineKeyboardButton(text="❗ Besoin d'aide", callback_data="SAT_NEED_HELP"),
        ],
        [InlineKeyboardButton(text="📚 Voir FAQ", url=site)]
    ])


async def satisfaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    # Only acknowledge success here; support flow is handled by ConversationHandler entry point
    if query.data == "SAT_OK":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Super, ravi d'avoir pu aider ! 😊")


# ---------------------- Handlers Telegram ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    if not user_is_authorized(user.id):
        await update.effective_message.reply_text(
            "Bonjour 👋! Ce bot est réservé aux membres Atlas Signals. "
            "Si vous pensez que c'est une erreur, contactez le support."
        )
        return

    await update.effective_message.reply_text(
        "Bienvenue sur le bot de support Atlas Signals ✨\n"
        "- Envoyez-moi un message pour obtenir de l'aide.\n"
        "- Utilisez /help pour voir les commandes.\n"
        "- Utilisez /ask <question> pour poser une question à l'IA.\n"
        "- Utilisez /id pour connaître votre ID Telegram.\n"
        "- Utilisez /support pour créer un ticket si besoin."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Commandes disponibles:\n"
        "/start - message d'accueil\n"
        "/help - aide\n"
        "/ask <question> - demander à l'IA\n"
        "/id - afficher votre ID Telegram\n"
        "/support - créer un ticket si le problème persiste\n"
        "/reloadkb - recharger le contexte entreprise (admin)"
    )


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    await update.effective_message.reply_text(f"Votre ID Telegram: {user.id}")


async def reload_kb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    if not user_is_admin(user.id):
        await update.effective_message.reply_text("Accès réservé aux admins.")
        return
    files, chars = load_business_kb()
    await update.effective_message.reply_text(
        f"KB rechargée: {files} fichier(s), {chars} caractères."
    )


# Support conversation flow
async def support_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user_is_authorized(user.id):
        await update.effective_message.reply_text("Accès refusé.")
        return ConversationHandler.END
    # If user has active open ticket, guide them to reply on it
    tid = USER_ACTIVE_TICKET.get(user.id)
    if tid and TICKETS.get(tid, {}).get("status") != "closed":
        await update.effective_message.reply_text(
            f"Vous avez déjà un ticket ouvert: #{tid}.\n"
            f"Répondez directement à un message du support ou utilisez /reply <votre message>."
        )
        return ConversationHandler.END
    await update.effective_message.reply_text("👍 D'accord, comment vous appelez-vous ?")
    return ASK_NAME

async def support_entry_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Called when user clicks "Besoin d'aide" button
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        update = Update(update.update_id, message=query.message)  # ensure we can reply
    user = update.effective_user
    if user:
        tid = USER_ACTIVE_TICKET.get(user.id)
        if tid and TICKETS.get(tid, {}).get("status") != "closed":
            await query.message.reply_text(
                f"Vous avez déjà un ticket ouvert: #{tid}.\n"
                f"Répondez directement au dernier message du support ou utilisez /reply <votre message>."
            )
            return ConversationHandler.END
    return await support_entry(update, context)


async def support_ask_jm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = (update.effective_message.text or "").strip()
    await update.effective_message.reply_text("Avez-vous un numéro de compte JM lié ? (sinon tapez 'non')")
    return ASK_JM


async def support_ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["jm"] = (update.effective_message.text or "").strip()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Accès / Invitation", callback_data="CAT_ACCESS")],
        [InlineKeyboardButton("Paiement / Facturation", callback_data="CAT_PAYMENT")],
        [InlineKeyboardButton("Signaux / Trading", callback_data="CAT_SIGNALS")],
        [InlineKeyboardButton("Autre", callback_data="CAT_OTHER")],
    ])
    await update.effective_message.reply_text("Quelle est la catégorie du problème ?", reply_markup=kb)
    return ASK_CATEGORY


async def support_ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mapping = {
        "CAT_ACCESS": "Accès / Invitation",
        "CAT_PAYMENT": "Paiement / Facturation",
        "CAT_SIGNALS": "Signaux / Trading",
        "CAT_OTHER": "Autre",
    }
    context.user_data["category"] = mapping.get(query.data, "Autre")
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("Merci 🙏. Décrivez brièvement le problème (avec détails utiles).")
    return ASK_DESCRIPTION


async def support_ask_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = (update.effective_message.text or "").strip()
    # Auto-categorize if 'Autre'
    if context.user_data.get("category") == "Autre":
        desc = context.user_data["description"]
        lang = detect_language(desc)
        hint_prompt = (
            "Catégorise ce problème parmi: Accès / Invitation, Paiement / Facturation, "
            "Signaux / Trading, Autre. Réponds uniquement par le libellé.\n\n" + desc
        )
        cat = await ask_ai(hint_prompt)
        if cat:
            context.user_data["category"] = (cat.split("\n")[0] or cat).strip()
    await update.effective_message.reply_text("Pouvez-vous joindre une capture d'écran ? (envoyez une image ou tapez 'skip') 🖼️")
    return ASK_SCREENSHOT


async def support_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.photo:
        # Save file_id for later sending to admins
        context.user_data["photo_file_id"] = update.effective_message.photo[-1].file_id
    else:
        # text like 'skip'
        pass
    user = update.effective_user
    preview = (
        f"Nom: {context.user_data.get('name','')}\n"
        f"JM: {context.user_data.get('jm','')}\n"
        f"ID Telegram: {user.id}\n"
        f"Catégorie: {context.user_data.get('category','')}\n"
        f"Description: {context.user_data.get('description','')}\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Envoyer ✅", callback_data="TICKET_SEND")]])
    await update.effective_message.reply_text("Aperçu du ticket:\n" + preview, reply_markup=kb)
    return CONFIRM_SEND


async def support_send_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    user = update.effective_user
    # Guard: prevent duplicate if open exists
    existing_tid = USER_ACTIVE_TICKET.get(user.id)
    if existing_tid and TICKETS.get(existing_tid, {}).get("status") != "closed":
        await query.message.reply_text(
            f"Un ticket est déjà ouvert: #{existing_tid}.\n"
            f"Répondez avec /reply ou au message du support."
        )
        context.user_data.clear()
        return ConversationHandler.END
    # Create ticket id
    ticket_id = str(int(time.time() * 1000))
    TICKETS[ticket_id] = {
        "user_id": user.id,
        "name": context.user_data.get('name',''),
        "jm": context.user_data.get('jm',''),
        "category": context.user_data.get('category',''),
        "description": context.user_data.get('description',''),
        "photo_file_id": context.user_data.get('photo_file_id'),
        "status": "open",
        "created_at": time.time(),
        "first_response_at": None,
        "assignee": None,
        "csat": None,
        "csat_note": None,
    }
    # mark as user's active open ticket
    USER_ACTIVE_TICKET[user.id] = ticket_id
    text = (
        f"🆘 Ticket #{ticket_id}\n"
        f"Nom: {TICKETS[ticket_id]['name']}\n"
        f"JM: {TICKETS[ticket_id]['jm']}\n"
        f"Client ID: {user.id}\n"
        f"Catégorie: {TICKETS[ticket_id]['category']}\n"
        f"Description: {TICKETS[ticket_id]['description']}\n"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Répondre ✍️", callback_data=f"ADM_REPLY:{ticket_id}"),
            InlineKeyboardButton("Clore ✅", callback_data=f"ADM_CLOSE:{ticket_id}"),
        ]
    ])
    admin_group = os.getenv("ADMIN_GROUP_ID", "").strip()
    if admin_group:
        try:
            await context.bot.send_message(chat_id=int(admin_group), text=text, reply_markup=kb)
            if TICKETS[ticket_id]["photo_file_id"]:
                await context.bot.send_photo(chat_id=int(admin_group), photo=TICKETS[ticket_id]["photo_file_id"], caption=f"Ticket #{ticket_id}")
        except Exception as e:
            logger.warning("Envoi au groupe admin échoué: %s", e)
    else:
        admin_ids = get_admin_ids()
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=text, reply_markup=kb)
                if TICKETS[ticket_id]["photo_file_id"]:
                    await context.bot.send_photo(chat_id=admin_id, photo=TICKETS[ticket_id]["photo_file_id"], caption=f"Ticket #{ticket_id}")
            except Exception as e:
                logger.warning("Envoi au admin %s échoué: %s", admin_id, e)
    await query.message.reply_text(
        f"Merci ✅😊 Votre demande a été envoyée à un administrateur.\n"
        f"Votre numéro de ticket: #{ticket_id}. Conservez-le pour le suivi."
    )
    context.user_data.clear()
    return ConversationHandler.END


# Admin reply handlers
async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    await query.answer()
    _, ticket_id = (query.data or "").split(":", 1)
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        await query.message.reply_text("Ticket introuvable ou déjà clos.")
        return ConversationHandler.END
    context.user_data["reply_ticket_id"] = ticket_id
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Réponse pour ticket #{ticket_id} — tapez votre message:" )
    return ADMIN_REPLY_INPUT


async def admin_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticket_id = context.user_data.get("reply_ticket_id")
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        await update.effective_message.reply_text("Ticket introuvable ou déjà clos.")
        return ConversationHandler.END
    reply_text = update.effective_message.text or ""
    # mark first_response_at
    if ticket.get("first_response_at") is None:
        ticket["first_response_at"] = time.time()
        ticket["status"] = "pending"
    # Send to customer
    try:
        await context.bot.send_message(chat_id=ticket["user_id"], text=f"📣 Réponse du support (ticket #{ticket_id}):\n{reply_text}")
        await update.effective_message.reply_text("Réponse envoyée au client ✅")
    except Exception as e:
        await update.effective_message.reply_text(f"Échec d'envoi au client: {e}")
    return ConversationHandler.END


async def admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    _, ticket_id = (query.data or "").split(":", 1)
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        await query.message.reply_text("Ticket introuvable ou déjà clos.")
        return
    ticket["status"] = "closed"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Ticket #{ticket_id} clôturé ✅")
    # clear active map if matches
    if USER_ACTIVE_TICKET.get(ticket["user_id"]) == ticket_id:
        USER_ACTIVE_TICKET.pop(ticket["user_id"], None)
    # Notify client about closure
    try:
        await context.bot.send_message(chat_id=ticket["user_id"], text=f"✅ Votre ticket #{ticket_id} a été clôturé. Si besoin, vous pouvez créer un nouveau ticket avec /support.")
    except Exception as e:
        logger.warning("Notification close client échouée: %s", e)
    # Ask CSAT to customer
    try:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐", callback_data=f"CSAT:{ticket_id}:1"), InlineKeyboardButton("⭐⭐", callback_data=f"CSAT:{ticket_id}:2"), InlineKeyboardButton("⭐⭐⭐", callback_data=f"CSAT:{ticket_id}:3")],
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"CSAT:{ticket_id}:4"), InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"CSAT:{ticket_id}:5")],
        ])
        await context.bot.send_message(chat_id=ticket["user_id"], text=f"Merci pour votre patience 🙏\nÉvaluez notre aide pour le ticket #{ticket_id}:", reply_markup=kb)
    except Exception as e:
        logger.warning("CSAT non envoyé: %s", e)

async def csat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    _, ticket_id, score = (query.data or "").split(":", 2)
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        return
    ticket["csat"] = int(score)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("Merci pour votre retour ⭐")

# Admin commands
async def tickets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_admin(update.effective_user.id):
        return
    lines = []
    for tid, t in list(TICKETS.items())[-50:]:
        age = int(time.time() - t.get("created_at", time.time()))
        lines.append(f"#{tid} | {t['status']} | @{t.get('assignee','-')} | {t['category']} | {age}s")
    await update.effective_message.reply_text("\n".join(lines) or "Aucun ticket")

async def ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_admin(update.effective_user.id):
        return
    tid = (context.args[0] if context.args else "").strip()
    t = TICKETS.get(tid)
    if not t:
        await update.effective_message.reply_text("Ticket introuvable")
        return
    age = int(time.time() - t.get("created_at", time.time()))
    frt = (t.get("first_response_at") and int(t["first_response_at"] - t["created_at"])) or "-"
    await update.effective_message.reply_text(
        f"Ticket #{tid}\nStatut: {t['status']}\nAssignee: {t.get('assignee','-')}\nCatégorie: {t['category']}\nFRT: {frt}s\nÂge: {age}s\nClient: {t['user_id']}\nNom: {t['name']}\nJM: {t['jm']}\nDesc: {t['description']}"
    )

async def ticket_close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_admin(update.effective_user.id):
        return
    tid = (context.args[0] if context.args else "").strip()
    if not tid or tid not in TICKETS:
        await update.effective_message.reply_text("Usage: /close <ticket_id>")
        return
    # simulate button close
    class DummyQ: pass
    q = DummyQ(); q.data = f"ADM_CLOSE:{tid}"; q.message = update.effective_message
    await admin_close_ticket(Update(update.update_id, callback_query=None), context)  # no-op; we call directly below
    # directly close
    TICKETS[tid]["status"] = "closed"
    await update.effective_message.reply_text(f"Ticket #{tid} clôturé ✅")

async def ticket_assign_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_is_admin(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text("Usage: /assign <ticket_id> <admin_id>")
        return
    tid, aid = context.args[0], context.args[1]
    if tid not in TICKETS:
        await update.effective_message.reply_text("Ticket introuvable")
        return
    TICKETS[tid]["assignee"] = aid
    await update.effective_message.reply_text(f"Ticket #{tid} assigné à {aid}")

# Client replies to open ticket
async def client_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not user_is_authorized(user.id):
        return
    if not check_rate_limit(user.id, "reply"):
        await update.effective_message.reply_text("Veuillez patienter avant une nouvelle réponse ⏳")
        return
    # ticket id optional
    tid = (context.args[0] if context.args else "").strip()
    if not tid:
        tid = USER_ACTIVE_TICKET.get(user.id, "")
    if not tid or tid not in TICKETS:
        await update.effective_message.reply_text("Aucun ticket ouvert trouvé. Utilisez /support pour en créer un." )
        return
    t = TICKETS[tid]
    if t.get("status") == "closed":
        await update.effective_message.reply_text("Ce ticket est déjà clôturé. Utilisez /support pour en créer un nouveau." )
        return
    # message after command args
    reply_text = " ".join(context.args[1:]).strip() if context.args else ""
    if not reply_text:
        await update.effective_message.reply_text("Usage: /reply <ticket_id?> <votre message>")
        return
    # forward to admins or group
    admin_group = os.getenv("ADMIN_GROUP_ID", "").strip()
    fwd = f"🔁 Réponse client pour ticket #{tid}\nClient {user.id}: {reply_text}"
    try:
        if admin_group:
            await context.bot.send_message(chat_id=int(admin_group), text=fwd)
        else:
            for admin_id in get_admin_ids():
                await context.bot.send_message(chat_id=admin_id, text=fwd)
    except Exception as e:
        logger.warning("Transmission de la réponse au staff échouée: %s", e)
    await update.effective_message.reply_text("Message envoyé au support ✅")

# Language detection heuristic
FR_HINTS = {"bonjour","svp","merci","problème","paiement","accès","s'il","ça","été","é","à","è","ù"}

def detect_language(text: str) -> str:
    t = (text or "").lower()
    score_fr = sum(1 for w in FR_HINTS if w in t)
    return "fr" if score_fr >= 1 else "en"

# Rate limiting

def check_rate_limit(user_id: int, command: str) -> bool:
    key = (command, user_id)
    dq = RATE_TRACK.setdefault(key, deque())
    now = time.time()
    # drop older than 60s
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_PER_MIN:
        return False
    dq.append(now)
    return True

# Session memory helper

def append_history(user_id: int, role: str, content: str) -> None:
    dq = SESSION_HISTORY.setdefault(user_id, deque(maxlen=SESSION_MAX_MESSAGES))
    dq.append({"role": role, "content": content})


async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not user_is_authorized(user.id):
        await update.effective_message.reply_text(
            "Accès refusé. Ce bot est réservé aux membres Atlas Signals."
        )
        return

    if not check_rate_limit(user.id, "ask"):
        await update.effective_message.reply_text("Veuillez patienter quelques instants avant une nouvelle question ⏳")
        return

    question = " ".join(context.args).strip()
    if not question:
        await update.effective_message.reply_text(
            "Utilisation: /ask <votre question>"
        )
        return

    lang = detect_language(question)
    append_history(user.id, "user", question)
    await update.effective_message.chat.send_action(action=ChatAction.TYPING)
    reply = await ask_ai(question)
    append_history(user.id, "assistant", reply)
    # add to cache
    key = question.strip().lower()
    if len(key) >= FAQ_MIN_LEN:
        FAQ_CACHE[key] = reply
        if len(FAQ_CACHE) > FAQ_CACHE_MAX:
            FAQ_CACHE.popitem(last=False)
    await update.effective_message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, reply_markup=satisfaction_keyboard())


async def inbound_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    if not user_is_authorized(user.id):
        await message.reply_text(
            "Accès refusé. Ce bot est réservé aux membres Atlas Signals."
        )
        return

    # If user replies to a support message containing a ticket id, route as a client reply
    try:
        import re
        if message.reply_to_message and message.reply_to_message.text:
            m = re.search(r"ticket\s*#(\d+)", message.reply_to_message.text, flags=re.IGNORECASE)
            if m:
                tid = m.group(1)
                t = TICKETS.get(tid)
                if t and t.get("status") != "closed":
                    admin_group = os.getenv("ADMIN_GROUP_ID", "").strip()
                    fwd = f"🔁 Réponse client pour ticket #{tid}\nClient {user.id}: {message.text}"
                    try:
                        if admin_group:
                            await context.bot.send_message(chat_id=int(admin_group), text=fwd)
                        else:
                            for admin_id in get_admin_ids():
                                await context.bot.send_message(chat_id=admin_id, text=fwd)
                    except Exception as e:
                        logger.warning("Transmission de la réponse au staff échouée: %s", e)
                    await message.reply_text("Message envoyé au support ✅")
                    return
    except Exception as e:
        logger.debug("Reply-to routing non appliqué: %s", e)

    prompt = message.text or ""
    if not prompt:
        await message.reply_text("Envoyez un message texte pour obtenir de l'aide.")
        return

    if not check_rate_limit(user.id, "msg"):
        await message.reply_text("Veuillez patienter quelques instants avant un nouveau message ⏳")
        return

    append_history(user.id, "user", prompt)
    await message.chat.send_action(action=ChatAction.TYPING)
    reply = await ask_ai(prompt)
    append_history(user.id, "assistant", reply)
    key = prompt.strip().lower()
    if len(key) >= FAQ_MIN_LEN:
        FAQ_CACHE[key] = reply
        if len(FAQ_CACHE) > FAQ_CACHE_MAX:
            FAQ_CACHE.popitem(last=False)
    await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, reply_markup=satisfaction_keyboard())


# ---------------------- Health Server ----------------------
async def handle_health(request: web.Request) -> web.Response:
    uptime = int(time.time() - START_TIME)
    payload = {
        "status": "ok",
        "uptime_s": uptime,
        "tickets_open": sum(1 for t in TICKETS.values() if t.get("status") != "closed"),
        "faq_cache": len(FAQ_CACHE),
    }
    return web.json_response(payload)


def run_health_server() -> None:
    try:
        app = web.Application()
        app.router.add_get("/healthz", handle_health)
        port = int(os.getenv("PORT", "8000"))
        web.run_app(app, port=port)
    except Exception as e:
        logger.warning("Health server stopped: %s", e)


# ---------------------- Entrée Programme ----------------------
def main() -> None:
    load_environment()
    # Preload KB if configured
    load_business_kb()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(token).build()

    # Start health server in background
    threading.Thread(target=run_health_server, daemon=True).start()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("ask", ask_cmd))
    application.add_handler(CommandHandler("id", id_cmd))
    application.add_handler(CommandHandler("reloadkb", reload_kb_cmd))

    # Support conversation
    support_conv = ConversationHandler(
        entry_points=[
            CommandHandler("support", support_entry),
            CallbackQueryHandler(support_entry_from_button, pattern="^SAT_NEED_HELP$"),
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_ask_jm)],
            ASK_JM: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_ask_category)],
            ASK_CATEGORY: [CallbackQueryHandler(support_ask_description, pattern="^CAT_")],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_ask_screenshot)],
            ASK_SCREENSHOT: [
                MessageHandler(filters.PHOTO, support_confirm),
                MessageHandler(filters.TEXT & ~filters.COMMAND, support_confirm),
            ],
            CONFIRM_SEND: [CallbackQueryHandler(support_send_ticket, pattern="^TICKET_SEND$")],
        },
        fallbacks=[CommandHandler("support", support_entry)],
        allow_reentry=True,
    )
    application.add_handler(support_conv)

    # Admin reply conversation
    admin_reply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_reply_start, pattern="^ADM_REPLY:")],
        states={
            ADMIN_REPLY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_send)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    application.add_handler(admin_reply_conv)

    # Close ticket handler
    application.add_handler(CallbackQueryHandler(admin_close_ticket, pattern="^ADM_CLOSE:"))

    # CSAT handler
    application.add_handler(CallbackQueryHandler(csat_handler, pattern="^CSAT:"))

    # Admin commands
    application.add_handler(CommandHandler("tickets", tickets_list))
    application.add_handler(CommandHandler("ticket", ticket_detail))
    application.add_handler(CommandHandler("close", ticket_close_cmd))
    application.add_handler(CommandHandler("assign", ticket_assign_cmd))
    application.add_handler(CommandHandler("reply", client_reply))

    # Satisfaction buttons handler (only SAT_OK here)
    application.add_handler(CallbackQueryHandler(satisfaction_callback, pattern="^SAT_OK$"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, inbound_message))

    logger.info("Bot démarré. En attente de messages...")
    application.run_polling()


if __name__ == "__main__":
    main()
