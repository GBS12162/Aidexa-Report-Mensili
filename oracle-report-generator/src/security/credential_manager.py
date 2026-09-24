from __future__ import annotations

import json
from pathlib import Path

from cryptography.fernet import Fernet


def encrypt_credentials(credentials: dict[str, str], key: bytes) -> dict[str, str]:
    fernet = Fernet(key)
    encrypted_credentials = {k: fernet.encrypt(v.encode()).decode() for k, v in credentials.items()}
    return encrypted_credentials

def decrypt_credentials(encrypted_credentials: dict[str, str], key: bytes) -> dict[str, str]:
    fernet = Fernet(key)
    decrypted_credentials = {k: fernet.decrypt(v.encode()).decode() for k, v in encrypted_credentials.items()}
    return decrypted_credentials

def load_encrypted_credentials(file_path: str, key_file: str) -> dict[str, str]:
    with open(file_path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    encrypted = payload.get("encrypted")
    if not isinstance(encrypted, str):
        raise ValueError("Missing encrypted credential payload")

    key = Path(key_file).read_bytes()
    decrypted_json = Fernet(key).decrypt(encrypted.encode()).decode("utf-8")
    return json.loads(decrypted_json)

def save_encrypted_credentials(file_path: str, encrypted_credentials: dict[str, str]) -> None:
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(encrypted_credentials, file)