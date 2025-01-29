import telebot
from flask import Flask, request, jsonify
import requests

# Telegram bot setup
API_TOKEN = '8064725015:AAFzO5kCMxLIBgoGIMqymWunTioRuiTw9U4'
bot = telebot.TeleBot(API_TOKEN)

# Flask setup
app = Flask(__name__)

TINPESA_API_URL = "https://api.tinypesa.com/api/v1/express/initialize/?username=Donga"
TINPESA_API_KEY = "3k6NdpnrdvY3ES-akS64Lv78XE3rURRtSPUqfaqlqruBHAX2af"
TINPESA_USERNAME = "Donga"
ACCOUNT_NUMBER = "DONGALTD"

# Command handler for /start
@bot.message_handler(commands=['start'])
def start(message):
    print(f"Start command received from {message.chat.id}")  # Debugging
    bot.send_message(message.chat.id, "Welcome! Please enter the amount you'd like to deposit (min 2000).")

# Command handler for /test
@bot.message_handler(commands=['test'])
def test(message):
    print(f"Test command received from {message.chat.id}")  # Debugging
    bot.send_message(message.chat.id, "Test message received!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    print(f"Handling message from {message.chat.id}: {message.text}")  # Debugging
    try:
        amount = int(message.text)
        if amount < 2000:
            bot.send_message(message.chat.id, "The minimum deposit amount is 2000. Please enter a valid amount.")
        else:
            bot.send_message(message.chat.id, f"Amount: {amount}. Please enter your phone number.")
            bot.register_next_step_handler(message, handle_phone, amount)
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid amount.")

def handle_phone(message, amount):
    phone = message.text
    print(f"Phone number received: {phone}")  # Debugging
    # Make the API call to initiate the STK Push
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
            bot.send_message(message.chat.id, "Mpesa Popup sent successfully! Please enter your PIN to complete the transaction.")
        else:
            bot.send_message(message.chat.id, f"Error: {response_data.get('message', 'Failed to initiate STK Push.')}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {str(e)}")

# Flask route to keep the bot running
@app.route('/')
def home():
    return "Server is running!"  # Added for debugging

@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    print("Received webhook data:", json_str)  # Log webhook data for debugging
    update = telebot.types.Update.de_json(json_str)
    print(f"Update processed: {update}")  # Debugging to check the processed update
    bot.process_new_updates([update])
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Remove any existing webhook
    bot.remove_webhook()
    
    # Set your webhook URL
    bot.set_webhook(url="https://tel-pay.onrender.com/webhook")  # Ensure this URL is correct and accessible by Telegram
    
    # Start the Flask server
    app.run(debug=True, host="0.0.0.0", port=10000)
