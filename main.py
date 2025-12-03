import os
import random
import datetime
import logging
from typing import Dict, List

import requests
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

# ------------ BASIC CONFIG -------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Render me env variable me dalna


# ------------ POETS KE NAMES / KEYS -------------

POET_KEYS = {
    "ahmad_faraz": "Ahmad Faraz ❤️‍🔥",
    "jaun_elia": "Jaun Elia 🔥",
    "parveen_shakir": "Parveen Shakir 😘",
    "allama_iqbal": "Allama Iqbal 😌",
    "mix": "Mix Poetry 💫",
}

# Har user + poet ke liye aaj use hue sheron ka record
# structure: used_poetry[user_id][poet_key] = {"date": date, "used_indexes": set([...])}
used_poetry: Dict[int, Dict[str, Dict]] = {}


# ------------ SAMPLE LOCAL POETRY (SAFE / ORIGINAL) -------------
# NOTE:
# Ye sirf sample hai. Real project me tum yahan se replace karke
# apni DB / API se poetry la sakte ho.

LOCAL_POETRY: Dict[str, List[str]] = {
    "ahmad_faraz": [
        "اُنھیں خبر ہی نہیں کتنا یاد رکھتے ہیں\nوہ لوگ ہم کو جو دل سے فراموش کر گئے",
        "میں سوچتا ہوں وہ کتنا قریب تھا دل کے\nکہ اس کے جانے سے دل اپنی جگہ نہیں رہتا",
    ],
    "jaun_elia": [
        "میں خود سے روٹھ کے دن رات بے سبب اُداس\nوہ مجھ سے پوچھ رہا ہے، بتاؤ قصور کیا ہے",
        "عجیب شخص ہوں میں، ہنس کے ٹال دیتا ہوں\nوہ سارے درد جو مر جانے کی طرف لے جائیں",
    ],
    "parveen_shakir": [
        "وہ ایک شخص جو خوابوں میں بھی نہیں آتا\nاسی کے نام پہ آنکھوں میں روشنی رکھنا",
        "محبتوں کے سفر میں یہ احتیاط رہے\nکہ خود کو بھول نہ جائیں کسی کو پا کے بھی",
    ],
    "allama_iqbal": [
        "ستاروں سے آگے جہاں اور بھی ہیں\nابھی عشق کے امتحاں اور بھی ہیں",
        "خودی کو کر بلند اتنا کہ ہر تقدیر سے پہلے\nخدا بندے سے خود پوچھے بتا تیری رضا کیا ہے",
    ],
    # mix ke liye hum sab ko use karenge is key se
}

# ------------ HELPER: INLINE KEYBOARD -------------

def build_main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Ahmad Faraz ❤️‍🔥", callback_data="ahmad_faraz"),
        ],
        [
            InlineKeyboardButton("Jaun Elia 🔥", callback_data="jaun_elia"),
        ],
        [
            InlineKeyboardButton("Parveen Shakir 😘", callback_data="parveen_shakir"),
        ],
        [
            InlineKeyboardButton("Allama Iqbal 😌", callback_data="allama_iqbal"),
        ],
        [
            InlineKeyboardButton("Mix Poetry 💫", callback_data="mix"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ------------ HELPER: TODAY CHECK -------------

def _reset_if_new_day(user_id: int, poet_key: str):
    today = datetime.date.today()
    if user_id not in used_poetry:
        used_poetry[user_id] = {}
    if poet_key not in used_poetry[user_id]:
        used_poetry[user_id][poet_key] = {"date": today, "used_indexes": set()}
    else:
        if used_poetry[user_id][poet_key]["date"] != today:
            # naya din -> reset
            used_poetry[user_id][poet_key] = {"date": today, "used_indexes": set()}


# ------------ HELPER: LOCAL RANDOM POETRY WITH NO REPEAT SAME DAY -------------

def get_local_poetry(user_id: int, poet_key: str) -> str:
    # agar mix hai to sab poets ka combined list
    if poet_key == "mix":
        combined = []
        for key, poems in LOCAL_POETRY.items():
            combined.extend(poems)
        poems = combined
    else:
        poems = LOCAL_POETRY.get(poet_key, [])

    if not poems:
        return "Abhi is shayar ki poetry add nahi ki gayi ❌"

    _reset_if_new_day(user_id, poet_key)

    used_indexes = used_poetry[user_id][poet_key]["used_indexes"]

    # available indexes jinhen aaj tak nahi bheja
    available_indexes = [
        i for i in range(len(poems)) if i not in used_indexes
    ]

    if not available_indexes:
        # sab use ho chuke, iss din me phir allow kar dete hain
        used_poetry[user_id][poet_key]["used_indexes"] = set()
        available_indexes = list(range(len(poems)))

    chosen_index = random.choice(available_indexes)
    used_poetry[user_id][poet_key]["used_indexes"].add(chosen_index)

    return poems[chosen_index]


# ------------ OPTIONAL: INTERNET / API SE POETRY LENA -------------

def get_poetry_from_api(poet_key: str) -> str:
    """
    Yahan pe tum apni API ya website ka endpoint use karo.
    Example:

        resp = requests.get(
            "https://your-domain.com/api/poetry",
            params={"poet": poet_key},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("text", "API ne poetry nahi bheji ❌")

    Abhi ke liye hum isko dummy bana rahe hain aur khali string return karenge.
    """
    return ""  # No external API configured yet


def get_poetry(user_id: int, poet_key: str) -> str:
    """
    Pehle API try karo (agar tumhne set ki ho). Agar khali aaye to local list se do.
    Is tarah tum baad me easily API add kar sakte ho.
    """
    try:
        api_poem = get_poetry_from_api(poet_key)
        if api_poem.strip():
            return api_poem
    except Exception as e:
        logger.error(f"API se poetry laate hue error: {e}")

    # fallback -> local poetry
    return get_local_poetry(user_id, poet_key)


# ------------ HANDLER: /start -------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Poetry Lover"

    # VIP style text
    text = (
        f"Assalamualaikum ❤️‍🔥 **{name}**\n\n"
        "✨ خوش آمدید میرے دل کے بہت قریب VIP Poetry Zone میں ✨\n\n"
        "🖋 *احمد فراز انداز میں چند لفظ:*\n"
        "“تیری یاد ایسے ہے جیسے خاموش سی بارش\n"
        "جو دل کو بھیگائے مگر آواز کہیں نہ آئے”\n\n"
        "👑 *Branding:* **Mudasir Poetry Bot** 👑\n\n"
        "🌸 دعائیں: اللہ تمہاری زندگی کو خوشیوں، محبتوں اور سکون سے بھر دے، "
        "ہر دن تمہارے لیے نیا عشق، نئی امید اور نئی مسکراہٹ لے کر آئے۔ آمین 🤲\n\n"
        "نیچے دیے گئے VIP Menu se apna favourite shayar select karein 👇"
    )

    await update.message.reply_markdown(
        text,
        reply_markup=build_main_menu(),
    )


# ------------ HANDLER: BUTTON CLICKS -------------

async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    poet_key = query.data

    poet_title = POET_KEYS.get(poet_key, "Poetry")
    poem = get_poetry(user.id, poet_key)

    reply_text = (
        f"**{poet_title}**\n\n"
        f"{poem}\n\n"
        "➕ Aur poetry chahiye to dobara button dabayein ya koi aur shayar select karein 💎"
    )

    # edit karne ke bajaye naya message bhejte hain taake menu baar baar rahe
    await query.message.reply_markdown(
        reply_text,
        reply_markup=build_main_menu(),
    )


# ------------ MAIN APP -------------

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env variable set nahi hai!")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_menu_click))

    # simple polling (Render pe worker process ke طور pe chalega)
    application.run_polling()


if __name__ == "__main__":
    main()