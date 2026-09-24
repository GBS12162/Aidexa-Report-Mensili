from __future__ import annotations

import getpass
import json
import os

from cryptography.fernet import Fernet

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

def _prompt_credentials() -> dict[str, str]:
    return {
        "username": input("Oracle username: ").strip(),
        "password": getpass.getpass("Oracle password: "),
        "host": input("Oracle host: ").strip(),
        "port": input("Oracle port: ").strip(),
        "service_name": input("Oracle service name: ").strip(),
    }


def main() -> None:
    key_file = 'key.key'
    if not os.path.exists(key_file):
        key = generate_key()
        save_key(key, key_file)
    else:
        key = load_key(key_file)

    credentials = _prompt_credentials()

    encrypted_credentials = encrypt_credentials(credentials, key)
    
    with open('encrypted_credentials.json', 'w') as file:
        json.dump({'encrypted': encrypted_credentials}, file)

if __name__ == '__main__':
    main()