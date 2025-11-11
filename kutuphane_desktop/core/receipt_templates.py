from __future__ import annotations

# Bu dosya fiş şablonları ve yer tutucular için merkezi kaynak sağlar.

RECEIPT_PLACEHOLDERS = [
    ("operator_name", "İşlemi yapan personel"),
    ("receipt_date", "Fiş tarihi (örn. 10.11.2025)"),
    ("receipt_time", "Fiş saati (örn. 14:32)"),
    ("student_full_name", "Öğrencinin adı soyadı"),
    ("student_number", "Öğrenci numarası"),
    ("student_class", "Öğrencinin sınıfı"),
    ("student_role", "Öğrencinin rolü / statüsü"),
    ("student_phone", "Öğrenci telefonu"),
    ("student_email", "Öğrenci e-posta adresi"),
    ("payment_amount", "Ödenen ceza tutarı"),
    ("payment_currency", "Para birimi"),
    ("remaining_debt", "Öğrencinin kalan borcu"),
    ("debt_items", "Borç kalemleri listesini metin olarak ekler"),
    ("loan_count", "Aktif ödünç sayısı"),
    ("return_deadline", "En yakın iade tarihi"),
]


RECEIPT_SCENARIOS = [
    ("fine_payment", "Ceza Ödemesi Fişi"),
    ("debt_statement", "Borcu Yoktur Bilgisi"),
    ("general_notice", "Bilgilendirme / Genel Fiş"),
]


DEFAULT_RECEIPT_TEMPLATES = {
    "fine_payment": {
        "title": "Ceza Ödemesi Fişi",
        "body": (
            "Okul Kütüphanesi\n"
            "Ceza Ödeme Makbuzu\n"
            "-------------------------\n"
            "Öğrenci : {{ student_full_name }} ({{ student_number }})\n"
            "Sınıf   : {{ student_class }} / {{ student_role }}\n"
            "Tarih   : {{ receipt_date }} {{ receipt_time }}\n"
            "Ödenen  : {{ payment_amount }} {{ payment_currency }}\n"
            "Kalan Borç : {{ remaining_debt }}\n"
            "İşlemi yapan: {{ operator_name }}\n"
            "\n"
            "Teşekkür ederiz."
        ),
    },
    "debt_statement": {
        "title": "Borcu Yoktur Belgesi",
        "body": (
            "Okul Kütüphanesi\n"
            "BORCU YOKTUR BİLGİSİ\n"
            "-------------------------\n"
            "Öğrenci : {{ student_full_name }} ({{ student_number }})\n"
            "Sınıf   : {{ student_class }} / {{ student_role }}\n"
            "Tarih   : {{ receipt_date }} {{ receipt_time }}\n"
            "\n"
            "Aktif ödünç sayısı : {{ loan_count }}\n"
            "Kalan borç         : {{ remaining_debt }}\n"
            "\n"
            "Bu tarih itibarıyla öğrenci kütüphanemize karşı borçlu değildir."
        ),
    },
    "general_notice": {
        "title": "Genel Bilgilendirme",
        "body": (
            "Okul Kütüphanesi\n"
            "Bilgilendirme\n"
            "-------------------------\n"
            "Öğrenci : {{ student_full_name }} ({{ student_number }})\n"
            "Tarih   : {{ receipt_date }} {{ receipt_time }}\n"
            "\n"
            "{{ debt_items }}\n"
            "\n"
            "İşlemi yapan: {{ operator_name }}\n"
        ),
    },
}
