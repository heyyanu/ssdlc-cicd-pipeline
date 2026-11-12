import subprocess
import pickle
import hashlib
import requests

# Vulnerability 1 — Command Injection (B602)
def run_command(user_input):
    result = subprocess.call(user_input, shell=True)
    return result

# Vulnerability 2 — Hardcoded Password (B105)
def check_admin(password):
    admin_password = "admin123"
    if password == admin_password:
        return True
    return False

# Vulnerability 3 — Pickle Deserialization (B301)
def load_user_data(data):
    user = pickle.loads(data)
    return user

# Vulnerability 4 — Weak Hashing (B303)
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# Vulnerability 5 — SSL Verification Disabled (B501)
def get_data(url):
    response = requests.get(url, verify=False)
    return response.json()