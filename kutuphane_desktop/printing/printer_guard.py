"""Utility helpers for validating printer state before sending jobs."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from typing import Dict, Optional, Tuple

DEFAULT_MEDIA_TYPES: Dict[str, str] = {
    "label": "LabelWithMark",
    "receipt": "Continue",
}

JOB_TITLES: Dict[str, str] = {
    "label": "etiket",
    "receipt": "fiş",
}

MEDIA_SETTING_KEYS: Dict[str, str] = {
    "label": "label_media_type",
    "receipt": "receipt_media_type",
}

_LPOPTIONS_PATH = shutil.which("lpoptions")
_LPSTAT_PATH = shutil.which("lpstat")


def ensure_printer_ready(printer_name: str) -> None:
    """Raise if the given printer looks missing or reports an error state."""

    state, detail = query_printer_state(printer_name)
    if state in {"missing", "not_found"}:
        raise RuntimeError(detail or "Yazıcı bulunamadı.")
    if state == "error":
        raise RuntimeError(detail or "Yazıcı hazır değil.")


def enforce_media_type(job_kind: str, printer_name: str, printing_prefs: Optional[Dict]) -> None:
    """Ensure MediaType/Type matches expectation for the requested job."""

    expected = _expected_media_type(job_kind, printing_prefs)
    if not expected:
        return

    current = _read_media_type(printer_name)
    if not current:
        return

    if _normalized_media(current) == _normalized_media(expected):
        return

    job_title = JOB_TITLES.get(job_kind, job_kind or "yazdırma")
    allow_auto = _auto_fix_enabled(printing_prefs)

    if allow_auto:
        success, err = _set_media_type(printer_name, expected)
        if success:
            return
        detail = err or "Bilinmeyen hata"
        raise RuntimeError(
            "Type ayarı otomatik olarak '{expected}' değerine alınamadı: {detail}".format(
                expected=expected,
                detail=detail,
            )
        )

    raise RuntimeError(
        "'{printer}' yazıcısının Type seçeneği '{current}' görünüyor. {title} yazdırmadan önce "
        "'{expected}' değeri seçilmelidir.".format(
            printer=printer_name,
            current=current,
            title=job_title.capitalize(),
            expected=expected,
        )
    )


def query_printer_state(printer_name: str) -> Tuple[str, str]:
    name = (printer_name or "").strip()
    if not name:
        return "missing", "Varsayılan yazıcı seçilmemiş. Yazıcı Ayarları sekmesinden bir yazıcı seçin."

    result = _query_cups_state(name)
    if result:
        return result

    result = _query_lpstat_state(name)
    if result:
        return result

    result = _query_windows_state(name)
    if result:
        return result

    return "unknown", ""


def _query_cups_state(printer_name: str) -> Optional[Tuple[str, str]]:
    if sys.platform.startswith("win"):
        return None
    try:
        import cups  # type: ignore
    except Exception:
        return None

    try:
        conn = cups.Connection()
        info = conn.getPrinters().get(printer_name)
    except Exception as exc:
        return "unknown", f"CUPS durumu okunamadı: {exc}"

    if not info:
        return "not_found", f"'{printer_name}' yazıcısı sistemde bulunamadı."

    state = info.get("printer-state")
    reasons = info.get("printer-state-reasons") or []
    if isinstance(reasons, str):
        reasons = [part.strip() for part in reasons.split(",") if part.strip()]

    if state == 3 and (not reasons or "none" in reasons):
        return "ready", "hazır"
    if state == 4:
        return "busy", "Yazıcı şu anda yazdırıyor."

    detail = ", ".join(reasons) if reasons else "Yazıcı hazır görünmüyor."
    return "error", detail


def _query_lpstat_state(printer_name: str) -> Optional[Tuple[str, str]]:
    if not _LPSTAT_PATH or sys.platform.startswith("win"):
        return None
    try:
        proc = subprocess.run(
            [_LPSTAT_PATH, "-p", printer_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
    except Exception as exc:
        return "unknown", f"lpstat çalıştırılamadı: {exc}"

    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        if "unknown" in stderr.lower():
            return "not_found", f"'{printer_name}' yazıcısı bulunamadı."
        return "error", stderr or f"'{printer_name}' yazıcısı hazır değil."

    out = (proc.stdout or "").lower()
    if any(flag in out for flag in ("disabled", "stopped", "offline")):
        return "error", f"'{printer_name}' yazıcısı hazır değil (lpstat)."
    if "is printing" in out or "now printing" in out:
        return "busy", "Yazıcı şu anda yazdırıyor."
    if "is idle" in out:
        return "ready", "hazır"
    return "unknown", out.strip()


def _query_windows_state(printer_name: str) -> Optional[Tuple[str, str]]:
    if not sys.platform.startswith("win"):
        return None
    try:
        import win32print  # type: ignore
    except Exception:
        return None

    try:
        handle = win32print.OpenPrinter(printer_name)
    except Exception as exc:
        return "not_found", f"'{printer_name}' yazıcısına erişilemedi: {exc}"

    try:
        info = win32print.GetPrinter(handle, 2)
    finally:
        try:
            win32print.ClosePrinter(handle)
        except Exception:
            pass

    status = info.get("Status", 0) or 0
    err_flags = (
        getattr(win32print, "PRINTER_STATUS_ERROR", 0)
        | getattr(win32print, "PRINTER_STATUS_PAPER_OUT", 0)
        | getattr(win32print, "PRINTER_STATUS_OFFLINE", 0)
        | getattr(win32print, "PRINTER_STATUS_PAPER_JAM", 0)
        | getattr(win32print, "PRINTER_STATUS_DOOR_OPEN", 0)
    )
    if status & err_flags:
        return "error", "Yazıcı hazır değil."
    return "ready", "hazır"


def _expected_media_type(job_kind: str, prefs: Optional[Dict]) -> Optional[str]:
    key = MEDIA_SETTING_KEYS.get(job_kind)
    if not key:
        return None
    if prefs:
        candidate = prefs.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return DEFAULT_MEDIA_TYPES.get(job_kind)


def _auto_fix_enabled(prefs: Optional[Dict]) -> bool:
    if not prefs:
        return True
    value = prefs.get("auto_fix_media_type")
    if value is None:
        return True
    return bool(value)


def _read_media_type(printer_name: str) -> Optional[str]:
    if not _LPOPTIONS_PATH or sys.platform.startswith("win"):
        return None
    try:
        proc = subprocess.run(
            [_LPOPTIONS_PATH, "-p", printer_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    for token in _split_lpoptions(proc.stdout):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {"MediaType", "media-type", "MediaTypeDefault"}:
            return value
    return None


def _set_media_type(printer_name: str, value: str) -> Tuple[bool, Optional[str]]:
    if not _LPOPTIONS_PATH or sys.platform.startswith("win"):
        return False, "lpoptions komutu bulunamadı."
    try:
        proc = subprocess.run(
            [_LPOPTIONS_PATH, "-p", printer_name, "-o", f"MediaType={value}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
    except Exception as exc:
        return False, str(exc)

    if proc.returncode == 0:
        return True, None
    detail = (proc.stderr or proc.stdout or "").strip() or None
    return False, detail


def _split_lpoptions(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        return shlex.split(stripped)
    except ValueError:
        return stripped.split()


def _normalized_media(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum()).lower()

