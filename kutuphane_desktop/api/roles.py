"""Rol yönetimi için API yardımcıları."""

from core.config import get_api_base_url
from core.utils import api_request


def _base_url(path="roller/"):
    base = get_api_base_url().rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def list_roles():
    return api_request("GET", _base_url())


def update_role(role_id, payload, *, partial=True):
    method = "PATCH" if partial else "PUT"
    return api_request(method, _base_url(f"roller/{role_id}/"), json=payload)
