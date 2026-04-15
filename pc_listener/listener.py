import ctypes
import os
import subprocess
import time

import requests
from dotenv import load_dotenv


load_dotenv()

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


def open_youtube():
    run_command('start msedge "https://www.youtube.com"')


def open_netflix():
    run_command('start msedge "https://www.netflix.com"')


def open_edge():
    run_command('start msedge')


def open_vscode():
    run_command('start code')


def open_spotify():
    run_command('start spotify')


def open_session_page():
    run_command(f'start msedge "{SESSION_PAGE_URL}?user_id={USER_ID}"')


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
    print("PC listener started")
    while True:
        try:
            status = detect_lock_state()
            post_heartbeat(status)

            selector_request = get_selector_request()
            if selector_request and status == "pc_on":
                open_session_page()
                ack_selector_request(selector_request["id"])
                print(f"Opened selector page for request {selector_request['id']}")

            action = get_next_action()
            if action:
                mode = action.get("mode")
                execute_mode(mode)
                ack_action(action["id"])
                print(f"Executed action {action['id']} mode={mode}")
        except requests.RequestException as ex:
            print(f"Network error: {ex}")
        except Exception as ex:
            print(f"Runtime error: {ex}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
