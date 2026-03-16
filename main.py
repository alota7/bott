import os
from datetime import datetime
from telebot import TeleBot, types
from flask import Flask, request
from config import API_TOKEN, ADMIN_GROUP_ID

bot = TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

RENDER_URL = "https://bott-2-jpt2.onrender.com"

# ==========================================
# DATA STORAGE
# ==========================================
admin_to_user_map = {}       # admin msg_id → user_id
user_to_admin_map = {}       # user msg_id → admin msg_id
thread_history = {}          # user_id → list of messages for history

# ==========================================
# START COMMAND
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "እንኳን ወደ HU Bible Study Section የጥያቄ መጠየቅያ BOT በደህና መጡ!"
    )

    inline = types.InlineKeyboardMarkup()
    inline.row(
        types.InlineKeyboardButton("ጥያቄዎን ይላኩ", callback_data="btn1"),
        types.InlineKeyboardButton("አስተያየት መስጫ", callback_data="btn2")
    )
    bot.send_message(
        message.chat.id,
       "ጥያቄዎን ወይም አስተያየትዎን ለመላክ፣ ከታች አንዱን አማራጭ ይምረጡ 👇",
        reply_markup=inline
    )

# ==========================================
# BUTTON CALLBACK
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "btn1":
        bot.send_message(call.message.chat.id, "ጥያቄዎን ይላኩ...")
    elif call.data == "btn2":
        bot.send_message(call.message.chat.id, "አስተያየትዎን ይላኩ...")
    bot.answer_callback_query(call.id)

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
        # get last 2 user messages
        user_msgs = [e for e in thread_history[user_id] if e["from"] != "Admin"][-2:]
        if user_msgs:
            prev_lines = [e["content"] for e in user_msgs]
            prev_message_text = "🕘 Previous Question:\n" + "\n".join(prev_lines) + "\n\n"

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

    bot.send_message(message.chat.id, "✅በተሳካ ሁኔታ ተልኳል። እናመሰግናለን!!")

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

# ==========================================
# HEALTH CHECK
# ==========================================
@app.route("/healthz")
def health():
    return {"status": "ok"}, 200

# ==========================================
# TELEGRAM WEBHOOK
# ==========================================
@app.route(f"/{API_TOKEN}", methods=["POST"])
def telegram_webhook():
    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

# ==========================================
# HOME PAGE
# ==========================================
@app.route("/")
def index():
    return "Bot is running"

# ==========================================
# RUN SERVER
# ==========================================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
