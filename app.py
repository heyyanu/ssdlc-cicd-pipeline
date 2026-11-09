from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello, Secure Pipeline!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username == 'admin' and password == 'password123':
        return jsonify({"status": "success", "message": "Logged in!"})
    else:
        return jsonify({"status": "fail", "message": "Invalid credentials"}), 401

if __name__ == '__main__':
    app.run(debug=False)