import os
import telebot
from flask import Flask, request, jsonify
import requests

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

# Initialize Flask app
app = Flask(__name__)

# TinPesa API URL
TINPESA_API_URL = "https://api.tinypesa.com/api/v1/express/initialize/?username=Donga"

# ✅ /start command
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    print(f"Start command received from {chat_id}")  # Debugging
    bot.send_message(chat_id, "Welcome! Please enter the amount you'd like to deposit (min 2000).")

# ✅ /test command
@bot.message_handler(commands=['test'])
def test(message):
    chat_id = message.chat.id
    print(f"Test command received from {chat_id}")  # Debugging
    bot.send_message(chat_id, "Test message received!")

# ✅ Handle deposit amount
@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_amount(message):
    chat_id = message.chat.id
    amount = int(message.text)

    if amount < 2000:
        bot.send_message(chat_id, "The minimum deposit amount is 2000. Please enter a valid amount.")
    else:
        bot.send_message(chat_id, f"Amount: {amount}. Please enter your phone number.")
        bot.register_next_step_handler(message, handle_phone, amount)

# ✅ Handle phone number and initiate TinPesa STK push
def handle_phone(message, amount):
    chat_id = message.chat.id
    phone = message.text.strip()

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
            bot.send_message(chat_id, "Mpesa Popup sent successfully! Please enter your PIN to complete the transaction.")
        else:
            bot.send_message(chat_id, f"Error: {response_data.get('message', 'Failed to initiate STK Push.')}")
    
    except Exception as e:
        bot.send_message(chat_id, f"Error: {str(e)}")

# ✅ Flask route for health check
@app.route('/')
def home():
    return "Server is running!", 200

# ✅ Webhook route to receive Telegram updates
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    print("Received webhook data:", json_str)  # Debugging
    
    try:
        if not json_str:
            return jsonify({"status": "error", "message": "Empty request body"}), 400

        update = telebot.types.Update.de_json(json_str)
        if not hasattr(update, "message"):
            return jsonify({"status": "error", "message": "Invalid update format"}), 400

        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Webhook processing error: {e}")  # Debugging
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ Ensure webhook is set correctly when the server starts
bot.remove_webhook()
bot.set_webhook(url="https://tel-pay.onrender.com/webhook")

# ✅ Fix Render hosting issues
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Render assigns a dynamic port
    app.run(host="0.0.0.0", port=port)
