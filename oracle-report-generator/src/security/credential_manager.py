def encrypt_credentials(credentials: dict, key: bytes) -> bytes:
    from cryptography.fernet import Fernet

    fernet = Fernet(key)
    encrypted_credentials = {k: fernet.encrypt(v.encode()).decode() for k, v in credentials.items()}
    return encrypted_credentials

def decrypt_credentials(encrypted_credentials: dict, key: bytes) -> dict:
    from cryptography.fernet import Fernet

    fernet = Fernet(key)
    decrypted_credentials = {k: fernet.decrypt(v.encode()).decode() for k, v in encrypted_credentials.items()}
    return decrypted_credentials

def load_encrypted_credentials(file_path: str) -> dict:
    import json

    with open(file_path, 'r') as file:
        encrypted_credentials = json.load(file)
    return encrypted_credentials

def save_encrypted_credentials(file_path: str, encrypted_credentials: dict) -> None:
    import json

    with open(file_path, 'w') as file:
        json.dump(encrypted_credentials, file)