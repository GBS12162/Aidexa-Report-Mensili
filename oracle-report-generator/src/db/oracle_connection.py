def load_encrypted_credentials(file_path: str) -> dict:
    """Load encrypted credentials from a file and decrypt them."""
    from cryptography.fernet import Fernet
    import json
    import os

    # Load the encryption key from an environment variable
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("Encryption key not found in environment variables.")

    fernet = Fernet(key)

    with open(file_path, 'rb') as file:
        encrypted_data = file.read()

    decrypted_data = fernet.decrypt(encrypted_data).decode()
    return json.loads(decrypted_data)


def get_connection(settings: OracleSettings) -> oracledb.Connection:
    """Establish a connection to the Oracle database using decrypted credentials."""
    credentials = load_encrypted_credentials("path/to/encrypted_credentials.json")

    try:
        connection = oracledb.connect(
            user=credentials['username'],
            password=credentials['password'],
            dsn=build_dsn(settings)
        )
        return connection
    except oracledb.DatabaseError as e:
        error, = e.args
        raise ConnectionError(f"Database connection failed: {error.message}") from e


def build_dsn(settings: OracleSettings) -> str:
    """Build an Oracle DSN from the configured host parameters."""
    return oracledb.makedsn(
        host=settings.host,
        port=settings.port,
        service_name=settings.service_name,
    )