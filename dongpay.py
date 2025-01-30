import os
import telebot
import requests
import time
from flask import Flask, request, jsonify

# Initialize Flask app
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

# ✅ /start command
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = WAITING_FOR_AMOUNT  # Set the state to waiting for amount
    print(f"Start command received from {chat_id}")  # Debugging
    bot.send_message(chat_id, "Welcome! Please enter the amount you'd like to deposit (min 2000).")

# ✅ Handle deposit amount
@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_amount(message):
    chat_id = message.chat.id
    if chat_id not in user_state or user_state[chat_id] != WAITING_FOR_AMOUNT:
        return  # Ignore if we're not expecting an amount

    amount = int(message.text)

    if amount < 2000:
        bot.send_message(chat_id, "The minimum deposit amount is 2000. Please enter a valid amount.")
    else:
        bot.send_message(chat_id, f"Amount: {amount}. Please enter your phone number.")
        user_state[chat_id] = WAITING_FOR_PHONE  # Update state to waiting for phone
        bot.register_next_step_handler(message, handle_phone, amount)

# ✅ Validate and process phone number for STK Push
def handle_phone(message, amount):
    chat_id = message.chat.id
    if chat_id not in user_state or user_state[chat_id] != WAITING_FOR_PHONE:
        return  # Ignore if we're not expecting a phone number

    phone = message.text.strip()

    # Ensure phone number is 10 digits and starts with 07
    if not phone.isdigit() or len(phone) != 10 or not phone.startswith("07"):
        bot.send_message(chat_id, "Invalid phone number. Please enter a valid Safaricom number (e.g., 0712345678).")
        user_state[chat_id] = WAITING_FOR_PHONE  # Stay in waiting for phone state
        return  # Prompt again for phone number

    print(f"Phone number received from {chat_id}: {phone}")  # Debugging

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
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# ✅ Flask route for health check
@app.route('/')
def index():
    return jsonify({"status": "Bot is running!"})

# ✅ Start bot using polling (for development purposes)
def start_polling():
    print("🚀 Bot is running using polling...")
    bot.remove_webhook()  # ✅ Remove webhook first
    time.sleep(1)  # ✅ Give time for Telegram to unregister webhook
    bot.polling(none_stop=True)  # ✅ Start polling

# ✅ Start bot in a separate thread
from threading import Thread
thread = Thread(target=start_polling)
thread.start()

# ✅ Start Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
