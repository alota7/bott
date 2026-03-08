import os
from telebot import TeleBot, types
from flask import Flask, request
from config import API_TOKEN, ADMIN_GROUP_ID

bot = TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

RENDER_URL = "https://bott-2-jpt2.onrender.com"

# message_id in admin group → user_id
admin_to_user_map = {}

# ================================
# START COMMAND
# ================================
@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "👋 Welcome to HU Bible Study Section Question and Answer Bot!\n"
        "እንኳን ወደ HU Bible Study Section የጥያቄ እና መልስ bot በደህና መጡ!"
    )

    # buttons on same line
    inline = types.InlineKeyboardMarkup()
    inline.row(
        types.InlineKeyboardButton("ጥያቄዎን ይላኩ", callback_data="btn1"),
        types.InlineKeyboardButton("አስተያየት መስጫ", callback_data="btn2")
    )

    bot.send_message(
        message.chat.id,
        "ከዚህ በታች አንዱን ይምረጡ 👇",
        reply_markup=inline
    )

# ================================
# BUTTON CALLBACK
# ================================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    if call.data == "btn1":
        bot.send_message(call.message.chat.id, "ጥያቄዎን ይላኩ...")

    elif call.data == "btn2":
        bot.send_message(call.message.chat.id, "አስተያየትዎን ይላኩ...")

    bot.answer_callback_query(call.id)

# ================================
# USER MESSAGE → ADMIN GROUP
# ================================
@bot.message_handler(
    content_types=['text','photo','video','document','voice','audio','sticker'],
    func=lambda m: m.chat.id != ADMIN_GROUP_ID
)
def forward_to_admin(message):

    user_id = message.from_user.id
    username = message.from_user.username
    name = f"@{username}" if username else message.from_user.first_name

    # forward message
    sent = bot.forward_message(
        ADMIN_GROUP_ID,
        message.chat.id,
        message.message_id
    )

    admin_to_user_map[sent.message_id] = user_id

    # notify admin
    bot.send_message(
        ADMIN_GROUP_ID,
        f"👤 From: {name}\n🆔 ID: {user_id}"
    )

    # confirmation to user
    bot.send_message(message.chat.id, "✅ ተልኳል!")

# ================================
# ADMIN REPLY → USER
# ================================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message)
def admin_reply(message):

    replied_msg_id = message.reply_to_message.message_id
    user_id = admin_to_user_map.get(replied_msg_id)

    if not user_id:
        return

    # forward admin reply to user
    bot.forward_message(
        user_id,
        ADMIN_GROUP_ID,
        message.message_id
    )

    bot.send_message(
        ADMIN_GROUP_ID,
        "✔ መልስ ተልኳል"
    )

# ================================
# HEALTH CHECK
# ================================
@app.route("/healthz")
def health():
    return {"status": "ok"}, 200

# ================================
# TELEGRAM WEBHOOK
# ================================
@app.route(f"/{API_TOKEN}", methods=["POST"])
def telegram_webhook():

    json_string = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_string)

    bot.process_new_updates([update])

    return "OK", 200

# ================================
# HOME PAGE
# ================================
@app.route("/")
def index():
    return "Bot is running"

# ================================
# RUN SERVER
# ================================
if __name__ == "__main__":

    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
