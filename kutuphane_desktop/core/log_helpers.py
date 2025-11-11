"""
Shared helpers for producing consistent audit-log detail strings.

Each log payload is built out of standard sections (Kullanıcı, Öğrenci,
Kitap, Tarih, Ceza, Tutar). Using the helpers below ensures every module
produces comparable multi-line descriptions that the backend can parse.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping, Sequence


def _to_decimal(value):
    if isinstance(value, Decimal):
        return value
    if value in (None, "", False):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def format_currency(value, suffix: str = " ₺") -> str:
    dec = _to_decimal(value)
    if dec is None:
        return f"0,00{suffix}"
    try:
        dec = dec.quantize(Decimal("0.01"))
    except InvalidOperation:
        dec = Decimal("0.00")
    text = format(dec, ".2f")
    text = text.replace(".", ",")
    return f"{text}{suffix}"


def _format_person(entity, *, include_number: bool = True) -> str:
    if not entity:
        return "—"
    if isinstance(entity, str):
        return entity.strip() or "—"
    if isinstance(entity, Mapping):
        ad = (entity.get("ad") or "").strip()
        soyad = (entity.get("soyad") or "").strip()
        full = " ".join(part for part in [ad, soyad] if part)
        if not full:
            full = (entity.get("ad_soyad") or entity.get("fullname") or "").strip()
        if not full:
            full = (entity.get("display") or "").strip()
        if not full:
            full = (entity.get("name") or entity.get("username") or "").strip()
        number = (
            entity.get("ogrenci_no")
            or entity.get("no")
            or entity.get("kullanici_no")
        )
        if include_number and number:
            return f"{full or '—'} (No: {number})"
        return full or (number or "—")
    return str(entity)


def _format_book(book) -> str:
    if not book:
        return "—"
    if isinstance(book, str):
        return book
    if isinstance(book, Mapping):
        title = (book.get("baslik") or book.get("title") or book.get("ad") or "").strip()
        if title:
            return title
    return str(book)


def _format_datetime(value) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y %H:%M")
    try:
        text = str(value).strip()
        if not text:
            return "—"
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            # ISO date
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
        if len(text) >= 16 and "T" in text:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        pass
    return str(value)


def build_log_detail(
    *,
    user=None,
    role: str | None = None,
    student=None,
    student_no: str | None = None,
    book=None,
    barcode: str | None = None,
    date=None,
    date_label: str = "Tarih",
    penalty=None,
    penalty_status: str | None = None,
    amount=None,
    amount_label: str = "Tutar",
    extra: Sequence[str] | str | None = None,
) -> str:
    lines: list[str] = []

    if user:
        person = _format_person(user, include_number=False)
        if role:
            person = f"{person} (Rol: {role})"
        lines.append(f"Kullanıcı: {person}")

    if student:
        lines.append(f"Öğrenci: {_format_person(student)}")
    elif student_no:
        lines.append(f"Öğrenci No: {student_no}")

    if book or barcode:
        title = _format_book(book)
        if barcode:
            lines.append(f"Kitap: {title} (Barkod: {barcode})")
        else:
            lines.append(f"Kitap: {title}")

    if date:
        lines.append(f"{date_label}: {_format_datetime(date)}")

    if penalty is not None:
        penalty_text = format_currency(penalty)
        if penalty_status:
            penalty_text = f"{penalty_text} ({penalty_status})"
        lines.append(f"Ceza: {penalty_text}")

    if amount is not None:
        amount_text = format_currency(amount)
        label = amount_label or "Tutar"
        lines.append(f"{label}: {amount_text}")

    if extra:
        if isinstance(extra, str):
            lines.append(extra)
        else:
            for line in extra:
                if line:
                    lines.append(line)

    return "\n".join(lines) if lines else ""
