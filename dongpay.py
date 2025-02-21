import os
import telebot
import requests
import time
import logging
from flask import Flask, jsonify
from dataclasses import dataclass
from threading import Thread

# Initialize Flask app (only for health check)
app = Flask(__name__)

# Load API credentials from environment variables
API_TOKEN = os.getenv('API_TOKEN')
TINPESA_API_KEY = os.getenv('TINPESA_API_KEY')
TINPESA_USERNAME = "Donga"
ACCOUNT_NUMBER = "DONGALTD"

# Validate API credentials
if not API_TOKEN or not TINPESA_API_KEY:
    raise ValueError("API_TOKEN or TINPESA_API_KEY is missing! Set them in environment variables.")

# Initialize Telegram bot
bot = telebot.TeleBot(API_TOKEN)

# TinPesa API URL
TINPESA_API_URL = "https://api.tinypesa.com/api/v1/express/initialize/?username=Donga"

# Track user states (we'll use chat_id as the key)
user_state = {}

# Define states
WAITING_FOR_AMOUNT = 1
WAITING_FOR_PHONE = 2

# Define languages
LANGUAGES = {
    "en": "English",
    "sw": "Swahili",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "hi": "Hindi"
}

# Dynamic state management
@dataclass
class UserState:
    state: int
    metadata: dict = None  # Store additional data like name, last transaction, etc.

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ /start command
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = UserState(state=WAITING_FOR_AMOUNT, metadata={"name": message.from_user.first_name})
    logger.info(f"Start command received from {chat_id}")
    bot.send_message(chat_id, "Welcome! Please enter the amount you'd like to deposit (min 2000).")

# ✅ Handle deposit amount
@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_amount(message):
    chat_id = message.chat.id
    if chat_id not in user_state or user_state[chat_id].state != WAITING_FOR_AMOUNT:
        return  # Ignore if we're not expecting an amount

    amount = int(message.text)

    if amount < 2000:
        bot.send_message(chat_id, "The minimum deposit amount is 2000. Please enter a valid amount.")
    else:
        bot.send_message(chat_id, f"Amount: {amount}. Please enter your phone number.")
        user_state[chat_id].state = WAITING_FOR_PHONE  # Update state to waiting for phone
        bot.register_next_step_handler(message, handle_phone, amount)

# ✅ Validate and process phone number for STK Push
def handle_phone(message, amount):
    chat_id = message.chat.id
    if chat_id not in user_state or user_state[chat_id].state != WAITING_FOR_PHONE:
        return  # Ignore if we're not expecting a phone number

    phone = message.text.strip()

    # Ensure phone number is 10 digits and starts with 07
    if not phone.isdigit() or len(phone) != 10 or not phone.startswith("07"):
        bot.send_message(chat_id, "Invalid phone number. Please enter a valid Safaricom number (e.g., 0712345678).")
        bot.register_next_step_handler(message, handle_phone, amount)  # Continue asking for phone number
        return  # Prompt again for phone number

    logger.info(f"Phone number received from {chat_id}: {phone}")

    # Ask for confirmation
    confirmation_message = f"""
    Please confirm your transaction details:
    Amount: KES {amount}
    Phone: {phone}

    Type 'confirm' to proceed or 'cancel' to abort.
    """
    bot.send_message(chat_id, confirmation_message)
    bot.register_next_step_handler(message, confirm_transaction, amount, phone)

# ✅ Confirm transaction
def confirm_transaction(message, amount, phone):
    chat_id = message.chat.id
    if message.text.lower() == 'confirm':
        payload = {
            "amount": amount,
            "msisdn": phone,
            "account_no": ACCOUNT_NUMBER,
            "username": TINPESA_USERNAME
        }
        headers = {
            "Content-Type": "application/json",
            "Apikey": TINPESA_API_KEY
        }
        try:
            response = requests.post(TINPESA_API_URL, json=payload, headers=headers)
            response_data = response.json()
            if response.status_code == 200 and response_data.get("success"):
                bot.send_message(chat_id, "✅ Mpesa Popup sent successfully! Please enter your PIN to complete the transaction.")
            else:
                bot.send_message(chat_id, f"❌ Error: {response_data.get('message', 'Failed to initiate STK Push.')}")
        except Exception as e:
            logger.error(f"Error initiating STK Push for {chat_id}: {str(e)}")
            bot.send_message(chat_id, f"⚠️ Error: {str(e)}")
    else:
        bot.send_message(chat_id, "✅ Transaction canceled. Type /start to begin again.")

# ✅ /cancel command
@bot.message_handler(commands=['cancel'])
def cancel(message):
    chat_id = message.chat.id
    if chat_id in user_state:
        del user_state[chat_id]  # Reset the user's state
    bot.send_message(chat_id, "✅ Operation canceled. Type /start to begin again.")

# ✅ /help command
@bot.message_handler(commands=['help'])
def help(message):
    help_text = """
    Welcome to DongaBet Deposit Bot! Here's how to use me:

    /start - Begin the deposit process.
    /help - Show this help message.
    /cancel - Cancel the current operation.
    /status - Check the bot's status.
    /language - Set your preferred language.
    /feedback - Share your feedback or report issues.
    /settings - Customize your preferences.
    /notify - Enable or disable notifications.

    For any issues, contact support @DongbetBot.
    """
    bot.send_message(message.chat.id, help_text)

# ✅ /status command
@bot.message_handler(commands=['status'])
def status(message):
    chat_id = message.chat.id
    try:
        response = requests.get(TINPESA_API_URL, headers={"Apikey": TINPESA_API_KEY})
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ Bot is running and connected to TinPesa API.")
        else:
            bot.send_message(chat_id, "⚠️ Bot is running, but TinPesa API is unreachable.")
    except Exception as e:
        logger.error(f"Error checking TinPesa API status: {str(e)}")
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# ✅ /language command
@bot.message_handler(commands=['language'])
def set_language(message):
    chat_id = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for code, name in LANGUAGES.items():
        markup.add(name)
    bot.send_message(chat_id, "Choose your preferred language:", reply_markup=markup)
    bot.register_next_step_handler(message, save_language)

def save_language(message):
    chat_id = message.chat.id
    language = message.text
    if chat_id in user_state:
        user_state[chat_id].metadata["language"] = language
    bot.send_message(chat_id, f"✅ Language set to {language}.")

# ✅ /feedback command
@bot.message_handler(commands=['feedback'])
def feedback(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Please share your feedback or report any issues. We'll get back to you shortly!")
    bot.register_next_step_handler(message, save_feedback)

def save_feedback(message):
    chat_id = message.chat.id
    feedback_text = message.text
    logger.info(f"Feedback received from {chat_id}: {feedback_text}")
    bot.send_message(chat_id, "✅ Thank you for your feedback! We'll review it shortly.")

# ✅ /notify command
@bot.message_handler(commands=['notify'])
def notify_users(message):
    chat_id = message.chat.id
    if chat_id in user_state:
        user_state[chat_id].metadata["notifications"] = not user_state[chat_id].metadata.get("notifications", False)
        status = "enabled" if user_state[chat_id].metadata["notifications"] else "disabled"
        bot.send_message(chat_id, f"✅ Notifications {status}.")
    else:
        bot.send_message(chat_id, "❌ Please start the bot with /start first.")

# ✅ /settings command
@bot.message_handler(commands=['settings'])
def settings(message):
    chat_id = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Enable Notifications", "Disable Notifications", "Change Language")
    bot.send_message(chat_id, "Choose a setting to update:", reply_markup=markup)
    bot.register_next_step_handler(message, update_settings)

def update_settings(message):
    chat_id = message.chat.id
    setting = message.text
    if chat_id in user_state:
        if setting == "Enable Notifications":
            user_state[chat_id].metadata["notifications"] = True
            bot.send_message(chat_id, "✅ Notifications enabled.")
        elif setting == "Disable Notifications":
            user_state[chat_id].metadata["notifications"] = False
            bot.send_message(chat_id, "✅ Notifications disabled.")
        elif setting == "Change Language":
            set_language(message)
    else:
        bot.send_message(chat_id, "❌ Please start the bot with /start first.")

# ✅ Handle unrecognized input
@bot.message_handler(func=lambda message: True)
def handle_unrecognized_input(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Sorry, I don't recognize that command. Type /help for a list of commands.")

# ✅ Flask route for health check
@app.route('/')
def index():
    return jsonify({"status": "Bot is running!"})

# ✅ Start bot using polling (for development purposes)
def start_polling():
    logger.info("🚀 Bot is running using polling...")
    bot.remove_webhook()  # Remove webhook first
    time.sleep(1)  # Give time for Telegram to unregister webhook
    bot.polling(none_stop=True)  # Start polling

# ✅ Start bot in a separate thread
thread = Thread(target=start_polling)
thread.start()

# ✅ Start Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
