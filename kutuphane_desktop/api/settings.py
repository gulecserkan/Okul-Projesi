"""Sunucu ayarları ile ilgili API yardımcıları."""

from core.config import get_api_base_url
from core.utils import api_request


def _endpoint() -> str:
    base = get_api_base_url().rstrip("/")
    return f"{base}/settings/loans/"


def fetch_loan_policy():
    return api_request("GET", _endpoint())


def update_loan_policy(payload):
    return api_request("PUT", _endpoint(), json=payload)
