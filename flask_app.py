from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from web3 import Web3
import requests
import time
import threading
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Для Telegram Mini App

# Загрузка переменных окружения
load_dotenv()

# BLOCKCHAIN
w3 = Web3(Web3.HTTPProvider('https://ethereum-sepolia.publicnode.com'))
print("✅ Web3 подключён")

CONTRACT_ADDRESS = CONTRACT_ADDRESS = "0x54Fc6752C178274eD1bcb7d67ef5D68bAFe07Ccc"
ACCOUNT = '0xc52c4B6dB509CF99fc85b532b7938e373824c109'
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '0x1e981e24e3731898790cc098d2ad8dcce2063a0898a1ce7f63a4294ae22ef2aa')

CONTRACT_ABI = [
    {"inputs":[{"internalType":"uint256","name":"_km","type":"uint256"}],"name":"logRun","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"runs","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalKm","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]

contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=CONTRACT_ABI
)

TELEGRAM_TOKEN = "8475048094:AAHvvbR8KX_YK6NV4kr58wiSQx5-hQLNQOI"

# Telegram функции
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': text})

def blockchain_tx(chat_id, km):
    km_total = int(km * 1000)
    nonce = w3.eth.get_transaction_count(ACCOUNT)
    tx = contract.functions.logRun(km_total).build_transaction({
        'from': ACCOUNT, 'nonce': nonce, 'gas': 200000, 'gasPrice': w3.to_wei('10', 'gwei')
    })
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    explorer = f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}"
    send_message(chat_id, f"✅ {km}км в блокчейн!\n🔗 {explorer}")

def telegram_bot():
    offset = 0
    print("🤖 Telegram bot активен")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            r = requests.get(url, params={'offset': offset, 'timeout': 30})
            data = r.json()

            for update in data['result']:
                offset = update['update_id'] + 1
                chat_id = update['message']['chat']['id']
                text = update['message']['text']

                if text == '/start':
                    send_message(chat_id, "🧊 Блокчейн-раннер\n🏃 /run 5.2\n📱 Кнопка Mini App снизу!")
                elif text.startswith('/run '):
                    km = float(text.split()[1])
                    send_message(chat_id, "⏳ Пишу в блокчейн...")
                    threading.Thread(target=blockchain_tx, args=(chat_id, km)).start()
                elif text == '/stats':
                    runs = contract.functions.getRuns().call()
                    total_km = sum(runs) / 1000
                    send_message(chat_id, f"📊 {len(runs)} пробежек\n📏 {total_km:.1f} км всего")
        except:
            time.sleep(5)

# MINI APP РОУТЫ
@app.route('/')
def home():
    return jsonify({
        "status": "FreshRunner LIVE 🏃‍♂️🔗 Sepolia",
        "endpoints": ["/logrun POST km=5.2", "/blockchain/stats GET", "/health"],
        "runs": 0,
        "version": "02.02.2026 Norilsk Blockchain Runner"
    })

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/blockchain/logrun', methods=['POST'])
def logrun():
    data = request.json
    km = float(data.get('distance', 5.2))
    km_total = int(km * 1000)

    nonce = w3.eth.get_transaction_count(ACCOUNT)
    tx = contract.functions.logRun(km_total).build_transaction({
        'from': ACCOUNT, 'nonce': nonce, 'gas': 200000, 'gasPrice': w3.to_wei('10', 'gwei')
    })
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"TX sent: 0x{tx_hash.hex()}")
    return jsonify({"status": "OK", "tx": "0x" + tx_hash.hex()})

@app.route('/blockchain/stats')
def stats():
    try:
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        runs_count = contract.functions.runs().call()
        total_distance = contract.functions.totalKm().call()
        return jsonify({
            "runs": int(runs_count),
            "total_km": int(total_distance),
            "last_updated": "blockchain"
        })
    except Exception as e:
        return jsonify({"error": f"Blockchain error: {str(e)}"}), 500

@app.route('/health')
def health():
    return jsonify({
        "status": "OK", 
        "web3_connected": w3.is_connected(),
        "contracts_db": os.path.exists('contracts.db'),
        "wallet": ACCOUNT[:10] + "..."
    })

if __name__ == '__main__':
    print("🚀 Flask + Telegram Mini App + Bot")
    print("🌐 http://127.0.0.1:5000/ — веб-интерфейс")
    print("📱 Telegram: /start")

    # Настройка порта для Render.com
    port = int(os.environ.get('PORT', 5000))

    # Flask в фоне + Telegram бот
    threading.Thread(target=lambda: app.run(debug=False, host='0.0.0.0', port=port), daemon=True).start()
    telegram_bot()
