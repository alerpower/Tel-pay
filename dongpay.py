import os
import telebot
import requests
import logging
from flask import Flask
from dataclasses import dataclass

# Initialize Flask app (for health check)
app = Flask(__name__)

# Load API credentials from environment variables
API_TOKEN = os.getenv('API_TOKEN')
TINPESA_API_KEY = os.getenv('TINPESA_API_KEY')
TINPESA_USERNAME = "Donga"
ACCOUNT_NUMBER = "DONGALTD"

if not API_TOKEN or not TINPESA_API_KEY:
    raise ValueError("API_TOKEN or TINPESA_API_KEY is missing! Set them in environment variables.")

# Initialize Telegram bot
bot = telebot.TeleBot(API_TOKEN)

# TinPesa API URL
TINPESA_API_URL = "https://api.tinypesa.com/api/v1/express/initialize/?username=Donga"

# Track user states
user_state = {}

# Define user states
WAITING_FOR_AMOUNT = 1
WAITING_FOR_PHONE = 2

# Supported languages
LANGUAGES = {
    "en": "English",
    "sw": "Swahili"
}

# Messages dictionary
MESSAGES = {
    "welcome": {
        "en": "Welcome! Please enter the amount you'd like to deposit (min 2000).",
        "sw": "Karibu! Tafadhali weka kiasi unachotaka kuweka (kiasi cha chini ni 2000)."
    },
    "invalid_amount": {
        "en": "The minimum deposit amount is 2000. Please enter a valid amount.",
        "sw": "Kiasi cha chini cha kuweka ni 2000. Tafadhali weka kiasi sahihi."
    },
    "enter_phone": {
        "en": "Amount: {}. Please enter your phone number.",
        "sw": "Kiasi: {}. Tafadhali weka namba yako ya simu."
    },
    "invalid_phone": {
        "en": "Invalid phone number. Please enter a valid Safaricom number (e.g., 0712345678).",
        "sw": "Namba ya simu si sahihi. Tafadhali weka namba sahihi ya Safaricom (mfano: 0712345678)."
    },
    "confirm_transaction": {
        "en": "Please confirm your transaction details:\nAmount: KES {}\nPhone: {}\n\nType 'confirm' to proceed or 'cancel' to abort.",
        "sw": "Tafadhali thibitisha maelezo yako ya muamala:\nKiasi: KES {}\nNamba ya Simu: {}\n\nAndika 'confirm' kuendelea au 'cancel' kukatisha."
    },
    "transaction_success": {
        "en": "✅ Mpesa Popup sent successfully! Please enter your PIN to complete the transaction.",
        "sw": "✅ Mpesa Popup imetumwa kwa mafanikio! Tafadhali weka PIN yako kukamilisha muamala."
    },
    "transaction_failed": {
        "en": "❌ Error: {}",
        "sw": "❌ Hitilafu: {}"
    },
    "operation_cancelled": {
        "en": "✅ Operation canceled. Type /start to begin again.",
        "sw": "✅ Hatua imekatishwa. Andika /start kuanza upya."
    },
    "choose_language": {
        "en": "Choose your preferred language:",
        "sw": "Chagua lugha unayotaka:"
    },
    "language_set": {
        "en": "✅ Language set to {}.",
        "sw": "✅ Lugha imebadilishwa kuwa {}."
    },
    "coming_soon": {
        "en": "🚧 Coming soon!",
        "sw": "🚧 Inakuja hivi karibuni!"
    },
    "unrecognized_input": {
        "en": "❌ Unrecognized input. Please follow the instructions.",
        "sw": "❌ Ingizo halitambuliki. Tafadhali fuata maagizo."
    }
}

# User state tracking with language preference
@dataclass
class UserState:
    state: int
    metadata: dict = None  # Store additional data like name, language, etc.

# Get message in the user's language
def get_message(chat_id, key, *args):
    lang = user_state.get(chat_id, UserState(0, {"language": "en"})).metadata.get("language", "en")
    return MESSAGES[key].get(lang, MESSAGES["coming_soon"]["en"]).format(*args)

# ✅ /start command
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = UserState(state=WAITING_FOR_AMOUNT, metadata={"name": message.from_user.first_name, "language": "en"})
    bot.send_message(chat_id, get_message(chat_id, "welcome"))

# ✅ Handle deposit amount
@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_amount(message):
    chat_id = message.chat.id
    if chat_id not in user_state or user_state[chat_id].state != WAITING_FOR_AMOUNT:
        return

    amount = int(message.text)
    if amount < 2000:
        bot.send_message(chat_id, get_message(chat_id, "invalid_amount"))
    else:
        bot.send_message(chat_id, get_message(chat_id, "enter_phone", amount))
        user_state[chat_id].state = WAITING_FOR_PHONE
        bot.register_next_step_handler(message, handle_phone, amount)

# ✅ Handle phone number
def handle_phone(message, amount):
    chat_id = message.chat.id
    phone = message.text.strip()

    if not phone.isdigit() or len(phone) != 10 or not phone.startswith("07"):
        bot.send_message(chat_id, get_message(chat_id, "invalid_phone"))
        bot.register_next_step_handler(message, handle_phone, amount)
        return

    bot.send_message(chat_id, get_message(chat_id, "confirm_transaction", amount, phone))
    bot.register_next_step_handler(message, confirm_transaction, amount, phone)


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

# ✅ Confirm transaction
def confirm_transaction(message, amount, phone):
    chat_id = message.chat.id
    if message.text.lower() == 'confirm':
        payload = {"amount": amount, "msisdn": phone, "account_no": ACCOUNT_NUMBER, "username": TINPESA_USERNAME}
        headers = {"Content-Type": "application/json", "Apikey": TINPESA_API_KEY}
        try:
            response = requests.post(TINPESA_API_URL, json=payload, headers=headers).json()
            if response.get("success"):
                bot.send_message(chat_id, get_message(chat_id, "transaction_success"))
            else:
                bot.send_message(chat_id, get_message(chat_id, "transaction_failed", response.get("message", "Unknown error.")))
        except Exception as e:
            bot.send_message(chat_id, get_message(chat_id, "transaction_failed", str(e)))
    else:
        bot.send_message(chat_id, get_message(chat_id, "operation_cancelled"))

# ✅ /language command
@bot.message_handler(commands=['language'])
def set_language(message):
    chat_id = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for code, name in LANGUAGES.items():
        markup.add(name)
    bot.send_message(chat_id, get_message(chat_id, "choose_language"), reply_markup=markup)
    bot.register_next_step_handler(message, save_language)

def save_language(message):
    chat_id = message.chat.id
    language = message.text.lower()
    lang_code = next((code for code, name in LANGUAGES.items() if name.lower() == language), None)
    if lang_code:
        user_state[chat_id].metadata["language"] = lang_code
        bot.send_message(chat_id, get_message(chat_id, "language_set", LANGUAGES[lang_code]))
    else:
        bot.send_message(chat_id, get_message(chat_id, "coming_soon"))

# ✅ /cancel command
@bot.message_handler(commands=['cancel'])
def cancel(message):
    chat_id = message.chat.id
    user_state.pop(chat_id, None)
    bot.send_message(chat_id, get_message(chat_id, "operation_cancelled"))

# ✅ Handle unrecognized input
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, get_message(chat_id, "unrecognized_input"))

