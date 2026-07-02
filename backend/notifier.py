import requests
import os
from dotenv import load_dotenv

load_dotenv()

class LINENotifier:
    def __init__(self):
        self.token = os.getenv("LINE_NOTIFY_TOKEN")
        self.api_url = "https://notify-api.line.me/api/notify"

    def send_message(self, message: str) -> bool:
        """
        Sends a message to the configured LINE Notify endpoint.
        """
        if not self.token or self.token == "your_line_notify_token_here":
            print(f"[Notifier] LINE_NOTIFY_TOKEN not configured. Mocking notification: {message}")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}
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
