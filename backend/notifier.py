"""Transactional email delivery for verified account alert recipients."""

import logging

import requests

from settings import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    endpoint = "https://api.resend.com/emails"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.resend_api_key
            and self.settings.alert_from_email
        )

    def send_alerts(self, recipient: str, facility_name: str, messages: list[str]) -> bool:
        if not self.configured:
            logger.info("Email delivery is not configured; notification was skipped")
            return False
        if not recipient or not messages:
            return False
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": self.settings.alert_from_email,
                "to": [recipient],
                "subject": f"【レベナビ】{facility_name}の価格変動アラート",
                "text": "レベナビで価格変動を検知しました。\n\n" + "\n".join(messages),
            },
            timeout=10,
        )
        if response.ok:
            return True
        logger.warning("Email provider rejected notification: %s", response.status_code)
        return False


notifier_service = EmailNotifier()
