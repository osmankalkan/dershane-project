"""
validate_result_counts() fonksiyonu için birim testleri.

Test stratejisi (mimari-sablon.md §11.2):
  - validator en yüksek öncelikli test hedefidir; veri doğruluğunu garantiler.
  - Her kural (R1–R5) için en az bir GEÇERLI ve bir BAŞARISIZ case yazılır.
  - Hata mesajlarının beklenen ve bulunan sayıları içerdiği doğrulanır.
  - measured=False bypass davranışı (ADR-004) ayrıca test edilir.

Çalıştırmak için (backend/ dizininden):
    pytest tests/test_pdf_engine/test_validator.py -v
"""

import sys
from pathlib import Path

import pytest

# Proje kökü sys.path'e ekleniyor (pytest conftest.py hazır olmadan da çalışsın)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.pdf_engine.validator import ValidationError, validate_result_counts

# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı sabitler
# ─────────────────────────────────────────────────────────────────────────────

VALID_DATA: dict = {
    "correct": 7,
    "wrong": 2,
    "blank": 1,
    "total_expected": 10,   # 7 + 2 + 1 = 10 ✓
}


def _make(**overrides) -> dict:
    """VALID_DATA'yı override'larla döndürür."""
    return {**VALID_DATA, **overrides}


# ─────────────────────────────────────────────────────────────────────────────
# R1 — Sayı tutarlılığı: correct + wrong + blank == total_expected
# ─────────────────────────────────────────────────────────────────────────────

class TestR1CountConsistency:

    def test_valid_counts_pass(self) -> None:
        """Geçerli veri — hata fırlatılmamalı."""
        validate_result_counts(VALID_DATA)  # exception yok

    def test_sum_greater_than_total_raises(self) -> None:
        """Toplam > total_expected."""
        data = _make(correct=8, wrong=2, blank=1, total_expected=10)
        # 8 + 2 + 1 = 11 ≠ 10
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        err = exc_info.value
        assert "11" in err.message          # bulunan toplam
        assert "10" in err.message          # beklenen total
        assert err.context["actual_sum"] == 11
        assert err.context["total_expected"] == 10
        assert err.context["difference"] == 1

    def test_sum_less_than_total_raises(self) -> None:
        """Toplam < total_expected."""
        data = _make(correct=3, wrong=2, blank=1, total_expected=10)
        # 3 + 2 + 1 = 6 ≠ 10
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        err = exc_info.value
        assert "6" in err.message
        assert "10" in err.message
        assert err.context["difference"] == -4

    def test_all_zero_with_matching_total_raises(self) -> None:
        """Sayılar sıfır ama total_expected de sıfır — R3 devreye girer."""
        data = _make(correct=0, wrong=0, blank=0, total_expected=0)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "total_expected"

    def test_all_blank_matches_total(self) -> None:
        """Tüm sorular boş bırakıldı — geçerli durum."""
        data = _make(correct=0, wrong=0, blank=10, total_expected=10)
        validate_result_counts(data)  # exception yok

    def test_all_correct_matches_total(self) -> None:
        """Tüm sorular doğru — geçerli durum."""
        data = _make(correct=20, wrong=0, blank=0, total_expected=20)
        validate_result_counts(data)

    def test_error_message_contains_all_components(self) -> None:
        """Hata mesajı correct, wrong, blank ve total değerlerini içermeli."""
        data = _make(correct=5, wrong=3, blank=1, total_expected=10)
        # 5 + 3 + 1 = 9 ≠ 10
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        msg = exc_info.value.message
        assert "5" in msg   # correct
        assert "3" in msg   # wrong
        assert "1" in msg   # blank
        assert "9" in msg   # actual_sum
        assert "10" in msg  # total_expected


# ─────────────────────────────────────────────────────────────────────────────
# R2 — Negatif değer yasak
# ─────────────────────────────────────────────────────────────────────────────

class TestR2NoNegatives:

    def test_negative_correct_raises(self) -> None:
        data = _make(correct=-1, wrong=5, blank=5, total_expected=10)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        err = exc_info.value
        assert err.field == "correct"
        assert "-1" in err.message

    def test_negative_wrong_raises(self) -> None:
        data = _make(correct=5, wrong=-2, blank=7, total_expected=10)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "wrong"

    def test_negative_blank_raises(self) -> None:
        data = _make(correct=5, wrong=5, blank=-1, total_expected=9)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "blank"

    def test_zero_values_are_valid(self) -> None:
        """Sıfır negatif değildir — geçerli olmalı."""
        data = _make(correct=0, wrong=0, blank=5, total_expected=5)
        validate_result_counts(data)


# ─────────────────────────────────────────────────────────────────────────────
# R3 — total_expected sıfırdan büyük olmalı
# ─────────────────────────────────────────────────────────────────────────────

class TestR3TotalPositive:

    def test_zero_total_raises(self) -> None:
        data = _make(correct=0, wrong=0, blank=0, total_expected=0)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        err = exc_info.value
        assert err.field == "total_expected"
        assert "0" in err.message

    def test_negative_total_raises(self) -> None:
        data = _make(correct=0, wrong=0, blank=0, total_expected=-5)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "total_expected"

    def test_positive_total_passes(self) -> None:
        validate_result_counts(VALID_DATA)


# ─────────────────────────────────────────────────────────────────────────────
# R4 — Tip güvenliği
# ─────────────────────────────────────────────────────────────────────────────

class TestR4TypeSafety:

    def test_string_digits_are_coerced(self) -> None:
        """Rakam string'leri int'e dönüştürülebilir — geçerli."""
        data = _make(correct="7", wrong="2", blank="1", total_expected="10")
        validate_result_counts(data)

    def test_float_integer_value_is_coerced(self) -> None:
        """10.0 gibi float'lar int'e dönüştürülebilir — geçerli."""
        data = _make(correct=7.0, wrong=2.0, blank=1.0, total_expected=10.0)
        validate_result_counts(data)

    def test_non_numeric_string_raises(self) -> None:
        data = _make(correct="yedi")
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "correct"

    def test_none_value_raises(self) -> None:
        data = _make(wrong=None)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "wrong"

    def test_bool_value_raises(self) -> None:
        """bool, int alt sınıfıdır ama burada geçersiz girdi sayılır."""
        data = _make(correct=True)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "correct"

    def test_list_value_raises(self) -> None:
        data = _make(blank=[1, 2])
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert exc_info.value.field == "blank"


# ─────────────────────────────────────────────────────────────────────────────
# R5 — Zorunlu anahtarlar
# ─────────────────────────────────────────────────────────────────────────────

class TestR5RequiredKeys:

    def test_missing_correct_raises(self) -> None:
        data = {k: v for k, v in VALID_DATA.items() if k != "correct"}
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert "correct" in exc_info.value.message

    def test_missing_total_expected_raises(self) -> None:
        data = {k: v for k, v in VALID_DATA.items() if k != "total_expected"}
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert "total_expected" in exc_info.value.message

    def test_empty_dict_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts({})
        ctx = exc_info.value.context
        assert "missing_keys" in ctx
        assert len(ctx["missing_keys"]) == 4

    def test_extra_keys_are_ignored(self) -> None:
        """Fazladan anahtar hata üretmemeli."""
        data = {**VALID_DATA, "student_name": "Ali Veli", "exam_id": "abc-123"}
        validate_result_counts(data)


# ─────────────────────────────────────────────────────────────────────────────
# measured=False bypass — ADR-004
# ─────────────────────────────────────────────────────────────────────────────

class TestMeasuredFalseBypass:
    """measured=False olduğunda R1 atlanmalıdır.

    Senaryo: Bir kazanım bu sınavda ölçülmedi (soru yoktu).
    correct=wrong=blank=0 olur ama total_expected > 0 olabilir.
    Bu durum "%0 başarı" değil, "veri yok" anlamına gelir (ADR-004).
    """

    def test_mismatched_counts_pass_when_not_measured(self) -> None:
        """D+Y+B ≠ total_expected ama measured=False → hata çıkmamalı."""
        data = _make(correct=0, wrong=0, blank=0, total_expected=5)
        # measured=True olsaydı (0+0+0=0 ≠ 5) hata verirdi
        validate_result_counts(data, measured=False)

    def test_r2_still_applies_when_not_measured(self) -> None:
        """Negatif değer measured=False olsa da hata üretir."""
        data = _make(correct=-1, wrong=0, blank=0, total_expected=5)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data, measured=False)
        assert exc_info.value.field == "correct"

    def test_r3_still_applies_when_not_measured(self) -> None:
        """total_expected sıfır olamaz measured=False olsa da."""
        data = _make(correct=0, wrong=0, blank=0, total_expected=0)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data, measured=False)
        assert exc_info.value.field == "total_expected"

    def test_r5_still_applies_when_not_measured(self) -> None:
        """Eksik anahtar measured=False olsa da hata üretir."""
        data = {"correct": 0, "wrong": 0, "blank": 0}  # total_expected yok
        with pytest.raises(ValidationError):
            validate_result_counts(data, measured=False)

    def test_valid_measured_true_still_works(self) -> None:
        """measured=True (varsayılan) normal çalışmaya devam eder."""
        validate_result_counts(VALID_DATA, measured=True)


# ─────────────────────────────────────────────────────────────────────────────
# ValidationError yapısı
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationErrorStructure:

    def test_error_has_message_attribute(self) -> None:
        data = _make(correct=99)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert hasattr(exc_info.value, "message")
        assert isinstance(exc_info.value.message, str)
        assert len(exc_info.value.message) > 0

    def test_error_has_context_dict(self) -> None:
        data = _make(correct=99)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert hasattr(exc_info.value, "context")
        assert isinstance(exc_info.value.context, dict)

    def test_error_is_exception_subclass(self) -> None:
        """ValidationError, normal Exception gibi yakalanabilmeli."""
        data = _make(correct=99)
        with pytest.raises(Exception):
            validate_result_counts(data)

    def test_str_representation(self) -> None:
        """str(exc) anlamlı bir mesaj döndürmeli."""
        data = _make(correct=99)
        with pytest.raises(ValidationError) as exc_info:
            validate_result_counts(data)
        assert str(exc_info.value)  # boş string değil
