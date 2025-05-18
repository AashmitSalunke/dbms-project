from flask import Flask, render_template, request, redirect, session, jsonify, url_for, flash
from flask_bcrypt import Bcrypt
import mysql.connector
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)

# MySQL connection
conn = mysql.connector.connect(
    host='localhost',
    user='aashmit',
    password='aashmit123',
    database='crypto_trading'
)
cursor = conn.cursor(dictionary=True)

# Home
@app.route('/')
def home():
    return redirect('/login')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password))
        conn.commit()
        return redirect('/login')
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')
        else:
            return "Invalid credentials"
    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['username'])

# Chart data
@app.route('/api/chart-data')
def chart_data():
    cursor.execute("SELECT crypto_name, SUM(quantity) AS total_qty FROM trades WHERE user_id = %s GROUP BY crypto_name", (session['user_id'],))
    results = cursor.fetchall()
    labels = [row['crypto_name'].capitalize() for row in results]
    data = [float(row['total_qty']) for row in results]
    return jsonify({"labels": labels, "data": data})

# Trade history
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')
    cursor.execute("SELECT * FROM trades WHERE user_id = %s", (session['user_id'],))
    trades = cursor.fetchall()
    return render_template('history.html', trades=trades)

# API: Get real-time price data
@app.route('/api/prices')
def get_price_data():
    cryptos = ['bitcoin', 'ethereum', 'dogecoin', 'solana']
    prices = {}
    for coin in cryptos:
        try:
            r = requests.get(f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd')
            prices[coin] = r.json()[coin]['usd']
        except Exception:
            prices[coin] = None
    return jsonify(prices)

# Trade page
@app.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        crypto = request.form['crypto']
        trade_type = request.form['type']
        qty = float(request.form['quantity'])
        counterparty = request.form['counterparty']

        r = requests.get(f'https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd')
        price = r.json()[crypto]['usd']

        cursor.execute(
            "INSERT INTO trades (user_id, crypto_name, trade_type, quantity, price_per_coin, counterparty) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (session['user_id'], crypto, trade_type, qty, price, counterparty)
        )
        conn.commit()
        flash(f"Successfully {trade_type} {qty} {crypto} at ${price:.2f}/coin.", "success")
        return redirect('/dashboard')
    return render_template('trade.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)