import os
from dataclasses import replace

os.environ["APP_ENV"] = "demo"
os.environ["SUPABASE_AUTH_REQUIRED"] = "false"
os.environ["DEMO_BYPASS_BILLING"] = "false"
os.environ["ALLOW_SIMULATED_DATA"] = "true"

from billing import StripeBilling
from settings import get_settings


def test_placeholder_webhook_secret_is_not_production_ready():
    settings = replace(
        get_settings(),
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret="whsec_pending_configuration",
        stripe_price_id_pro="price_example",
    )

    assert StripeBilling(settings).configured is False


def test_complete_stripe_configuration_is_ready():
    settings = replace(
        get_settings(),
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret="whsec_example",
        stripe_price_id_pro="price_example",
    )

    assert StripeBilling(settings).configured is True
