"""Stripe Checkout and webhook helpers for organization subscriptions."""

import stripe

from settings import Settings, get_settings


class BillingConfigurationError(RuntimeError):
    pass


class StripeBilling:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.stripe_secret_key and self.settings.stripe_webhook_secret and self.settings.stripe_price_id_pro)

    def _configure(self) -> None:
        if not self.configured:
            raise BillingConfigurationError("Stripe is not fully configured")
        stripe.api_key = self.settings.stripe_secret_key

    def create_checkout(self, organization_id: str, customer_email: str) -> str:
        self._configure()
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": self.settings.stripe_price_id_pro, "quantity": 1}],
            success_url=f"{self.settings.frontend_app_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{self.settings.frontend_app_url}/?checkout=cancelled",
            client_reference_id=organization_id,
            customer_email=customer_email,
            metadata={"organization_id": organization_id},
        )
        if not session.url:
            raise BillingConfigurationError("Stripe did not return a Checkout URL")
        return session.url

    def create_portal(self, customer_id: str) -> str:
        self._configure()
        session = stripe.billing_portal.Session.create(customer=customer_id, return_url=self.settings.frontend_app_url)
        return session.url

    def verify_event(self, payload: bytes, signature: str | None):
        self._configure()
        if not signature:
            raise BillingConfigurationError("Missing Stripe-Signature")
        try:
            return stripe.Webhook.construct_event(payload, signature, self.settings.stripe_webhook_secret)
        except Exception as exc:
            raise BillingConfigurationError("Invalid Stripe webhook signature") from exc


stripe_billing = StripeBilling()
