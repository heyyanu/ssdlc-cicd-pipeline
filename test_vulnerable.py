import subprocess
import json
import hashlib
import requests
import bcrypt

def run_command(user_input):
    result = subprocess.call(
        ["ls", user_input]    
    )
    return result

def check_admin(password):
    import os
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if password == admin_password:
        return True
    return False

def load_user_data(data):
    user = json.loads(data)  
    return user


def hash_password(password):
    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    )
    return hashed

def get_data(url):
    response = requests.get(
        url,
        verify=True,    
        timeout=30      
    )
    return response.json()