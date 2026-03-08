import os
import re
import requests
from telebot import TeleBot, types
from flask import Flask, request
from config import API_TOKEN, ADMIN_GROUP_ID

bot = TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

RENDER_URL = "https://bott-2-jpt2.onrender.com"
thread_history = {}
admin_to_user_map = {}
new_users = set()
user_state = {}   # አዲስ: ተጠቃሚ በቨርስ ፍለጋ ሁኔታ ላይ እንዳለ ለማወቅ

# ================================
# የመጽሐፍ ቅዱስ ጥቅስ ፍለጋ ለማጣቀሻ ማጣቀሻ (Amharic + English)
# ================================
BOOK_MAP = {
    # Old Testament (English + አማርኛ)
    "genesis": "GEN", "gen": "GEN", "ዘፍጥረት": "GEN", "ኦሪት ዘፍጥረት": "GEN",
    "exodus": "EXO", "exo": "EXO", "ዘጸአት": "EXO",
    "leviticus": "LEV", "lev": "LEV", "ዘሌዋውያን": "LEV",
    "numbers": "NUM", "num": "NUM", "ዘነሙስ": "NUM",
    "deuteronomy": "DEU", "deu": "DEU", "ዘዳግም": "DEU",
    "joshua": "JOS", "jos": "JOS", "ኢያሱ": "JOS",
    "judges": "JDG", "jdg": "JDG", "መናገድ": "JDG",
    "ruth": "RUT", "rut": "RUT", "ሩት": "RUT",
    "1 samuel": "1SA", "1samuel": "1SA", "1sa": "1SA", "1 ሳሙኤል": "1SA",
    "2 samuel": "2SA", "2samuel": "2SA", "2sa": "2SA", "2 ሳሙኤል": "2SA",
    "1 kings": "1KI", "1kings": "1KI", "1ki": "1KI", "1 ነገሥት": "1KI",
    "2 kings": "2KI", "2kings": "2KI", "2ki": "2KI", "2 ነገሥት": "2KI",
    "1 chronicles": "1CH", "1chronicles": "1CH", "1ch": "1CH", "1 ዜና መዋዕል": "1CH",
    "2 chronicles": "2CH", "2chronicles": "2CH", "2ch": "2CH", "2 ዜና መዋዕል": "2CH",
    "ezra": "EZR", "ezr": "EZR", "ኤዝራ": "EZR",
    "nehemiah": "NEH", "neh": "NEH", "ነህምያ": "NEH",
    "esther": "EST", "est": "EST", "አስቴር": "EST",
    "job": "JOB", "ኢዮብ": "JOB",
    "psalms": "PSA", "psalm": "PSA", "psa": "PSA", "መዝሙር": "PSA",
    "proverbs": "PRO", "pro": "PRO", "መጻሕፍተ ምሳሌ": "PRO",
    "ecclesiastes": "ECC", "ecc": "ECC", "መክብብ": "ECC",
    "song of solomon": "SNG", "song": "SNG", "sng": "SNG", "መኃልየ መኃልይ": "SNG",
    "isaiah": "ISA", "isa": "ISA", "ኢሳይያስ": "ISA",
    "jeremiah": "JER", "jer": "JER", "ኤርምያስ": "JER",
    "lamentations": "LAM", "lam": "LAM", "አስቃቅ": "LAM",
    "ezekiel": "EZK", "ezk": "EZK", "ኤዜክኤል": "EZK",
    "daniel": "DAN", "dan": "DAN", "ዳንኤል": "DAN",
    "hosea": "HOS", "hos": "HOS", "ሆሴዕ": "HOS",
    "joel": "JOL", "jol": "JOL", "ኢዮኤል": "JOL",
    "amos": "AMO", "amo": "AMO", "አሞጽ": "AMO",
    "obadiah": "OBA", "oba": "OBA", "ኦባድያ": "OBA",
    "jonah": "JON", "jon": "JON", "ዮናስ": "JON",
    "micah": "MIC", "mic": "MIC", "ሚክያስ": "MIC",
    "nahum": "NAM", "nam": "NAM", "ናሆም": "NAM",
    "habakkuk": "HAB", "hab": "HAB", "ዕንባቆም": "HAB",
    "zephaniah": "ZEP", "zep": "ZEP", "ሶፎንያስ": "ZEP",
    "haggai": "HAG", "hag": "HAG", "ሐጌ": "HAG",
    "zechariah": "ZEC", "zec": "ZEC", "ዘካርያስ": "ZEC",
    "malachi": "MAL", "mal": "MAL", "ማላኪ": "MAL",

    # New Testament
    "matthew": "MAT", "mat": "MAT", "ማቴዎስ": "MAT",
    "mark": "MRK", "mrk": "MRK", "ማርቆስ": "MRK",
    "luke": "LUK", "luk": "LUK", "ሉቃስ": "LUK",
    "john": "JHN", "jhn": "JHN", "ዮሐንስ": "JHN",
    "acts": "ACT", "act": "ACT", "የሐዋርያት ሥራ": "ACT",
    "romans": "ROM", "rom": "ROM", "ሮሜ": "ROM",
    "1 corinthians": "1CO", "1corinthians": "1CO", "1co": "1CO", "1 ቆሮንቶስ": "1CO",
    "2 corinthians": "2CO", "2corinthians": "2CO", "2co": "2CO", "2 ቆሮንቶስ": "2CO",
    "galatians": "GAL", "gal": "GAL", "ገላትያ": "GAL",
    "ephesians": "EPH", "eph": "EPH", "ኤፌሶን": "EPH",
    "philippians": "PHP", "php": "PHP", "ፊልጵስዩስ": "PHP",
    "colossians": "COL", "col": "COL", "ቆላስይ": "COL",
    "1 thessalonians": "1TH", "1thessalonians": "1TH", "1th": "1TH", "1 ተሰሎንቄ": "1TH",
    "2 thessalonians": "2TH", "2thessalonians": "2TH", "2th": "2TH", "2 ተሰሎንቄ": "2TH",
    "1 timothy": "1TI", "1timothy": "1TI", "1ti": "1TI", "1 ጢሞቴዎስ": "1TI",
    "2 timothy": "2TI", "2timothy": "2TI", "2ti": "2TI", "2 ጢሞቴዎስ": "2TI",
    "titus": "TIT", "tit": "TIT", "ጢቶ": "TIT",
    "philemon": "PHM", "phm": "PHM", "ፊልሞን": "PHM",
    "hebrews": "HEB", "heb": "HEB", "ዕብራይስጥ": "HEB",
    "james": "JAM", "jam": "JAM", "ያዕቆብ": "JAM",
    "1 peter": "1PE", "1peter": "1PE", "1pe": "1PE", "1 ጴጥሮስ": "1PE",
    "2 peter": "2PE", "2peter": "2PE", "2pe": "2PE", "2 ጴጥሮስ": "2PE",
    "1 john": "1JN", "1john": "1JN", "1jn": "1JN", "1 ዮሐንስ": "1JN",
    "2 john": "2JN", "2john": "2JN", "2jn": "2JN", "2 ዮሐንስ": "2JN",
    "3 john": "3JN", "3john": "3JN", "3jn": "3JN", "3 ዮሐንስ": "3JN",
    "jude": "JUD", "jud": "JUD", "ይሁዳ": "JUD",
    "revelation": "REV", "rev": "REV", "ራእይ": "REV",
}

def parse_bible_reference(ref: str):
    """የተጠቃሚ ግቤትን (John 3:16 ወይም ዮሐንስ 3:16) ወደ book_id, chapter, verse ይቀይራል"""
    if not ref:
        return None
    # ትክክለኛ ማጣቀሻ ለመያዝ (1 John 3:16 ወይም ዮሐንስ 3:16)
    match = re.match(r'(?i)^(.*?)\s+(\d+)(?::\s*(\d+))?$', ref.strip())
    if not match:
        return None
    book_str = match.group(1).strip().lower()
    chapter = int(match.group(2))
    verse_str = match.group(3)
    if not verse_str:
        return None
    verse = int(verse_str)

    # ቀጥታ ማጣቀሻ
    book_id = BOOK_MAP.get(book_str)
    if book_id:
        return book_id, chapter, verse

    # ተጨማሪ ሙከራ (ክፍተት አስወግድ)
    book_str2 = re.sub(r'\s+', '', book_str).replace('of', '')
    book_id = BOOK_MAP.get(book_str2)
    if book_id:
        return book_id, chapter, verse

    return None

def search_bible_verse(ref: str):
    """Amharic ጥቅስ ከነጻ API ያገኛል (bible-api-kappa.vercel.app)"""
    parsed = parse_bible_reference(ref)
    if not parsed:
        return None

    book_id, chapter, verse_num = parsed
    url = f"https://bible-api-kappa.vercel.app/api/v1/verses/amhara/{book_id}/{chapter}/{verse_num}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200 and "data" in data:
                v = data["data"]
                full_ref = f"{v['book']} {v['chapter']}:{v['verseNum']}"
                return {"reference": full_ref, "verse": v["verse"]}
    except Exception:
        pass  # አውታረ መረብ ችግር ወይም API ችግር
    return None

# ================================
# START COMMAND
# ================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in new_users:
        new_users.add(user_id)
        bot.send_message(
            message.chat.id,
            "👋 Welcome to HU Bible Study Section Question and Answer Bot!\n"
            "እንኳን ወደ HU Bible Study Section የጥያቄ እና መልስ bot በደህና መጡ!",
        )

    # አዲስ ቁልፍ: የመጽሐፍ ቅዱስ ጥቅስ ፈልግ
    inline = types.InlineKeyboardMarkup()
    inline.add(
        types.InlineKeyboardButton("ከገላትያ", callback_data="btn1"),
        types.InlineKeyboardButton("ከየትኛውም ቦታ ይጠይቁ", callback_data="btn2")
    )
    inline.add(
        types.InlineKeyboardButton("በቤተሰብ፣ በሴክሽን ፕሮግራም ላይ ማንኛውንም አስተያየት ይስጡ", callback_data="btn3")
    )
    inline.add(
        types.InlineKeyboardButton("የመጽሐፍ ቅዱስ ጥቅስ ፈልግ", callback_data="btn4")
    )
    bot.send_message(
        message.chat.id,
        "ከቅዱስ መጽሐፋችን ማንኛውንም ጥያቄ ይጠይቁ!",
        reply_markup=inline
    )

# ================================
# BUTTON CALLBACK
# ================================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if data == "btn4":
        # ጥቅስ ፍለጋ ሁኔታ
        user_state[user_id] = "verse_search"
        bot.send_message(
            chat_id,
            "📖 የፈለጉትን ጥቅስ ማጣቀሻ ይፃፉ (ለምሳሌ: **John 3:16** ወይም **ዮሐንስ 3:16**)\n\n"
            "በእንግሊዝኛ ወይም በአማርኛ ማጣቀሻ ይጠቀሙ። ቀጥታ መልስ ይመጣል!"
        )
    else:
        # ሌሎች ቁልፎች = ጥያቄ/አስተያየት
        if user_id in user_state:
            user_state.pop(user_id, None)  # ፍለጋ ሁኔታ አጥፋ
        bot.send_message(chat_id, "ጥያቄዎን / አስተያየትዎን ይላኩ...")

# ================================
# USER MESSAGE HANDLER (ጥቅስ ፍለጋ + ወደ አስተዳዳሪ ማስተላለፍ)
# ================================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_GROUP_ID)
def forward_to_admin(message):
    user_id = message.from_user.id

    # === አዲስ: ጥቅስ ፍለጋ ሁኔታ ===
    if user_id in user_state and user_state[user_id] == "verse_search":
        result = search_bible_verse(message.text)
        if result:
            bot.send_message(
                message.chat.id,
                f"📖 **{result['reference']}**\n\n"
                f"{result['verse']}\n\n"
                "ትርጉም: መጽሐፍ ቅዱስ (አማርኛ)"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ ጥቅሱ አልተገኘም። ማጣቀሻውን በትክክል ይፃፉ (ለምሳሌ: John 3:16 ወይም ዮሐንስ 3:16)\n\n"
                "ዳግም ለመሞከር ቁልፉን ይጫኑ ወይም ሌላ ጥያቄ ይጠይቁ።"
            )
        # ሁኔታ አጥፋ
        user_state.pop(user_id, None)
        return

    # === መደበኛ: ጥያቄ/አስተያየት → አስተዳዳሪ ===
    username = message.from_user.username
    name = f"@{username}" if username else message.from_user.first_name
    text = message.text if message.text else "[Media]"
    sent = bot.send_message(
        ADMIN_GROUP_ID,
        f"📩 From {name}\n\n{text}"
    )
    admin_to_user_map[sent.message_id] = user_id
    bot.send_message(message.chat.id, "✅ Question / Comment sent!")

# ================================
# ADMIN REPLY (ቀድሞው ነው)
# ================================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message)
def admin_reply(message):
    replied = message.reply_to_message.message_id
    user_id = admin_to_user_map.get(replied)
    if not user_id:
        return
    bot.send_message(user_id, f"💬 Answer:\n{message.text}")
    bot.send_message(ADMIN_GROUP_ID, "✔ Answer sent")

# ================================
# HEALTH CHECK + WEBHOOK (ቀድሞው ነው)
# ================================
@app.route("/healthz")
def health():
    return {"status": "ok"}, 200

@app.route(f"/{API_TOKEN}", methods=["POST"])
def telegram_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running"

# ================================
# START SERVER
# ================================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
