from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Tuple
import html

from PyQt5.QtCore import QSizeF, Qt
from PyQt5.QtGui import QTextDocument, QFont, QTextOption
from PyQt5.QtPrintSupport import QPrinter

from api import auth
from core.config import load_settings
from core.receipt_templates import DEFAULT_RECEIPT_TEMPLATES
from printing.printer_guard import ensure_printer_ready, enforce_media_type


class ReceiptPrintError(RuntimeError):
    """Raised when receipt printing fails."""


_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value in (None, "", False):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")


def _format_amount(value, places: str = ".2f") -> str:
    quant = _to_decimal(value)
    try:
        quant = quant.quantize(Decimal("0.01"))
    except InvalidOperation:
        quant = Decimal("0.00")
    return format(quant, places)


def _student_name(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    first = student.get("ad") or student.get("first_name") or ""
    last = student.get("soyad") or student.get("last_name") or ""
    name = " ".join(part for part in (first, last) if part).strip()
    if name:
        return name
    return (
        student.get("ad_soyad")
        or student.get("full_name")
        or student.get("isim")
        or student.get("isim_soyisim")
        or ""
    )


def _student_class(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    sinif = student.get("sinif") or student.get("class")
    if isinstance(sinif, dict):
        return sinif.get("ad") or sinif.get("name") or ""
    return sinif or ""


def _student_role(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    return (
        student.get("rol")
        or student.get("rol_adi")
        or student.get("role")
        or student.get("status")
        or ""
    )


def _student_number(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    return (
        student.get("ogrenci_no")
        or student.get("no")
        or student.get("numara")
        or student.get("student_no")
        or ""
    )


def _student_phone(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    return (
        student.get("telefon")
        or student.get("phone")
        or student.get("gsm")
        or ""
    )


def _student_email(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    return student.get("email") or student.get("mail") or ""


def _loan_count(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return "0"
    if student.get("aktif_odunc_sayisi") is not None:
        return str(student.get("aktif_odunc_sayisi"))
    if student.get("loan_count") is not None:
        return str(student.get("loan_count"))
    active_loans = student.get("active_loans")
    if isinstance(active_loans, (list, tuple, set)):
        return str(len(active_loans))
    return "0"


def _mask_name(value: str, visible: int = 2) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    parts = text.split()
    masked_parts = []
    for part in parts:
        if len(part) <= visible:
            masked_parts.append(part)
        else:
            masked_parts.append(part[:visible] + "**")
    return " ".join(masked_parts)


def _parse_due_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            return None
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(clean)
        except ValueError:
            return None
    return None


def _nearest_return_deadline(student: Dict[str, Any]) -> str:
    if not isinstance(student, dict):
        return ""
    active_loans = student.get("active_loans")
    if not isinstance(active_loans, (list, tuple)):
        return ""
    best_dt = None
    best_display = ""
    for loan in active_loans:
        if not isinstance(loan, dict):
            continue
        due_val = loan.get("iade_tarihi") or loan.get("effective_iade_tarihi") or loan.get("due_date")
        if not due_val:
            continue
        dt = _parse_due_datetime(due_val)
        display = dt.strftime("%d.%m.%Y") if dt else str(due_val)
        if not best_display or (dt and (best_dt is None or dt < best_dt)):
            best_display = display
            best_dt = dt
    return best_display


def _format_debt_items(entries) -> str:
    if not entries:
        return "Borç kaydı bulunmuyor."
    lines = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        book = entry.get("kitap") or entry.get("book") or ""
        barcode = entry.get("barkod") or entry.get("barcode") or ""
        amount = _format_amount(entry.get("gecikme_cezasi"))
        paid = entry.get("gecikme_cezasi_odendi")
        status = "Ödendi" if paid else "Bekliyor"
        pieces = []
        if book:
            pieces.append(str(book))
        if barcode:
            pieces.append(f"#{barcode}")
        label = " ".join(pieces) if pieces else "Ceza"
        lines.append(f"- {label}: {amount} ₺ ({status})")
    return "\n".join(lines)


def build_receipt_context(summary: Dict[str, Any] | None, **overrides) -> Dict[str, str]:
    summary = summary or {}
    student = summary.get("student") or {}
    entries = summary.get("entries") or []
    now = datetime.now()
    remaining = summary.get("outstanding_total")
    operator_name = overrides.pop(
        "operator_name",
        auth.get_current_full_name() or auth.get_current_username() or "Kütüphane Personeli",
    )
    context: Dict[str, Any] = {
        "receipt_date": overrides.pop("receipt_date", now.strftime("%d.%m.%Y")),
        "receipt_time": overrides.pop("receipt_time", now.strftime("%H:%M")),
        "operator_name": operator_name,
        "student_full_name": _student_name(student),
        "student_number": _student_number(student),
        "student_class": _student_class(student),
        "student_role": _student_role(student),
        "student_phone": _student_phone(student),
        "student_email": _student_email(student),
        "loan_count": _loan_count(student),
        "remaining_debt": _format_amount(overrides.pop("remaining_debt", remaining)),
        "debt_items": _format_debt_items(entries),
        "return_deadline": overrides.pop("return_deadline", _nearest_return_deadline(student)),
        "payment_amount": _format_amount(overrides.pop("payment_amount", 0)),
        "payment_currency": overrides.pop("payment_currency", "TL"),
    }
    context.update(overrides)
    for key, value in list(context.items()):
        if value is None:
            context[key] = ""
        else:
            context[key] = str(value)
    student_mask = _mask_name(context.get("student_full_name"))
    operator_mask = _mask_name(context.get("operator_name"))
    context.setdefault("student_full_name_masked", student_mask or context.get("student_full_name", ""))
    context.setdefault("operator_name_masked", operator_mask or context.get("operator_name", ""))
    return context


def _render_template_text(template_body: str, context: Dict[str, str], *, escape_values: bool = True) -> str:
    def replacer(match):
        key = match.group(1)
        value = context.get(key, "")
        if escape_values:
            value = html.escape(value, quote=False)
        return value

    return _PLACEHOLDER_PATTERN.sub(replacer, template_body or "")


def render_receipt_html(template_body: str, context: Dict[str, str]) -> str:
    """Render receipt template as HTML (placeholder values are escaped)."""
    rendered = _render_template_text(template_body, context, escape_values=True)
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n")
    if not rendered.strip():
        rendered = "&nbsp;"
    style = (
        "<style>"
        "body{margin:0;padding:0;font-family:inherit;}"
        ".receipt-body{white-space:pre-line;}"
        ".receipt-body hr{margin:4px 0;height:2px;background:#000;border:none;display:block;}"
        "</style>"
    )
    return f"<html><head>{style}</head><body><div class='receipt-body'>{rendered}</div></body></html>"


def create_receipt_document(receipt_prefs: Dict[str, Any], html_text: str) -> Tuple[QTextDocument, float, float]:
    """
    Build a QTextDocument for preview/printing and return it along with the target page size in mm.
    """
    mm_w = float(receipt_prefs.get("mm_w", 70.0))
    mm_h = float(receipt_prefs.get("mm_h", 120.0))
    font_pt = int(receipt_prefs.get("font_pt", 10) or 10)
    margin_mm = 5.0

    doc = QTextDocument()
    option = QTextOption()
    option.setWrapMode(QTextOption.WordWrap)
    doc.setDefaultTextOption(option)

    font = QFont()
    font_family = receipt_prefs.get("font_family")
    if font_family:
        font.setFamily(font_family)
    font.setPointSize(font_pt)
    doc.setDefaultFont(font)

    margin_points = (margin_mm / 25.4) * 72.0
    doc.setDocumentMargin(margin_points)
    doc.setHtml(html_text or "&nbsp;")

    available_width_mm = max(10.0, mm_w - (margin_mm * 2))
    text_width_points = (available_width_mm / 25.4) * 72.0
    doc.setTextWidth(text_width_points)

    doc.adjustSize()
    layout = doc.documentLayout()
    content_height_points = layout.documentSize().height()
    content_height_mm = max(0.0, content_height_points * 25.4 / 72.0)
    min_height_mm = max(mm_h * 0.2, content_height_mm + margin_mm * 2)
    final_height_mm = max(min_height_mm, margin_mm * 2 + 1.0)

    total_width_points = (mm_w / 25.4) * 72.0
    total_height_points = (final_height_mm / 25.4) * 72.0
    doc.setPageSize(QSizeF(total_width_points, total_height_points))

    return doc, mm_w, final_height_mm


def _configure_printer(printer: QPrinter, receipt_prefs: Dict[str, Any], printing_prefs: Dict[str, Any]) -> Tuple[float, float]:
    mm_w = float(receipt_prefs.get("mm_w", 70.0))
    mm_h = float(receipt_prefs.get("mm_h", 120.0))
    dpi = int(receipt_prefs.get("dpi", 203))
    rotate = bool(receipt_prefs.get("rotate_print", False))

    if rotate:
        printer.setOrientation(QPrinter.Landscape if mm_w >= mm_h else QPrinter.Portrait)
    else:
        printer.setOrientation(QPrinter.Portrait if mm_h >= mm_w else QPrinter.Landscape)

    printer.setPaperSize(QSizeF(mm_w, mm_h), QPrinter.Millimeter)
    printer.setFullPage(True)
    try:
        printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
    except Exception:
        pass

    is_thermal = printing_prefs.get("receipt_is_thermal")
    if is_thermal is None:
        is_thermal = printing_prefs.get("label_is_thermal")

    if is_thermal:
        printer.setResolution(max(203, dpi))
        printer.setColorMode(QPrinter.GrayScale)
    else:
        printer.setResolution(dpi)
        printer.setColorMode(QPrinter.Color)

    return mm_w, mm_h


def _resolve_template(receipt_prefs: Dict[str, Any], template_key: str) -> Dict[str, str]:
    templates = receipt_prefs.get("templates") or {}
    template = templates.get(template_key)
    if not template:
        template = DEFAULT_RECEIPT_TEMPLATES.get(template_key)
    if not template:
        raise ReceiptPrintError(f"'{template_key}' fiş şablonu bulunamadı.")
    return template


def _stringify_context(context: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key, value in (context or {}).items():
        if value is None:
            result[key] = ""
        else:
            result[key] = str(value)
    return result


def print_receipt_from_template(template_key: str, context: Dict[str, Any]) -> None:
    settings = load_settings() or {}
    receipt_prefs = settings.get("receipts", {}) or {}
    printing_prefs = settings.get("printing", {}) or {}

    printer_name = printing_prefs.get("receipt_printer") or printing_prefs.get("label_printer")
    if not printer_name:
        raise ReceiptPrintError("Varsayılan fiş yazıcısı seçilmemiş. Yazıcı Ayarları sekmesinden bir yazıcı seçin.")

    template = _resolve_template(receipt_prefs, template_key)
    body = template.get("body", "").strip()
    if not body:
        raise ReceiptPrintError("Fiş şablonu boş. Lütfen Ayarlar > Fiş sekmesinden güncelleyin.")

    rendered_html = render_receipt_html(body, _stringify_context(context))
    if not rendered_html.strip():
        raise ReceiptPrintError("Fiş içeriği üretilemedi. Şablon ve verileri kontrol edin.")

    ensure_printer_ready(printer_name)
    enforce_media_type("receipt", printer_name, printing_prefs)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setPrinterName(printer_name)
    mm_w, _ = _configure_printer(printer, receipt_prefs, printing_prefs)

    doc, _, final_height_mm = create_receipt_document(receipt_prefs, rendered_html)
    printer.setPaperSize(QSizeF(mm_w, final_height_mm), QPrinter.Millimeter)

    try:
        doc.print_(printer)
    except Exception as exc:
        raise ReceiptPrintError(f"Fiş yazıcıya gönderilemedi: {exc}") from exc


def print_fine_payment_receipt(summary: Dict[str, Any] | None, payment_amount, *, payment_currency: str | None = None) -> None:
    amount = _format_amount(payment_amount)
    summary = summary or {}
    settings = load_settings() or {}
    receipt_prefs = settings.get("receipts", {}) or {}
    currency = payment_currency or receipt_prefs.get("currency") or "TL"
    remaining = summary.get("outstanding_total")
    context = build_receipt_context(
        summary,
        payment_amount=amount,
        payment_currency=currency,
        remaining_debt=_format_amount(remaining),
    )
    print_receipt_from_template("fine_payment", context)


def check_receipt_printer_status() -> Tuple[bool, str]:
    """Return (ok?, message). Message filled when printer cannot be used."""

    settings = load_settings() or {}
    printing_prefs = settings.get("printing", {}) or {}
    printer_name = printing_prefs.get("receipt_printer") or printing_prefs.get("label_printer")
    if not printer_name:
        return False, "Varsayılan fiş yazıcısı seçilmemiş. Yazıcı Ayarları sekmesinden bir fiş yazıcısı belirleyin."
    try:
        ensure_printer_ready(printer_name)
    except Exception as exc:
        return False, str(exc)
    try:
        enforce_media_type("receipt", printer_name, printing_prefs)
    except Exception as exc:
        return False, str(exc)
    return True, ""
