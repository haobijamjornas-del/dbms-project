import os
import socket
import subprocess
import sys
import threading
import webbrowser

from backend import create_app
from backend.config import BaseConfig

app = create_app(os.environ.get("MINDCARE_ENV", "development"))


def find_free_port(start=5000, tries=20):
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit(f"No free port between {start} and {start + tries}.")


def open_browser(url, delay=1.5):
    def launch():
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", url], check=False)
            else:
                webbrowser.open_new_tab(url)
        except Exception:
            pass

    threading.Timer(delay, launch).start()


if __name__ == "__main__":
    if not os.path.exists(BaseConfig.DATABASE_PATH):
        raise SystemExit("mindcare.db not found. Run:  python init_db.py")

    port = find_free_port(5000)
    url = f"http://127.0.0.1:{port}"

    print()
    print("  " + "=" * 58)
    print("   MindCare - AI-Based Mental Health Monitoring System")
    print("  " + "=" * 58)
    print(f"   App        {url}")
    print(f"   REST API   {url}/api/v1")
    print( "   Sign in    admin / mindcare123")
    print( "   Stop       Ctrl+C")
    print("  " + "=" * 58)
    print()

    if "--no-browser" not in sys.argv and \
            os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        open_browser(url)

    app.run(debug=app.config["DEBUG"], port=port, use_reloader=True)
