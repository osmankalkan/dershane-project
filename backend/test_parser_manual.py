"""
Manuel test scripti — TYT format parser'ı ve PDF Engine'i doğrular.

Kullanım:
    python test_parser_manual.py [pdf_yolu]

Varsayılan PDF yolu: sample_pdfs/tyt_örnek.pdf

Çıktılar:
  - Terminale okunabilir özet (parser + engine testleri)
  - output_sample.json  (tam ham + normalize JSON çıktısı)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Proje kök dizinini Python path'e ekle ─────────────────────────────────────
# Bu script backend/ altından çalıştırılır: python test_parser_manual.py
_BACKEND_DIR = Path(__file__).parent.resolve()
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.pdf_engine.parsers.parser_tyt_format import ParserTYTFormat  # noqa: E402

# ── Renkli terminal çıktısı ────────────────────────────────────────────────────
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _header(text: str) -> None:
    print(f"\n{_BOLD}{_CYAN}{'═' * 70}{_RESET}")
    print(f"{_BOLD}{_CYAN}  {text}{_RESET}")
    print(f"{_BOLD}{_CYAN}{'═' * 70}{_RESET}")


def _section(text: str) -> None:
    print(f"\n{_BOLD}{'─' * 60}{_RESET}")
    print(f"{_BOLD}  {text}{_RESET}")
    print(f"{'─' * 60}{_RESET}")


def _ok(text: str) -> None:
    print(f"  {_GREEN}✓{_RESET} {text}")


def _warn(text: str) -> None:
    print(f"  {_YELLOW}⚠{_RESET} {text}")


def _err(text: str) -> None:
    print(f"  {_RED}✗{_RESET} {text}")


def _info(text: str) -> None:
    print(f"    {text}")


# ── Ana test akışı ────────────────────────────────────────────────────────────


def main() -> None:
    # PDF yolu: argümandan veya varsayılan
    pdf_path_str = sys.argv[1] if len(sys.argv) > 1 else "sample_pdfs/tyt_örnek.pdf"
    pdf_path = Path(pdf_path_str)

    _header("TYT Format Parser — Manuel Test")
    print(f"  PDF: {pdf_path.resolve()}")

    if not pdf_path.exists():
        _err(f"PDF bulunamadı: {pdf_path}")
        sys.exit(1)

    parser = ParserTYTFormat()
    print(f"  Parser: {parser!r}")

    # ── 1. can_handle ──────────────────────────────────────────────────────────
    _section("1. can_handle()")
    can = parser.can_handle(pdf_path)
    if can:
        _ok("can_handle() → True  (parser bu formatı tanıdı)")
    else:
        _err("can_handle() → False  (parser bu formatı tanımıyor!)")
        sys.exit(1)

    # ── 2. extract() ──────────────────────────────────────────────────────────
    _section("2. extract()")
    try:
        raw = parser.extract(pdf_path)
        _ok("extract() başarıyla tamamlandı")
    except Exception as exc:
        _err(f"extract() HATA: {exc}")
        raise

    raw_students = raw.get("raw_students", [])
    raw_exam = raw.get("raw_exam_info", {})
    warnings = raw.get("warnings", [])
    errors = raw.get("errors", [])

    _info(f"Bulunan öğrenci sayısı : {len(raw_students)}")
    _info(f"Sınav bilgisi          : {raw_exam}")
    if warnings:
        _warn(f"{len(warnings)} uyarı var:")
        for w in warnings[:10]:
            _info(f"  • {w}")
        if len(warnings) > 10:
            _info(f"  ... ve {len(warnings) - 10} uyarı daha")
    if errors:
        for e in errors:
            _err(e)

    # Her öğrenci için kısa özet
    print()
    print(f"  {'#':<4} {'Ad Soyad':<30} {'Sınıf':<8} {'Puanı':<12} {'Özet Ders':<6} {'Analiz Satır'}")
    print(f"  {'─' * 4} {'─' * 30} {'─' * 8} {'─' * 12} {'─' * 6} {'─' * 12}")
    for i, s in enumerate(raw_students, 1):
        name = s.get("full_name", "?")[:28]
        klass = s.get("student_class", "-")
        score = s.get("tyt_score", "-") or "-"
        n_summary = len(s.get("summary_subjects", []))
        n_analysis = len(s.get("analysis_subjects", []))
        print(f"  {i:<4} {name:<30} {klass:<8} {score:<12} {n_summary:<6} {n_analysis}")

    # ── 3. normalize() ────────────────────────────────────────────────────────
    _section("3. normalize()")
    try:
        normalized = parser.normalize(raw)
        _ok("normalize() başarıyla tamamlandı")
    except Exception as exc:
        _err(f"normalize() HATA: {exc}")
        raise

    norm_students = normalized.get("student_results", [])
    norm_warnings = normalized.get("warnings", [])

    _info(f"Normalize edilen öğrenci : {len(norm_students)}")
    _info(f"Kurum                    : {normalized.get('institution_name', '-')}")
    if norm_warnings:
        _warn(f"{len(norm_warnings)} normalleştirme uyarısı")

    # İlk öğrenciyi detaylı göster
    if norm_students:
        _section("4. İlk Öğrenci Detaylı Özet (normalize() çıktısı)")
        first = norm_students[0]
        print(f"  Ad Soyad    : {first.get('full_name')}")
        print(f"  Öğr. Kodu   : {first.get('student_code') or '(yok)'}")
        print(f"  Sınıf       : {first.get('student_class') or '(yok)'}")
        print(f"  TYT Puanı   : {first.get('tyt_score') or '(yok)'}")
        results = first.get("subject_results", [])
        print(f"  Sonuç satırı: {len(results)} adet")
        print()

        # Ders bazında özet: toplam kazanım sayısı
        from collections import Counter

        subject_counts: Counter[str] = Counter()
        for r in results:
            subject_counts[r.get("subject_name", "?")] += 1

        print(f"  {'Ders':<45} {'Satır Sayısı'}")
        print(f"  {'─' * 45} {'─' * 12}")
        for subj, cnt in subject_counts.most_common():
            print(f"  {subj:<45} {cnt}")

        # İlk 10 satır
        print()
        print("  İlk 10 sonuç satırı:")
        print(f"  {'Ders':<20} {'Konu/Kazanım':<40} {'S':>3} {'D':>3} {'Y':>3} {'B':>3} {'%':>6}")
        print(f"  {'─' * 20} {'─' * 40} {'─' * 3} {'─' * 3} {'─' * 3} {'─' * 3} {'─' * 6}")
        for r in results[:10]:
            subj = (r.get("subject_name") or "")[:18]
            desc = (r.get("outcome_description") or "")[:38]
            s_ = r.get("total_questions", 0)
            d_ = r.get("correct", 0)
            y_ = r.get("wrong", 0)
            b_ = r.get("blank", 0)
            pct = r.get("success_pct", "-")
            print(f"  {subj:<20} {desc:<40} {s_:>3} {d_:>3} {y_:>3} {b_:>3} {str(pct):>6}")

    # ── 5. PDFEngine.process() entegrasyon testi ──────────────────────────────
    _section("5. PDFEngine.process() — Entegrasyon Testi")
    from app.pdf_engine.engine import PDFEngine

    engine = PDFEngine()
    try:
        eng_result = engine.process(pdf_path)
        if eng_result.ok:
            _ok(f"engine.process() → {eng_result.status}")
        elif eng_result.needs_review:
            _warn(f"engine.process() → {eng_result.status} ({eng_result.review_reason})")
        else:
            _err(f"engine.process() → {eng_result.status} ({eng_result.review_reason})")

        _info(f"Parser        : {eng_result.parser_name}")
        _info(f"Confidence    : {eng_result.confidence}")
        _info(f"Öğrenci sayısı: {len(eng_result.normalized_data['student_results']) if eng_result.normalized_data else 0}")
        _info(f"Uyarı sayısı  : {len(eng_result.warnings)}")

        if eng_result.validation_errors:
            _warn(f"{len(eng_result.validation_errors)} doğrulama hatası:")
            for e in eng_result.validation_errors[:5]:
                _info(f"  • {e[:80]}")
        else:
            _ok("Tüm subject_result satırları validator'dan geçti")

        if eng_result.review_detail:
            _info(f"Review detay  : {eng_result.review_detail[:80]}")

    except Exception as exc:
        _err(f"engine.process() HATA: {exc}")
        raise

    # ── 6. JSON çıktısı ───────────────────────────────────────────────────────
    _section("6. JSON Çıktısı")
    output_path = Path("output_sample.json")
    output_data = {
        "raw": raw,
        "normalized": normalized,
        "engine_result": {
            "status": eng_result.status,
            "parser_name": eng_result.parser_name,
            "confidence": eng_result.confidence,
            "validation_errors": eng_result.validation_errors,
            "warnings": eng_result.warnings,
            "review_reason": eng_result.review_reason,
        },
    }
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    _ok(f"Kaydedildi → {output_path.resolve()}")
    _info(f"Dosya boyutu: {output_path.stat().st_size / 1024:.1f} KB")

    _header("Test tamamlandı ✓")


if __name__ == "__main__":
    main()
