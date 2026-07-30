"""
PDF parser çıktısı için veri tutarlılık doğrulayıcısı.

Sorumluluk (mimari-sablon.md §4, P3 — Sessiz hata yok):
  Şüpheli veya tutarsız veri hiçbir zaman otomatik kaydedilmez.
  Bu modül, normalizer çıktısının veritabanına yazılmadan önce
  iş kurallarına uyduğunu doğrular.

Doğrulanan kurallar:
  R1 — Sayı tutarlılığı : correct + wrong + blank == total_expected
  R2 — Negatif değer yok: her sayı alanı >= 0 olmalı
  R3 — Toplam pozitif  : total_expected > 0 olmalı
  R4 — Tip güvenliği   : tüm alanlar int (veya int'e dönüştürülebilir)
  R5 — Zorunlu alan    : beklenen 4 anahtar dict'te bulunmalı

measured=False olan kayıtlar R1 kontrolünden muaftır (ADR-004):
  "Ölçülmedi" anlamına gelen satırlarda D+Y+B=0 normal bir durumdur.

Kullanım:
    from app.pdf_engine.validator import validate_result_counts, ValidationError

    try:
        validate_result_counts({"correct": 5, "wrong": 2, "blank": 3, "total_expected": 10})
    except ValidationError as exc:
        # review_queue'ya "VALIDATION_FAILED" olarak ekle
        ...
"""

from __future__ import annotations

from typing import Any

# ── Özel hata sınıfı ─────────────────────────────────────────────────────────

REQUIRED_KEYS: frozenset[str] = frozenset({"correct", "wrong", "blank", "total_expected"})


class ValidationError(Exception):
    """Veri tutarlılık doğrulaması başarısız olduğunda fırlatılır.

    Attributes:
        message:  İnsan tarafından okunabilir hata açıklaması.
        field:    Hatanın kaynaklandığı alan adı (biliniyorsa).
        context:  Hatayla ilgili ek sayısal bağlam (beklenen, bulunan vb.).
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.context = context or {}

    def __repr__(self) -> str:
        return f"ValidationError(field={self.field!r}, message={self.message!r}, context={self.context})"


# ── Yardımcı: tek alan doğrulama ─────────────────────────────────────────────


def _to_int(value: Any, field: str) -> int:
    """Değeri int'e çevirir; başarısız olursa ValidationError fırlatır."""
    if isinstance(value, bool):
        # bool, int'in alt sınıfıdır; True/False hatalı girdi sayılır.
        raise ValidationError(
            message=f"'{field}' alanı int olmalıdır, bool alındı.",
            field=field,
            context={"received": value},
        )
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            message=f"'{field}' alanı int'e dönüştürülemedi: {value!r}",
            field=field,
            context={"received": value},
        ) from exc


# ── Ana doğrulama fonksiyonu ──────────────────────────────────────────────────


def validate_result_counts(
    data: dict[str, Any],
    *,
    measured: bool = True,
) -> None:
    """Soru sayısı tutarlılığını ve alan kısıtlarını doğrular.

    Bu fonksiyon normalizer çıktısındaki her öğrenci-kazanım satırı için
    çağrılır. Başarısız olursa ValidationError fırlatır; sessizce geçmez (P3).

    Uygulanan kurallar:
        R1 (measured=True)  : correct + wrong + blank == total_expected
        R2                  : correct, wrong, blank >= 0
        R3                  : total_expected > 0
        R4                  : tüm değerler int (veya int'e dönüştürülebilir)
        R5                  : 4 zorunlu anahtar dict'te bulunmalı

    measured=False ise R1 atlanır — kazanım sınavda ölçülmedi (ADR-004).
    Ancak R2, R3, R4, R5 measured=False durumunda da uygulanır.

    Args:
        data: Doğrulanacak sözlük. Beklenen anahtarlar:
              {
                  "correct":        int,  # Doğru sayısı
                  "wrong":          int,  # Yanlış sayısı
                  "blank":          int,  # Boş sayısı
                  "total_expected": int,  # Rapordaki toplam soru sayısı
              }
        measured: Bu kazanım sınavda ölçüldü mü?
                  False ise D+Y+B == total_expected kontrolü (R1) atlanır.

    Returns:
        None — tüm kurallar sağlandığında sessizce döner.

    Raises:
        ValidationError: Herhangi bir kural ihlal edildiğinde.
                         Hata mesajı beklenen ve bulunan sayıları içerir.
    """
    # R5 — Zorunlu anahtar kontrolü
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ValidationError(
            message=f"Zorunlu alan(lar) eksik: {sorted(missing)}",
            field=None,
            context={"missing_keys": sorted(missing)},
        )

    # R4 — Tip dönüşümü (hatalı tipte ise ValidationError fırlatır)
    correct = _to_int(data["correct"], "correct")
    wrong = _to_int(data["wrong"], "wrong")
    blank = _to_int(data["blank"], "blank")
    total = _to_int(data["total_expected"], "total_expected")

    # R3 — Toplam pozitif olmalı
    if total <= 0:
        raise ValidationError(
            message=(f"'total_expected' sıfırdan büyük olmalıdır, alınan: {total}"),
            field="total_expected",
            context={"received": total},
        )

    # R2 — Negatif değer kontrolü
    for field_name, field_val in (
        ("correct", correct),
        ("wrong", wrong),
        ("blank", blank),
    ):
        if field_val < 0:
            raise ValidationError(
                message=(f"'{field_name}' negatif olamaz, alınan: {field_val}"),
                field=field_name,
                context={"received": field_val},
            )

    # R1 — D + Y + B == total_expected  (measured=False ise atla — ADR-004)
    if measured:
        actual_sum = correct + wrong + blank
        if actual_sum != total:
            raise ValidationError(
                message=(
                    f"Soru sayısı uyuşmazlığı: "
                    f"correct({correct}) + wrong({wrong}) + blank({blank}) = {actual_sum}, "
                    f"beklenen total_expected = {total}"
                ),
                field=None,
                context={
                    "correct": correct,
                    "wrong": wrong,
                    "blank": blank,
                    "actual_sum": actual_sum,
                    "total_expected": total,
                    "difference": actual_sum - total,
                },
            )
