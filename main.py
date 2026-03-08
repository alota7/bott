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
user_mode = {}   # NEW: remembers which button user clicked (question or comment)

# ================================
# START COMMAND
# ================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # === ONLY FOR NEWCOMERS ===
    if user_id not in new_users:
        new_users.add(user_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("/start"))
        bot.send_message(
            message.chat.id,
            "👋 Welcome to HU Bible Study Section Question and Answer Bot!\n"
            "እንኳን ወደ HU Bible Study Section የጥያቄ እና መልስ bot በደህና መጡ!",
            reply_markup=markup
        )
    
    # Always show the two inline buttons
    inline = types.InlineKeyboardMarkup()
    inline.add(
        types.InlineKeyboardButton("ጥያቄዎን ይላኩ...", callback_data="btn1"),
        types.InlineKeyboardButton("አስተያየት መስጫ...", callback_data="btn2")
    )
    bot.send_message(
        message.chat.id,
        "",                     
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
            "ጥያቄዎን ይላኩ...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        user_mode[user_id] = "question"
    
    elif call.data == "btn2":
        bot.send_message(
            call.message.chat.id,
            "አስተያየትዎን ይላኩ...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        user_mode[user_id] = "comment"
    
    bot.answer_callback_query(call.id)

# ================================
# USER MESSAGE → ADMIN
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
    
    # === DIFFERENT SUCCESS MESSAGE BASED ON BUTTON CLICKED ===
    if user_id in user_mode:
        mode = user_mode.pop(user_id)                    # remove after use
        success_msg = "✅ Question sent!" if mode == "question" else "✅ Comment sent!"
    else:
        success_msg = "✅ Sent!"
    
    bot.send_message(
        message.chat.id,
        success_msg,
        reply_markup=types.ReplyKeyboardRemove()
    )

# ================================
# ADMIN REPLY
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
# HEALTH CHECK + WEBHOOK + SERVER
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
