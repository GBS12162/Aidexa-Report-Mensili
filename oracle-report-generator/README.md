# oracle-report-generator
This project is a portable Python application designed to connect to an Oracle database, extract sales data, and generate an Excel report without requiring user intervention or knowledge of SQL or Python.

## Features
- Connects to an Oracle database using encrypted credentials.
- Handles authentication errors gracefully.
- Extracts sales data and generates a professionally formatted Excel report.
- Logs application events and errors without exposing sensitive information.

## Project Structure
```
oracle-report-generator/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── oracle_connection.py
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── data_extractor.py
│   │   ├── excel_formatter.py
│   │   └── pivot_generator.py
│   ├── security/
│   │   ├── __init__.py
│   │   └── credential_manager.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── scripts/
│   ├── encrypt_credentials.py
│   └── build_exe.py
├── config.py
├── requirements.txt
├── report.spec
├── .env.example
├── .gitignore
└── README.md
```

## Build Instructions
1. Install the required dependencies using pip:
   ```
   pip install -r requirements.txt
   ```
2. Run the encryption script to set up the initial credentials:
   ```
   python scripts/encrypt_credentials.py
   ```
3. Build the executable using PyInstaller:
   ```
   python scripts/build_exe.py
   ```

## PyInstaller Command
To build the application into a single executable, use the following command:
```
pyinstaller --onefile --add-data "path/to/your/.env;." --add-data "path/to/your/report.spec;." src/main.py
```

## Credential Encryption Strategy
1. Use the `Fernet` class from the `cryptography` package to encrypt and decrypt credentials.
2. Store the encryption key securely, possibly in an environment variable or a secure vault.
3. Ensure that the encrypted credentials are stored in a file that is not included in version control.

## Usage
After building the executable, run it to generate the Excel report. The application will automatically connect to the database using the encrypted credentials and produce the report without any user input required.

## Troubleshooting
- Ensure that the Oracle database is accessible and that the credentials are correctly encrypted.
- Check the logs for any errors related to database connections or data extraction.

This README provides a comprehensive overview of the project, its structure, and instructions for building and using the application.