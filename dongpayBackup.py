from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TINPESA_API_URL = "https://api.tinypesa.com/api/v1/express/initialize/?username=Donga"
TINPESA_API_KEY = "3k6NdpnrdvY3ES-akS64Lv78XE3rURRtSPUqfaqlqruBHAX2af"
TINPESA_USERNAME = "Donga"
ACCOUNT_NUMBER = "DONGALTD"

@app.route('/stk_push', methods=['POST'])
def stk_push():
    data = request.json
    amount = data.get("amount")
    phone = data.get("phone")

    if not amount or not phone:
        return jsonify({"error": "Amount and phone number are required"}), 400

    payload = {
        "amount": amount,
        "msisdn": phone,
        "account_no": ACCOUNT_NUMBER,
        "username": TINPESA_USERNAME  # Corrected here
    }

    headers = {
        "Content-Type": "application/json",
        "Apikey": TINPESA_API_KEY  # Corrected here
    }

    try:
        response = requests.post(TINPESA_API_URL, json=payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("success"):
            return jsonify({"message": "STK Push sent successfully"})
        else:
            return jsonify({"error": response_data.get("message", "STK Push failed")}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
