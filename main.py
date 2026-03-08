import os
from telebot import TeleBot, types
from flask import Flask, request
from config import API_TOKEN, ADMIN_GROUP_ID

bot = TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

RENDER_URL = "https://bott-2-jpt2.onrender.com"

admin_to_user_map = {}          # message_id in group → user_id
user_to_last_admin_msg = {}     # user_id → last forwarded message_id in admin group
user_questions = {}             # user_id → list of previous questions/comments
new_users = set()               # track new users (optional, kept for compatibility)

# ================================
# START COMMAND
# ================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Initialize user data for question history
    if user_id not in user_questions:
        user_questions[user_id] = []
    
    # Always show welcome message every time /start is triggered
    bot.send_message(
        message.chat.id,
        "👋 Welcome to HU Bible Study Section Question and Answer Bot!\n"
        "እንኳን ወደ HU Bible Study Section የጥያቄ እና መልስ bot በደህና መጡ!"
    )
    
    # Always show the button options
    inline = types.InlineKeyboardMarkup(row_width=1)
    inline.add(
        types.InlineKeyboardButton("ጥያቄዎን ይላኩ...", callback_data="btn1"),
        types.InlineKeyboardButton("አስተያየት መስጫ...", callback_data="btn2")
    )
    bot.send_message(
        message.chat.id,
        "ከዚህ በታች አንዱን ይምረጡ 👇",
        reply_markup=inline
    )

# ================================
# INLINE BUTTON CALLBACK
# ================================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    
    if call.data == "btn1":
        bot.send_message(call.message.chat.id, "ጥ�iyaቄዎን ይላኩ...")
    
    elif call.data == "btn2":
        bot.send_message(call.message.chat.id, "አስተያየትዎን ይላኩ...")
    
    bot.answer_callback_query(call.id)

# ================================
# FORWARD USER MESSAGE TO ADMIN GROUP (with history)
# ================================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_GROUP_ID)
def forward_to_admin(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = f"@{username}" if username else message.from_user.first_name
    text = message.text if message.text else "[Media / Non-text content]"

    # Save this message
    if user_id not in user_questions:
        user_questions[user_id] = []
    user_questions[user_id].append(text)

    # Build message with history (last 1 or 2 previous messages)
    history_part = ""
    if len(user_questions[user_id]) > 1:
        prev_questions = user_questions[user_id][:-1][-2:]  # last 2 before current
        history_part = "🗨 Previous:\n" + "\n".join([f"• {q}" for q in prev_questions]) + "\n\n"

    full_text = (
        f"📩 From {name} (ID: {user_id})\n"
        f"{history_part}"
        f"New message:\n{text}"
    )

    # Send to admin group
    sent = bot.send_message(ADMIN_GROUP_ID, full_text)
    admin_to_user_map[sent.message_id] = user_id
    user_to_last_admin_msg[user_id] = sent.message_id

    # Confirmation to user
    bot.send_message(message.chat.id, "✅ ተልኳል!")

# ================================
# ADMIN REPLIES → SEND TO USER
# ================================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message)
def admin_reply(message):
    replied_msg_id = message.reply_to_message.message_id
    user_id = admin_to_user_map.get(replied_msg_id)
    
    if not user_id:
        return

    # Send answer to user
    bot.send_message(user_id, f"💬 መልስ:\n{message.text}")

    # Confirm to admin
    bot.send_message(ADMIN_GROUP_ID, "✔ መልስ ተልኳል")

    # Clean up map
    admin_to_user_map.pop(replied_msg_id, None)

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
