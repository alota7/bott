from telebot import TeleBot, types
from config import API_TOKEN, ADMIN_GROUP_ID
from flask import Flask, request

bot = TeleBot(API_TOKEN)
app = Flask(__name__)

# ==========================================
# THREAD STORAGE
# ==========================================
thread_history = {}       
admin_to_user_map = {}    
user_to_admin_map = {}
new_users = set()

# ==========================================
# /start COMMAND
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in new_users:
        new_users.add(user_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn_start = types.KeyboardButton("/start")
        markup.add(btn_start)
        bot.send_message(
            message.chat.id,
            "👋 Welcome to HU Bible Study Section Question and Answer Bot!"
            "\nእንኳን ወደ HU Bible Study Section የጥያቄ እና መልስ bot በደህና መጡ!",
            reply_markup=markup
        )

    inline_markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("ከገላትያ", callback_data="btn1")
    btn2 = types.InlineKeyboardButton("ከየትኛውም ቦታ ይጠይቁ", callback_data="btn2")
    inline_markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        "ከየት መጠየቅ ይፈልጋሉ?\nChoose an option:",
        reply_markup=inline_markup
    )

# ==========================================
# INLINE BUTTON
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.send_message(
        call.message.chat.id,
        "ጥያቄዎን ይላኩ...\nSend your Question..."
    )

# ==========================================
# FORWARD USER MESSAGE
# ==========================================
@bot.message_handler(
    func=lambda m: m.chat.id != ADMIN_GROUP_ID,
    content_types=['text', 'photo', 'document', 'voice', 'audio', 'video', 'video_note']
)
def forward_to_admin(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    display_name = f"@{username}" if username else first_name

    sent = None
    media_id = None
    content = ""

    if message.content_type == "text":
        content = message.text
    elif message.content_type == "photo":
        media_id = message.photo[-1].file_id
        content = message.caption or "[Photo]"
    elif message.content_type == "document":
        media_id = message.document.file_id
        content = message.caption or "[Document]"
    elif message.content_type == "voice":
        media_id = message.voice.file_id
        content = "[Voice message]"
    elif message.content_type == "audio":
        media_id = message.audio.file_id
        content = message.caption or "[Audio]"
    elif message.content_type == "video":
        media_id = message.video.file_id
        content = message.caption or "[Video]"
    elif message.content_type == "video_note":
        media_id = message.video_note.file_id
        content = "[Video note]"

    prev_message_text = ""
    if user_id in thread_history:
        for entry in reversed(thread_history[user_id]):
            if entry["from"] != "Admin":
                prev_lines = entry["content"].splitlines()[:2]
                prev_message_text = "\n".join(prev_lines)
                prev_message_text = f"🕘 Previous Question:\n{prev_message_text}\n\n"
                break

    message_to_admin = f"{prev_message_text}📩 From {display_name}:\n{content}"

    if message.content_type == "text":
        sent = bot.send_message(ADMIN_GROUP_ID, message_to_admin)
    elif message.content_type == "photo":
        sent = bot.send_photo(ADMIN_GROUP_ID, media_id, caption=message_to_admin)
    elif message.content_type == "document":
        sent = bot.send_document(ADMIN_GROUP_ID, media_id, caption=message_to_admin)
    elif message.content_type == "voice":
        sent = bot.send_voice(ADMIN_GROUP_ID, media_id, caption=message_to_admin)
    elif message.content_type == "audio":
        sent = bot.send_audio(ADMIN_GROUP_ID, media_id, caption=message_to_admin)
    elif message.content_type == "video":
        sent = bot.send_video(ADMIN_GROUP_ID, media_id, caption=message_to_admin)
    elif message.content_type == "video_note":
        sent = bot.send_video_note(ADMIN_GROUP_ID, media_id)

    if not sent:
        return

    if user_id not in thread_history:
        thread_history[user_id] = []
    thread_history[user_id].append({
        "from": display_name,
        "type": message.content_type,
        "content": content,
        "media_id": media_id
    })

    admin_to_user_map[sent.message_id] = user_id
    user_to_admin_map[message.message_id] = sent.message_id

    bot.send_message(message.chat.id, "✅ ጥያቄዎ ተልኳል።\nYour question has been sent!\nWait for the Answer...")

# ==========================================
# ADMIN REPLY HANDLER
# ==========================================
@bot.message_handler(
    func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message,
    content_types=['text', 'photo', 'document', 'voice', 'audio', 'video', 'video_note']
)
def handle_admin_reply(message):
    replied_id = message.reply_to_message.message_id
    user_id = admin_to_user_map.get(replied_id)
    if not user_id:
        return

    sent = None
    media_id = None
    content = ""

    if message.content_type == "text":
        content = message.text
        sent = bot.send_message(user_id, f"💬 Answer:\n{content}")
    elif message.content_type == "photo":
        media_id = message.photo[-1].file_id
        content = message.caption or ""
        sent = bot.send_photo(user_id, media_id, caption=f"💬 Answer:\n{content}")
    elif message.content_type == "document":
        media_id = message.document.file_id
        content = message.caption or ""
        sent = bot.send_document(user_id, media_id, caption=f"💬 Answer:\n{content}")
    elif message.content_type == "voice":
        media_id = message.voice.file_id
        sent = bot.send_voice(user_id, media_id, caption="💬 Answer")
    elif message.content_type == "audio":
        media_id = message.audio.file_id
        content = message.caption or ""
        sent = bot.send_audio(user_id, media_id, caption=f"💬 Answer\n{content}")
    elif message.content_type == "video":
        media_id = message.video.file_id
        content = message.caption or ""
        sent = bot.send_video(user_id, media_id, caption=f"💬 Answer\n{content}")
    elif message.content_type == "video_note":
        media_id = message.video_note.file_id
        sent = bot.send_video_note(user_id, media_id)

    if not sent:
        return

    if user_id not in thread_history:
        thread_history[user_id] = []
    thread_history[user_id].append({
        "from": "Admin",
        "type": message.content_type,
        "content": content,
        "media_id": media_id
    })

    admin_to_user_map[message.message_id] = user_id
    user_to_admin_map[sent.message_id] = message.message_id

    bot.send_message(ADMIN_GROUP_ID, "✔ Answer sent to user!")

# ————————————
# HEALTH CHECK ROUTE (for Render)
# ————————————
@app.route("/healthz", methods=["GET"])
def health_check():
    return {"status": "ok"}, 200

# ————————————
# WEBHOOK RECEIVER
# ————————————
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook_handler():
    update = request.get_json(force=True)
    bot.process_new_updates([types.Update.de_json(update)])
    return "ok", 200
# ==========================================
# WEBHOOK RECEIVER
# ==========================================
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook_handler():
    update = request.get_json(force=True)
    bot.process_new_updates([types.Update.de_json(update)])
    return "ok", 200

# The old polling is removed — webhook will receive updates
