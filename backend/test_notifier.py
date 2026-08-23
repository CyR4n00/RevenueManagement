from dataclasses import replace
from types import SimpleNamespace

from notifier import EmailNotifier
from settings import get_settings


def test_email_notifier_uses_verified_recipient_and_alert_body(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return SimpleNamespace(ok=True, status_code=202)

    monkeypatch.setattr("notifier.requests.post", fake_post)
    notifier = EmailNotifier(replace(
        get_settings(), resend_api_key="re_test", alert_from_email="レベナビ <alerts@example.com>",
    ))

    delivered = notifier.send_alerts(
        "owner@example.com", "テスト旅館", ["競合Aが値上げしました", "競合Bが部屋なしです"],
    )

    assert delivered is True
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["json"]["to"] == ["owner@example.com"]
    assert "テスト旅館" in captured["json"]["subject"]
    assert "競合Bが部屋なしです" in captured["json"]["text"]


def test_email_notifier_skips_when_provider_is_not_configured(monkeypatch):
    monkeypatch.setattr(
        "notifier.requests.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not call provider")),
    )
    notifier = EmailNotifier(replace(get_settings(), resend_api_key="", alert_from_email=""))

    assert notifier.send_alerts("owner@example.com", "テスト旅館", ["alert"]) is False
