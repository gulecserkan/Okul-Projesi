"""Denetim logları için API yardımcıları."""

from __future__ import annotations

from typing import Optional

from core.config import get_api_base_url
from core.utils import api_request


def _endpoint() -> str:
    base = get_api_base_url().rstrip("/")
    return f"{base}/logs/"


def send_log(islem: str, *, detay: Optional[str] = None, ip_adresi: Optional[str] = None):
    """
    Denetim kaydı oluşturur.

    Args:
        islem: Yapılan işlem için kısa başlık (Türkçe).
        detay: Olayın açıklaması (Türkçe).
        ip_adresi: Biliniyorsa istemci IP bilgisi (opsiyonel).
    """
    if not islem:
        raise ValueError("islem parametresi zorunludur.")

    payload: dict[str, Optional[str]] = {"islem": islem}

    if detay is not None:
        payload["detay"] = detay
    if ip_adresi:
        payload["ip_adresi"] = ip_adresi

    return api_request("POST", _endpoint(), json=payload)


def safe_send_log(islem: str, *, detay: Optional[str] = None, ip_adresi: Optional[str] = None):
    """
    Ağ hatalarında uygulamayı durdurmadan log gönder.
    """
    try:
        resp = send_log(islem, detay=detay, ip_adresi=ip_adresi)
        status = getattr(resp, "status_code", None)
        if status and status not in (200, 201):
            print(f"[DBG] Log gönderimi başarısız ({status}): {islem}")
        return resp
    except Exception as exc:  # pragma: no cover - sadece ağ/JSON hatalarında tetiklenir
        print(f"[DBG] Log gönderilemedi: {exc}")
        return None
