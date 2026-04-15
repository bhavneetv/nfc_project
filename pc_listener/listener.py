import ctypes
import os
import subprocess
import time
import webbrowser
import logging
import shutil
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

# Setup logging to file (for pythonw.exe which has no console)
log_file = os.path.join(os.path.dirname(__file__), "listener.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also print to console if there is one
    ]
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
USER_ID = os.getenv("USER_ID", "demo-user")
DEVICE_ID = os.getenv("DEVICE_ID", "windows-main")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
SESSION_PAGE_URL = os.getenv("SESSION_PAGE_URL", f"{API_BASE_URL}/select.html")


def detect_lock_state() -> str:
    user32 = ctypes.windll.User32
    hdesktop = user32.OpenInputDesktop(0, False, 0x0100)
    if hdesktop == 0:
        return "pc_locked"
    user32.CloseDesktop(hdesktop)
    return "pc_on"


def post_heartbeat(status: str):
    requests.post(
        f"{API_BASE_URL}/api/pc/heartbeat",
        json={"device_id": DEVICE_ID, "user_id": USER_ID, "status": status},
        timeout=10,
    )


def get_next_action():
    resp = requests.get(f"{API_BASE_URL}/api/pc/next-action", params={"user_id": USER_ID}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("action")


def get_selector_request():
    resp = requests.get(f"{API_BASE_URL}/api/pc/selector-request", params={"user_id": USER_ID}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("request")


def ack_selector_request(request_id: int):
    requests.post(f"{API_BASE_URL}/api/pc/selector-ack", json={"request_id": request_id}, timeout=10)


def ack_action(action_id: int):
    requests.post(f"{API_BASE_URL}/api/pc/ack", json={"action_id": action_id}, timeout=10)


def run_command(command: str):
    subprocess.Popen(command, shell=True)


def start_app(target: str):
    """Launch app/URL using PowerShell (properly handles user session from background process)."""
    try:
        logger.info(f"Starting app/URL: {target}")
        
        if target.startswith(('http://', 'https://')):
            # URLs - open with default browser via PowerShell
            cmd = f'powershell -NoProfile -WindowStyle Hidden -Command "Start-Process \'{target}\'"'
        elif target == 'spotify':
            cmd = f'powershell -NoProfile -WindowStyle Hidden -Command "Start-Process \'spotify\'"'
        elif target == 'code':
            cmd = f'powershell -NoProfile -WindowStyle Hidden -Command "Start-Process \'code\'"'
        elif target == 'msedge':
            cmd = f'powershell -NoProfile -WindowStyle Hidden -Command "Start-Process \'msedge\'"'
        else:
            logger.error(f"Unknown app: {target}")
            return
        
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    except Exception as e:
        logger.error(f"Failed to start '{target}': {e}")


def open_youtube():
    start_app('https://www.youtube.com')


def open_netflix():
    start_app('https://www.netflix.com')


def open_edge():
    start_app('msedge')


def open_vscode():
    start_app('code')


def open_spotify():
    start_app('spotify')


def open_session_page():
    webbrowser.open(f"{SESSION_PAGE_URL}?user_id={USER_ID}")


def enable_focus_mode():
    # Windows Focus Assist has no stable free public CLI API; keep this as a no-op hook.
    pass


def execute_mode(mode: str):
    status = detect_lock_state()
    if status == "pc_locked":
        open_session_page()
        return

    if mode == "study":
        enable_focus_mode()
        open_youtube()
    elif mode == "coding":
        enable_focus_mode()
        open_vscode()
        open_spotify()
        open_edge()
    elif mode == "fun":
        open_youtube()
        open_netflix()
        open_edge()


def main():
    logger.info("PC listener started")
    while True:
        try:
            status = detect_lock_state()
            post_heartbeat(status)

            selector_request = get_selector_request()
            if selector_request and status == "pc_on":
                open_session_page()
                ack_selector_request(selector_request["id"])
                logger.info(f"Opened selector page for request {selector_request['id']}")

            action = get_next_action()
            if action:
                mode = action.get("mode")
                execute_mode(mode)
                ack_action(action["id"])
                logger.info(f"Executed action {action['id']} mode={mode}")
        except requests.RequestException as ex:
            logger.error(f"Network error: {ex}")
        except Exception as ex:
            logger.error(f"Runtime error: {ex}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
