from cryptography.fernet import Fernet
import os
import json

def generate_key() -> bytes:
    return Fernet.generate_key()

def save_key(key: bytes, key_file: str) -> None:
    with open(key_file, 'wb') as file:
        file.write(key)

def load_key(key_file: str) -> bytes:
    with open(key_file, 'rb') as file:
        return file.read()

def encrypt_credentials(credentials: dict, key: bytes) -> str:
    fernet = Fernet(key)
    credentials_json = json.dumps(credentials).encode()
    encrypted = fernet.encrypt(credentials_json)
    return encrypted.decode()

def main():
    key_file = 'key.key'
    if not os.path.exists(key_file):
        key = generate_key()
        save_key(key, key_file)
    else:
        key = load_key(key_file)

    credentials = {
        'username': 'your_username',
        'password': 'your_password',
        'host': 'your_host',
        'port': 'your_port',
        'service_name': 'your_service_name'
    }

    encrypted_credentials = encrypt_credentials(credentials, key)
    
    with open('encrypted_credentials.json', 'w') as file:
        json.dump({'encrypted': encrypted_credentials}, file)

if __name__ == '__main__':
    main()