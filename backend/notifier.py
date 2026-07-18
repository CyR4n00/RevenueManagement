"""LINE Messaging API notification adapter (LINE Notify was discontinued)."""

import logging

import requests

from settings import Settings, get_settings

logger = logging.getLogger(__name__)


class LineMessagingNotifier:
    endpoint = "https://api.line.me/v2/bot/message/push"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.line_channel_access_token and self.settings.line_user_id)

    def send_message(self, message: str) -> bool:
        if not self.configured:
            logger.info("LINE Messaging API is not configured; notification was skipped")
            return False
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.settings.line_channel_access_token}"},
            json={"to": self.settings.line_user_id, "messages": [{"type": "text", "text": message[:5000]}]},
            timeout=10,
        )
        if response.ok:
            return True
        logger.warning("LINE Messaging API rejected notification: %s", response.status_code)
        return False


notifier_service = LineMessagingNotifier()
