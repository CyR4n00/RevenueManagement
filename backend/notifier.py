import requests
import os
from dotenv import load_dotenv

load_dotenv()

class LINENotifier:
    def __init__(self):
        self.api_url = "https://notify-api.line.me/api/notify"

    def send_message(self, message: str) -> bool:
        """
        Sends a message to the configured LINE Notify endpoint.
        """
        from database import SessionLocal
        from models import DBSystemConfig

        token = None
        with SessionLocal() as db:
            sys_config = db.query(DBSystemConfig).first()
            token = sys_config.line_notify_token if sys_config and sys_config.line_notify_token else os.getenv("LINE_NOTIFY_TOKEN")

        if not token or token == "your_line_notify_token_here":
            print(f"[Notifier] LINE_NOTIFY_TOKEN not configured. Mocking notification: {message}")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        data = {"message": message}

        try:
            response = requests.post(self.api_url, headers=headers, data=data)
            if response.status_code == 200:
                print("[Notifier] LINE notification sent successfully.")
                return True
            else:
                print(f"[Notifier] Failed to send LINE notification: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[Notifier Error] {e}")
            return False

notifier_service = LINENotifier()
