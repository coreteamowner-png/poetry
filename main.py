import os
import re
import random
import datetime
import logging
from typing import Dict, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------- BASIC CONFIG ----------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Render me env vars me set karna

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

POET_KEYS = {
    "ahmad_faraz": "Ahmad Faraz ❤️‍🔥",
    "jaun_elia": "Jaun Elia 🔥",
    "parveen_shakir": "Parveen Shakir 😘",
    "allama_iqbal": "Allama Iqbal 😌",
    "mix": "Mix Poetry 💫",
}

# user_id -> poet_key -> {date, used_indexes}
used_poetry: Dict[int, Dict[str, Dict]] = {}

# ---------- CLEANING / FILTERING ----------

# ASCII digits + Urdu digits + special mark "؍"
UNWANTED_PATTERN = re.compile(r"[0-9۰-۹؍]+")


def clean_block(text: str) -> str:
    """
    Faltu numbers 1؍ 2؍ etc hata deta hai,
    extra spaces remove karta hai,
    khali lines hata deta hai.
    """
    # remove numbers & "؍"
    text = UNWANTED_PATTERN.sub("", text)

    # Normalize spaces inside lines
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # multiple spaces -> single space
        line = re.sub(r"\s+", " ", line)
        lines.append(line)

    cleaned = "\n".join(lines).strip()
    return cleaned


def load_poetry_from_files() -> List[str]:
    """
    Dono files se shayri load karta hai,
    blank line ke basis par shayr split karta hai,
    clean karta hai,
    duplicate shayr hata deta hai.
    """
    all_blocks: List[str] = []

    filenames = [
        "urdu_shayri_2000.txt",
        "kashida_deep_urdu_shayari_1000.txt",
    ]

    for fname in filenames:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            logger.warning(f"Poetry file missing: {path}")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            continue

        # split on blank lines: ek shair == 2–4 lines ka block
        raw_blocks = re.split(r"\n\s*\n", raw)
        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue
            cleaned = clean_block(block)
            if len(cleaned) < 10:
                # bohat chhota / bekaar block -> skip
                continue
            all_blocks.append(cleaned)

    # remove exact duplicates while preserving order
    unique_blocks: List[str] = []
    seen = set()
    for b in all_blocks:
        if b not in seen:
            seen.add(b)
            unique_blocks.append(b)

    logger.info(f"Loaded {len(unique_blocks)} unique poetry blocks.")
    return unique_blocks


ALL_POETRY: List[str] = load_poetry_from_files()


# ---------- MENU UI ----------

def build_main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Ahmad Faraz ❤️‍🔥", callback_data="ahmad_faraz")],
        [InlineKeyboardButton("Jaun Elia 🔥", callback_data="jaun_elia")],
        [InlineKeyboardButton("Parveen Shakir 😘", callback_data="parveen_shakir")],
        [InlineKeyboardButton("Allama Iqbal 😌", callback_data="allama_iqbal")],
        [InlineKeyboardButton("Mix Poetry 💫", callback_data="mix")],
    ]
    return InlineKeyboardMarkup(buttons)


# ---------- SAME DIN REPEAT NA HO ----------

def _reset_if_new_day(user_id: int, poet_key: str):
    today = datetime.date.today()
    if user_id not in used_poetry:
        used_poetry[user_id] = {}

    if poet_key not in used_poetry[user_id]:
        used_poetry[user_id][poet_key] = {"date": today, "used_indexes": set()}
    else:
        if used_poetry[user_id][poet_key]["date"] != today:
            # Naya din -> reset
            used_poetry[user_id][poet_key] = {"date": today, "used_indexes": set()}


def get_poetry(user_id: int, poet_key: str) -> str:
    """
    Abhi hum sab options ke liye same ALL_POETRY use kar rahe hain,
    bas user + poet_key ke hisaab se repeat control ho raha hai.
    """
    if not ALL_POETRY:
        return "❌ Abhi poetry load nahi hui (files check karein)."

    _reset_if_new_day(user_id, poet_key)

    used_indexes = used_poetry[user_id][poet_key]["used_indexes"]
    total = len(ALL_POETRY)

    # indexes jo aaj abhi tak use nahi hue
    available_indexes = [i for i in range(total) if i not in used_indexes]

    if not available_indexes:
        # is din sab bhej chuke -> reset karo aur phir se chalao
        used_poetry[user_id][poet_key]["used_indexes"] = set()
        available_indexes = list(range(total))

    idx = random.choice(available_indexes)
    used_poetry[user_id][poet_key]["used_indexes"].add(idx)

    return ALL_POETRY[idx]


# ---------- /start HANDLER ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Poetry Lover"

    text = (
        f"Assalamualaikum ❤️‍🔥 **{name}**\n\n"
        "✨ خوش آمدید میرے دل کے VIP Poetry Zone میں ✨\n\n"
        "🖋 *احمد فراز انداز میں چند لفظ:*\n"
        "“تیری یاد ایسے ہے جیسے خاموش سی بارش\n"
        "جو دل کو بھیگائے مگر آواز کہیں نہ آئے”\n\n"
        "👑 *Branding:* **Mudasir Poetry Bot** 👑\n\n"
        "🌸 دعا: اللہ تمہاری زندگی کو خوشیوں، محبتوں اور سکون سے بھر دے۔ آمین 🤲\n\n"
        "نیچے دیا گیا VIP Menu استعمال کریں اور دل کی دنیا کو روشن کریں 👇"
    )

    await update.message.reply_markdown(
        text,
        reply_markup=build_main_menu(),
    )


# ---------- BUTTON HANDLER ----------

async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    poet_key = query.data
    poet_title = POET_KEYS.get(poet_key, "Poetry")

    poem = get_poetry(user.id, poet_key)

    reply_text = (
        "✦──────❖──────✦\n"
        f"**{poet_title}**\n"
        "✦──────❖──────✦\n\n"
        f"{poem}\n\n"
        "💎 Aur poetry chahiye ho to yahi button dobara dabayein "
        "ya koi aur shayar select karein۔"
    )

    await query.message.reply_markdown(
        reply_text,
        reply_markup=build_main_menu(),
    )


# ---------- MAIN APP ----------

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env variable set nahi hai! (Render env vars me BOT_TOKEN set karein)")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_menu_click))

    application.run_polling()


if __name__ == "__main__":
    main()
