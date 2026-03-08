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
        bot.send_message(call.message.chat.id, "ጥያቄዎን ይላኩ...")
    
    elif call.data == "btn2":
        bot.send_message(call.message.chat.id, "አስተያየትዎን ይላኩ...")
    
    bot.answer_callback_query(call.id)

# ================================
# SHOW MESSAGE WITH INLINE BUTTONS
# ================================
@bot.message_handler(func=lambda m: True)
def show_message(message):
    inline = types.InlineKeyboardMarkup(row_width=2)
    inline.add(
        types.InlineKeyboardButton("ጥያቄዎን", callback_data="btn1"),
        types.InlineKeyboardButton("አስተያየት", callback_data="btn2")
    )
    bot.send_message(message.chat.id, "Choose an option:", reply_markup=inline)

# ================================
# FORWARD USER MESSAGE TO ADMIN GROUP (with history)
# ================================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_GROUP_ID)
def forward_to_admin(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = f"@{username}" if username else message.from_user.first_name
    
    # Save this message
    if user_id not in user_questions:
        user_questions[user_id] = []
    user_questions[user_id].append(message.text if message.text else "No text content")
    
    # Check if the user has already answered this question
    if user_id in admin_to_user_map:
        # User has already answered this question, skip forwarding to admin group
        return
    
    # Build message with history (last 1 or 2 previous messages)
    history_part = ""
    if len(user_questions[user_id]) > 1:
        prev_questions = user_questions[user_id][-2:]  # last 2 before current
        history_part = "🗨 Previous:\n" + "\n".join([f"• {q}" for q in prev_questions]) + "\n\n"
    
    # Relay the message to the admin group
    if message.content_type == 'audio':
        bot.send_audio(ADMIN_GROUP_ID, message.audio.file_id, caption=f"📩 From {name} (ID: {user_id})\n{history_part}")
    elif message.content_type == 'voice':
        bot.send_voice(ADMIN_GROUP_ID, message.voice.file_id, caption=f"📩 From {name} (ID: {user_id})\n{history_part}")
    elif message.content_type == 'document':
        bot.send_document(ADMIN_GROUP_ID, message.document.file_id, caption=f"📩 From {name} (ID: {user_id})\n{history_part}")
    elif message.content_type == 'photo':
        bot.send_photo(ADMIN_GROUP_ID, message.photo[-1].file_id, caption=f"📩 From {name} (ID: {user_id})\n{history_part}")
    elif message.content_type == 'text':
        bot.send_message(ADMIN_GROUP_ID, f"📩 From {name} (ID: {user_id})\n{history_part}\n{text}")
    elif message.content_type == 'link':
        bot.send_message(ADMIN_GROUP_ID, f"📩 From {name} (ID: {user_id})\n{history_part}\nLink: {message.text}")
    else:
        bot.send_message(ADMIN_GROUP_ID, f"📩 From {name} (ID: {user_id})\n{history_part}\n[Media / Non-text content]")

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
    if message.content_type == 'audio':
        bot.send_audio(user_id, message.audio.file_id, caption=message.text)
    elif message.content_type == 'voice':
        bot.send_voice(user_id, message.voice.file_id, caption=message.text)
    elif message.content_type == 'document':
        if message.document.file_size > 20000000:  # Check file size limit
            bot.send_message(ADMIN_GROUP_ID, "🚫 File too large. Please use a link instead.")
            return
        bot.send_document(user_id, message.document.file_id, caption=message.text)
    elif message.content_type == 'photo':
        bot.send_photo(user_id, message.photo[-1].file_id, caption=message.text)
    elif message.content_type == 'text':
        bot.send_message(user_id, message.text)
    elif message.content_type == 'link':
        bot.send_message(user_id, message.text)
    else:
        bot.send_message(ADMIN_GROUP_ID, "🚫 Unsupported content type.")

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
