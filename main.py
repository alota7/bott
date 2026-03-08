import os
from telebot import TeleBot, types
from flask import Flask, request
from config import API_TOKEN, ADMIN_GROUP_ID

bot = TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

RENDER_URL = "https://bott-2-jpt2.onrender.com"

thread_history = {}
admin_to_user_map = {}
new_users = set()
user_mode = {}   # question or comment mode

# ================================
# START COMMAND / Start button click
# ================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Welcome message only once (for new users)
    if user_id not in new_users:
        new_users.add(user_id)
        bot.send_message(
            message.chat.id,
            "👋 Welcome to HU Bible Study Section Question and Answer Bot!\n"
            "እንኳን ወደ HU Bible Study Section የጥያቄ እና መልስ bot በደህና መጡ!"
        )
    
    # Always show the two choice buttons when /start is used
    inline = types.InlineKeyboardMarkup(row_width=1)  # better vertical look on mobile
    inline.add(
        types.InlineKeyboardButton("ጥያቄዎን ይላኩ...", callback_data="btn1"),
        types.InlineKeyboardButton("አስተያየት መስጫ...", callback_data="btn2")
    )
    bot.send_message(
        message.chat.id,
        "ከዚህ በታች አንዱን ይምረጡ 👇",   # optional small hint text — you can remove if you want it completely empty
        reply_markup=inline
    )

# ================================
# BUTTON CALLBACK
# ================================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    
    if call.data == "btn1":
        bot.send_message(
            call.message.chat.id,
            "ጥያቄዎን ይላኩ..."
        )
        user_mode[user_id] = "question"
    
    elif call.data == "btn2":
        bot.send_message(
            call.message.chat.id,
            "አስተያየትዎን ይላኩ..."
        )
        user_mode[user_id] = "comment"
    
    bot.answer_callback_query(call.id)

# ================================
# FORWARD USER MESSAGE TO ADMIN
# ================================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_GROUP_ID)
def forward_to_admin(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = f"@{username}" if username else message.from_user.first_name
    text = message.text if message.text else "[Media]"
    
    sent = bot.send_message(
        ADMIN_GROUP_ID,
        f"📩 From {name}\n\n{text}"
    )
    admin_to_user_map[sent.message_id] = user_id
    
    # Success message depending on mode
    if user_id in user_mode:
        mode = user_mode.pop(user_id)
        success = "✅ ጥያቄዎ ተልኳል!" if mode == "question" else "✅ አስተያየትዎ ተልኳል!"
    else:
        success = "✅ ተልኳል!"
    
    bot.send_message(message.chat.id, success)

# ================================
# ADMIN REPLIES TO USER
# ================================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message)
def admin_reply(message):
    replied = message.reply_to_message.message_id
    user_id = admin_to_user_map.get(replied)
    if not user_id:
        return
    bot.send_message(user_id, f"💬 መልስ:\n{message.text}")
    bot.send_message(ADMIN_GROUP_ID, "✔ መልስ ተልኳል")

# ================================
# WEBHOOK & SERVER
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

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
