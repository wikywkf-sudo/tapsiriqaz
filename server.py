import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = 'tapsiriqaz.db'
ADMIN_PASSWORD = "ZiyaAdmin777"  # Admin panelinin şifrəsi

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # İstifadəçilər cədvəli (Dəvət edən şəxs əlavə olundu)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0.0,
                referred_by TEXT
            )
        ''')
        # Tranzaksiyalar cədvəli
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                username TEXT,
                amount REAL,
                type TEXT DEFAULT 'task',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

init_db()

@app.route("/")
def home():
    return jsonify({"status": "running", "owner": "Ziya"})

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip().lower()
    referrer = data.get("referrer", "").strip().lower()
    
    if not username:
        return jsonify({"error": "İstifadəçi adı boş ola bilməz"}), 400
    
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Əgər dəvət edən varsa və özü-özünü dəvət etmirsə qeyd et
            ref_user = referrer if referrer and referrer != username else None
            cursor.execute("INSERT INTO users (username, referred_by) VALUES (?, ?)", (username, ref_user))
            conn.commit()
        return jsonify({"message": "Qeydiyyat uğurludur", "username": username}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "Giriş uğurludur", "username": username}), 200

@app.route("/api/balance/<username>", methods=["GET"])
def get_balance(username):
    username = username.strip().lower()
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
    if row:
        return jsonify({"username": username, "balance": row[0]}), 200
    return jsonify({"error": "İstifadəçi tapılmadı"}), 404

# ADGEM POSTBACK - 50% ADMIN KOMİSSİYASI VƏ %5 DƏVƏT BONUSU SİSTEMİ
@app.route("/postback", methods=["GET", "POST"])
def postback():
    args = request.args.to_dict() if request.method == "GET" else request.form.to_dict()
    transaction_id = args.get("transaction_id")
    username = args.get("user_id", "").strip().lower()
    raw_amount = args.get("amount") # AdGem-dən gələn ümumi pul (Məsələn 1.00 AZN)

    if not transaction_id or not username or not raw_amount:
        return jsonify({"error": "Parametrlər çatışmır"}), 400

    try:
        total_payout = float(raw_amount)
        # 100-də 50 qaydası: İstifadəçiyə pulun yarısı verilir, yarısı admin olaraq sizə qalır
        user_payout = total_payout * 0.50 

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # Təkrar yoxlanış
            cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
            if cursor.fetchone():
                return jsonify({"message": "Bu tapşırıq artıq işlənib"}), 200

            # İstifadəçini tap
            cursor.execute("SELECT referred_by FROM users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            if not user_row:
                return jsonify({"error": "İstifadəçi tapılmadı"}), 404
            
            referred_by = user_row[0]

            # İstifadəçinin balansını artır
            cursor.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (user_payout, username))
            cursor.execute("INSERT INTO transactions (id, username, amount, type) VALUES (?, ?, ?, 'task')", (transaction_id, username, user_payout))

            # DƏVƏT SİSTEMİ BONUSU: Dəvət edən şəxsə istifadəçi qazancının %10-u qədər əlavə bonus (Sizin cibinizdən çıxmır)
            if referred_by:
                ref_bonus = user_payout * 0.10
                cursor.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (ref_bonus, referred_by))
                cursor.execute("INSERT INTO transactions (id, username, amount, type) VALUES (?, ?, ?, 'referral')", (transaction_id + "_ref", referred_by, ref_bonus))

            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ZİYA ÜÇÜN ÖZƏL ADMİN PANELİ ENDPOINT-İ
@app.route("/api/admin/dashboard", methods=["POST"])
def admin_dashboard():
    data = request.json or {}
    password = data.get("password")
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Yanlış admin şifrəsi!"}), 403
    
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Bütün istifadəçiləri və balansları gətirir
        cursor.execute("SELECT username, balance, referred_by FROM users")
        users = [{"username": r[0], "balance": r[1], "referred_by": r[2]} for r in cursor.fetchall()]
        
        # Son tamamlanan tapşırıqlar
        cursor.execute("SELECT id, username, amount, type, timestamp FROM transactions ORDER BY timestamp DESC LIMIT 20")
        txs = [{"id": r[0], "username": r[1], "amount": r[2], "type": r[3], "date": r[4]} for r in cursor.fetchall()]
        
    return jsonify({"users": users, "transactions": txs})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

