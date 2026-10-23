#!/usr/bin/env python3
import os
import platform
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, "venv")
IS_WINDOWS = platform.system() == "Windows"

VENV_PY = os.path.join(VENV_DIR, "Scripts" if IS_WINDOWS else "bin",
                       "python.exe" if IS_WINDOWS else "python")

REQUIRED = ["flask", "scikit-learn", "pandas", "numpy", "joblib"]
MODEL_FILES = ["vectorizer.pkl", "stress_model.pkl",
               "theme_vectorizer.pkl", "theme_model.pkl", "metadata.json"]


def say(step, message):
    print(f"  [{step}] {message}", flush=True)


def banner():
    print()
    print("  " + "=" * 62)
    print("   MindCare - AI-Based Mental Health Monitoring System")
    print("   DBMS Mini Project  |  universal launcher")
    print("  " + "=" * 62)
    print()


def fail(message, hint=None):
    print()
    print(f"  ERROR: {message}")
    if hint:
        print(f"         {hint}")
    print()
    if IS_WINDOWS:
        input("  Press Enter to close...")
    sys.exit(1)


def check_python():
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 9):
        fail(f"Python 3.9 or newer is required (found {major}.{minor}).",
             "Install a newer Python from https://www.python.org/downloads/")
    say("1/5", f"Python {major}.{minor} on {platform.system()} - OK")


def ensure_venv():
    if os.path.exists(VENV_PY):
        say("2/5", "Virtual environment found")
        return
    say("2/5", "Creating the virtual environment (one-off)...")
    try:
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    except subprocess.CalledProcessError:
        fail("Could not create the virtual environment.",
             "On Debian/Ubuntu you may need:  sudo apt install python3-venv")
    if not os.path.exists(VENV_PY):
        fail("The virtual environment was created but its Python is missing.")


def packages_present():
    probe = ("import flask, sklearn, pandas, numpy, joblib")
    return subprocess.run([VENV_PY, "-c", probe],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def ensure_packages():
    if packages_present():
        say("3/5", "Dependencies already installed")
        return

    say("3/5", "Installing dependencies - this is the slow part, "
               "please wait a few minutes...")
    subprocess.run([VENV_PY, "-m", "pip", "install", "--quiet",
                    "--upgrade", "pip"], check=False)

    req = os.path.join(BASE_DIR, "requirements.txt")
    installed = False
    if os.path.exists(req):
        installed = subprocess.run(
            [VENV_PY, "-m", "pip", "install", "-r", req]).returncode == 0
        if not installed:
            say("3/5", "Pinned versions unavailable for this Python - "
                       "falling back to the latest compatible ones...")
    if not installed:
        if subprocess.run([VENV_PY, "-m", "pip", "install"] + REQUIRED).returncode != 0:
            fail("Dependency installation failed.",
                 "Check your internet connection and try running this again.")

    if not packages_present():
        fail("Dependencies installed but could not be imported.")


def ensure_models():
    model_dir = os.path.join(BASE_DIR, "ml", "models")
    missing = [f for f in MODEL_FILES
               if not os.path.exists(os.path.join(model_dir, f))]
    if not missing:
        say("4/5", "Trained models found")
        return
    say("4/5", "Training the models on the dataset (about 10 seconds)...")
    if subprocess.run([VENV_PY, os.path.join(BASE_DIR, "ml", "train_model.py")],
                      cwd=BASE_DIR).returncode != 0:
        fail("Model training failed.",
             "Check that data/synthetic_stress_dataset.csv is present.")


def needs_upgrade(path):
    import sqlite3
    conn = sqlite3.connect(path)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "aptitude_attempt" not in tables or "rescue_game" not in tables:
            return True
        levels = {r[0] for r in conn.execute("SELECT code FROM age_group")}
        return levels != {"JUNIOR", "INTERMEDIATE", "ADVANCED"}
    finally:
        conn.close()


def ensure_database():
    fresh = "--fresh" in sys.argv
    db_path = os.path.join(BASE_DIR, "mindcare.db")
    if os.path.exists(db_path) and not fresh:
        if needs_upgrade(db_path):
            say("5/5", "Updating your database with the latest features (your data is kept)...")
            if subprocess.run([VENV_PY, os.path.join(BASE_DIR, "init_db.py"), "--upgrade"],
                              cwd=BASE_DIR).returncode != 0:
                fail("Database upgrade failed.")
            return
        say("5/5", "Database found")
        return
    if fresh:
        say("5/5", "Building an EMPTY database - you will create the first account...")
        args = [VENV_PY, os.path.join(BASE_DIR, "init_db.py"), "--empty"]
    else:
        say("5/5", "Building and seeding the database (about 30 seconds)...")
        args = [VENV_PY, os.path.join(BASE_DIR, "init_db.py")]
    if subprocess.run(args, cwd=BASE_DIR).returncode != 0:
        fail("Database build failed.")


def launch():
    print()
    print("  Starting the server. Your browser will open shortly.")
    print("  Press Ctrl+C here to stop it.")
    print()
    try:
        subprocess.run([VENV_PY, os.path.join(BASE_DIR, "run.py")], cwd=BASE_DIR)
    except KeyboardInterrupt:
        print("\n  Server stopped.\n")


def main():
    banner()
    check_python()
    ensure_venv()
    ensure_packages()
    ensure_models()
    ensure_database()
    launch()
    if IS_WINDOWS:
        input("  Press Enter to close...")


if __name__ == "__main__":
    main()
