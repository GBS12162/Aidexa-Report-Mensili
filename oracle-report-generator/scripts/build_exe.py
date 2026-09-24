import os
import subprocess

def build_executable():
    pyinstaller_command = [
        "pyinstaller",
        "--onefile",
        "--add-data", "report.spec;.",
        "src/main.py"
    ]

    if os.path.exists(".env"):
        pyinstaller_command[2:2] = ["--add-data", ".env;."]
    
    try:
        subprocess.run(pyinstaller_command, check=True)
        print("Build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during the build process: {e}")

if __name__ == "__main__":
    build_executable()