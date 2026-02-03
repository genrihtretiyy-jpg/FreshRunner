from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from web3 import Web3
import requests
import time
import threading
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Для Telegram Mini App

# Загрузка переменных окружения
load_dotenv()

# Database initialization
def init_contracts_db():
    conn = sqlite3.connect('contracts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS contracts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  contract_addr TEXT,
                  total_km REAL,
                  deployed_at TEXT)''')
    conn.commit()
    conn.close()

# Web3 contract data
RUNNER_ABI = [
    {"inputs":[{"internalType":"uint256","name":"initialKm","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[],"name":"getKm","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getOwner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}
]

RUNNER_BYTECODE = "0x608060405234801561001057600080fd5b506040516101408061014083398101806040528101908080519060200190929190805190602001909291908051906020019092919080519060200190929190805190602001909291908051906020019092919050505060008054600160a060020a03191633179055806001819055505061010b806100906000396000f3fe60806040526004361061004c5763ffffffff7c01000000000000000000000000000000000000000000000000000000006000350416632db37e5b8114610051575b600080fd5b34801561005d57600080fd5b5061006661007c565b6040518082815260200191505060405180910390f35b6000543373ffffffffffffffffffffffffffffffffffffffff1614156100b057600054816000819055506001819055505b5056fea165627a7a723058200c1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef0029"

# Web3 Sepolia + WALLET с проверкой
w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_SEPOLIA_URL')))
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

if not PRIVATE_KEY:
    print("❌ PRIVATE_KEY НЕТ в .env!")
    raise ValueError("Установи PRIVATE_KEY в Render Environment Variables")

ACCOUNT = w3.eth.account.from_key(PRIVATE_KEY)
w3.eth.default_account = ACCOUNT.address

print(f"✅ Wallet: {ACCOUNT.address}")
print(f"✅ Web3: {w3.is_connected()}")

CONTRACT_ADDRESS = CONTRACT_ADDRESS = "0x54Fc6752C178274eD1bcb7d67ef5D68bAFe07Ccc"

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
    print("Telegram bot active")
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
        "status": "FreshRunner LIVE", 
        "endpoints": ["/logrun POST", "/blockchain/stats GET"]
    })

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/blockchain/logrun', methods=['POST'])
def logrun():
    try:
        km = float(request.json.get('km', 0.0))
        
        # МОК: генерируем фейковый контракт адрес
        import time
        contract_addr = f"0x{int(km*100):06x}NORILSK{int(time.time()) % 100000:05x}"
        
        # СОХРАНИМ РЕАЛЬНО в БД (эта часть работает!)
        init_contracts_db()
        conn = sqlite3.connect('contracts.db')
        c = conn.cursor()
        c.execute("INSERT INTO contracts (contract_addr, total_km, deployed_at) VALUES (?, ?, ?)",
                  (contract_addr, km, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return {
            "status": "DEPLOYED_TO_SEPOLIA_MOCK",
            "contract": contract_addr,
            "km": km,
            "message": "БД + /stats работают! Alchemy для реального deploy"
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/logrun', methods=['POST'])  
def simple_logrun():
    return logrun_endpoint()

def logrun_endpoint():  # ← новое имя!
    try:
        data = request.json
        km = float(data.get('km', 0.0))
        return {
            "status": "SUCCESS", 
            "km": km,
            "message": "Flask OK - готов к Web3!"
        }
    except Exception as e:
        return {"error": str(e)}, 400

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
    print("Flask + Telegram Mini App + Bot")
    print("http://127.0.0.1:5000/ — веб-интерфейс")
    print("Telegram: /start")

    # Настройка порта для Render.com
    port = int(os.environ.get('PORT', 5000))

    # Flask в фоне + Telegram бот
    threading.Thread(target=lambda: app.run(debug=False, host='0.0.0.0', port=port), daemon=True).start()
    telegram_bot()
