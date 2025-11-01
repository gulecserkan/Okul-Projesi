"""Sunucu ayarları ile ilgili API yardımcıları."""

from core.config import get_api_base_url
from core.utils import api_request


def _endpoint() -> str:
    base = get_api_base_url().rstrip("/")
    return f"{base}/settings/loans/"


def fetch_loan_policy():
    return api_request("GET", _endpoint())


def update_loan_policy(payload, *, partial=False):
    method = "PATCH" if partial else "PUT"
    return api_request(method, _endpoint(), json=payload)


def fetch_role_loan_policies():
    base = get_api_base_url().rstrip("/")
    return api_request("GET", f"{base}/settings/loans/roles/")


def update_role_loan_policies(policies):
    base = get_api_base_url().rstrip("/")
    return api_request("PUT", f"{base}/settings/loans/roles/", json=policies)


def fetch_notification_settings():
    base = get_api_base_url().rstrip("/")
    return api_request("GET", f"{base}/settings/notifications/")


def update_notification_settings(payload, *, partial=False):
    base = get_api_base_url().rstrip("/")
    method = "PATCH" if partial else "PUT"
    return api_request(method, f"{base}/settings/notifications/", json=payload)
