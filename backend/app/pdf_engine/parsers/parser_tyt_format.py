"""
TYT (Türkiye Yükseköğretim Yeterlilik Sınavı) formatı PDF parser'ı.

Desteklenen format özellikleri:
  - Tek PDF'te art arda birden fazla öğrenci sayfası
  - Her sayfa bir öğrenci bloğu; 'SINAV SONUÇ BELGESİ' başlığıyla başlar
  - Sayfa iki sütunlu layout:
      Sol  : öğrenci bilgileri + ders bazlı özet tablo + cevap anahtarı satırları
      Sağ  : "DERSLERE GÖRE BAŞARI ANALİZİ" (Ders > Konu/Kazanım hiyerarşisi)
  - 'Boş' sütunu PDF'te yoktur; Boş = Soru − Doğru − Yanlış hesaplanır
  - Net ve Başarı% değerleri negatif olabilir (yanlış ceza sistemi) — bu normaldir
  - "Cevap Anahtarı" + öğrenci işaretleri satırları tamamen atlanır

Mimari notu (mimari-sablon.md §4, P1):
  Bu dosya bağımsız bir plugin'dir. Diğer parser'lara dokunulmaz.
  Yeni format = yeni dosya kuralı uygulanır.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

from app.pdf_engine.parsers.base_parser import BasePDFParser

# ── Sabitler ──────────────────────────────────────────────────────────────────

PARSER_NAME = "TYT_FORMAT_V1"

# Sayfa başlığında aranan zorunlu anahtar kelime
_SINAV_BELGESI_MARKER = "SINAV SONUÇ BELGESİ"

# Sağ sütunun başladığı x koordinatı eşiği (pt cinsinden)
_RIGHT_COLUMN_X_THRESHOLD = 300.0

# Satırları gruplamak için dikey tolerans (pt)
_ROW_TOLERANCE_PT = 4.0

# Cevap anahtarı / öğrenci cevabı satırlarını atlatan pattern'lar
_SKIP_LINE_PATTERNS: list[str] = [
    r"^Cevap\s+Anahtarı",  # "Cevap Anahtarı B ADBDB..."
    r"^Soru\s+No\b",  # "Soru No 1234567..."
    r"^TYT\s+Türkçe\s+[a-zA-ZçÇğĞşŞüÜöÖıİ]",  # "TYT Türkçe bDBDBD..."
    r"^TYT\s+Sosyal\s+[a-zA-ZçÇğĞşŞüÜöÖıİ]",  # "TYT Sosyal cdaEABD..."
    r"^TYT\s+Matematik\s+[a-zA-ZçÇğĞşŞüÜöÖıİ]",  # "TYT Matematik EBCC..."
    r"^TYT\s+Fen\s+[a-zA-ZçÇğĞşŞüÜöÖıİ]",  # "TYT Fen ..."
]
_SKIP_PATTERNS_COMPILED = [re.compile(p) for p in _SKIP_LINE_PATTERNS]

# Özet tablodaki ders satırlarını tanımak için subject prefix'leri
_SUBJECT_PREFIXES = (
    "Türkçe",
    "Tarih-1",
    "Coğrafya-1",
    "Felsefe (Seçmeli)",
    "Felsefe",
    "Din Kül. ve Ahl. Bil.",
    "TYT Sosyal",
    "Matematik-1",
    "Fizik",
    "Kimya",
    "Biyoloji",
    "TYT Fen",
    "Toplam:",
)

# Analiz bölümündeki ders başlığı satırlarını tanımak için pattern
# Örn: "Türkçe 402216 55"  veya  "Tarih-1 5 2 3 40"  (sadece sayılar var)
# Ders başlıkları: metin + 2–3 rakam token ile biten satır (no S/D/Y/B% quadruple)
_SUBJECT_HEADER_RE = re.compile(
    r"^(TYT\s+)?"
    r"(Türkçe|Tarih-1|Coğrafya-1|Felsefe(?:\s+\(Seçmeli\))?|"
    r"Din\s+Kül\..*|Matematik-1|Fizik|Kimya|Biyoloji|TYT\s+Sosyal|TYT\s+Fen)"
    r"\s+(\d+)\s+(\d+)\s+(\d+)\s*(\d+)?\s*$"
)

# Sayısal sonuç quadruple'ı: 4 ardışık sayı (son N sayısı) — sağ sütun outcome satırı
# S D Y B%  →  son token % işareti olmadan sayısal değer (0, 100, -11 vb.)
_OUTCOME_NUMBERS_RE = re.compile(r"^(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s*$")


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────


def _group_words_into_rows(
    words: list[dict[str, Any]],
    tolerance: float = _ROW_TOLERANCE_PT,
) -> list[list[dict[str, Any]]]:
    """Kelimeleri dikey koordinatlarına göre satırlara gruplar.

    PDF'te aynı görsel satırdaki kelimeler tam aynı 'top' değerine sahip
    olmayabilir; bu nedenle ±tolerance pt içindeki kelimeler aynı satıra ait
    kabul edilir.

    Returns:
        Y koordinatına göre sıralanmış satır listesi. Her satır, o satırdaki
        kelimeleri x0'a göre (soldan sağa) sıralı döndürür.
    """
    if not words:
        return []

    # top'a göre sırala
    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))

    rows: list[list[dict[str, Any]]] = []
    current_row: list[dict[str, Any]] = [sorted_words[0]]
    current_top = sorted_words[0]["top"]

    for word in sorted_words[1:]:
        if abs(word["top"] - current_top) <= tolerance:
            current_row.append(word)
        else:
            rows.append(sorted(current_row, key=lambda w: w["x0"]))
            current_row = [word]
            current_top = word["top"]

    if current_row:
        rows.append(sorted(current_row, key=lambda w: w["x0"]))

    return rows


def _row_to_text(row: list[dict[str, Any]]) -> str:
    """Bir satırdaki kelimeleri boşlukla birleştirerek tek string döndürür."""
    return " ".join(w["text"] for w in row)


def _should_skip_line(text: str) -> bool:
    """Cevap anahtarı veya öğrenci işareti satırı mı? Atlanmalı mı?"""
    stripped = text.strip()
    for pattern in _SKIP_PATTERNS_COMPILED:
        if pattern.search(stripped):
            return True
    return False


def _safe_int(value: str, default: int = 0) -> int:
    """Dönüştürme hatası olursa default döndürür; gürültülü çıktı vermez."""
    try:
        return int(value.replace(",", ".").split(".")[0])
    except (ValueError, AttributeError):
        return default


def _safe_float(value: str, default: float = 0.0) -> float:
    """Virgüllü Türkçe sayı formatını float'a çevirir."""
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return default


# ── Ana Parser Sınıfı ─────────────────────────────────────────────────────────


class ParserTYTFormat(BasePDFParser):
    """TYT sınav sonuç belgesi formatı için PDF parser implementasyonu.

    Her çağrı için bir pdfplumber oturumu açar ve kapatır.
    Thread-safety: pdfplumber nesneleri paylaşılmaz; her extract() bağımsız.
    """

    parser_name: str = PARSER_NAME

    # ── can_handle ────────────────────────────────────────────────────────────

    def can_handle(self, pdf_path: Path) -> bool:
        """PDF bu formatta mı? İlk sayfada 'SINAV SONUÇ BELGESİ' ara.

        Hiçbir zaman exception fırlatmaz; tanımlanamayan formatta False döner.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    return False
                first_page_text = pdf.pages[0].extract_text() or ""
                return _SINAV_BELGESI_MARKER in first_page_text and not any(
                    k in first_page_text for k in ["LGS", "8.SINIF", "MADALYON"]
                )
        except Exception:  # noqa: BLE001
            return False

    # ── extract ───────────────────────────────────────────────────────────────

    def extract(self, pdf_path: Path) -> dict[str, Any]:
        """PDF'ten ham veriyi çeker; normalleştirme yapmaz.

        Her sayfa bir öğrenci bloğu olarak işlenir.

        Returns:
            {
                "raw_students": [...],   # Öğrenci başına ham veri
                "raw_exam_info": {...},  # Sınav adı, kurum vb.
                "warnings": [...],
                "errors": [...],
            }

        Raises:
            ExtractionError: PDF hiç açılamazsa (bozuk, şifreli vb.).
        """
        warnings: list[str] = []
        errors: list[str] = []
        raw_students: list[dict[str, Any]] = []
        raw_exam_info: dict[str, Any] = {}

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    try:
                        student_raw, exam_info, page_warnings = self._extract_student_page(page, page_num)
                        warnings.extend(page_warnings)

                        if student_raw:
                            raw_students.append(student_raw)

                        # Sınav bilgisini ilk sayfadan al (tüm sayfalarda aynı)
                        if not raw_exam_info and exam_info:
                            raw_exam_info = exam_info

                    except Exception as exc:  # noqa: BLE001
                        msg = f"Sayfa {page_num}/{total_pages} işlenirken hata: {exc}"
                        errors.append(msg)
                        warnings.append(msg)

        except Exception as exc:
            # Engelleyici hata — PDF hiç açılamıyor
            raise RuntimeError(f"PDF dosyası açılamadı: {pdf_path} — {exc}") from exc

        return {
            "raw_students": raw_students,
            "raw_exam_info": raw_exam_info,
            "warnings": warnings,
            "errors": errors,
        }

    # ── normalize ─────────────────────────────────────────────────────────────

    def normalize(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Ham parser çıktısını ortak NormalizedExamData formatına dönüştürür.

        extract() çıktısını alır; validator.py'nin anlayacağı standart yapıya
        çevirir.

        Returns:
            NormalizedExamData sözleşmesine uygun dict.

        Raises:
            NormalizationError: Öğrenci listesi tamamen boşsa.
        """
        warnings: list[str] = list(raw_data.get("warnings", []))
        raw_students: list[dict[str, Any]] = raw_data.get("raw_students", [])
        raw_exam: dict[str, Any] = raw_data.get("raw_exam_info", {})

        if not raw_students:
            raise ValueError("Normalleştirme başarısız: raw_students listesi boş.")

        normalized_students: list[dict[str, Any]] = []

        for raw_s in raw_students:
            try:
                normalized_s = self._normalize_student(raw_s)
                normalized_students.append(normalized_s)
            except Exception as exc:  # noqa: BLE001
                name = raw_s.get("full_name", "?")
                warnings.append(f"Öğrenci '{name}' normalleştirilemedi: {exc}")

        return {
            "exam_date": raw_exam.get("exam_date", ""),
            "institution_name": raw_exam.get("institution_name", ""),
            "source_format": PARSER_NAME,
            "student_results": normalized_students,
            "warnings": warnings,
        }

    # ── Özel: tek sayfa / tek öğrenci çekme ──────────────────────────────────

    def _extract_student_page(
        self,
        page: Any,
        page_num: int,
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        """Tek bir PDF sayfasından öğrenci verisini ve sınav bilgisini çeker.

        Returns:
            (student_raw, exam_info, warnings)
        """
        warnings: list[str] = []
        words = page.extract_words(use_text_flow=False)

        if not words:
            warnings.append(f"Sayfa {page_num}: kelime bulunamadı, atlandı.")
            return {}, {}, warnings

        # Sütunları ayır
        left_words = [w for w in words if w["x0"] < _RIGHT_COLUMN_X_THRESHOLD]
        right_words = [w for w in words if w["x0"] >= _RIGHT_COLUMN_X_THRESHOLD]

        left_rows = _group_words_into_rows(left_words)
        right_rows = _group_words_into_rows(right_words)

        # ── Sol sütun: başlık, öğrenci bilgisi, özet tablo ──
        exam_info = self._parse_exam_info(left_rows)
        student_meta = self._parse_student_meta(left_rows)
        summary_subjects = self._parse_summary_table(left_rows, warnings)

        # ── Sağ sütun: derslere göre başarı analizi ──
        analysis_subjects = self._parse_analysis_section(right_rows, warnings)

        student_raw: dict[str, Any] = {
            **student_meta,
            "summary_subjects": summary_subjects,
            "analysis_subjects": analysis_subjects,
            "page_num": page_num,
        }

        return student_raw, exam_info, warnings

    # ── Özel: Sol sütun parser'ları ──────────────────────────────────────────

    def _parse_exam_info(self, rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
        """Sınav adı ve kurum bilgisini sol sütun satırlarından çeker."""
        exam_name = ""
        institution_name = ""

        for row in rows[:6]:  # İlk 6 satıra bak
            text = _row_to_text(row)
            if _SINAV_BELGESI_MARKER in text:
                # "SINAV SONUÇ BELGESİ YKS - TYT 5. DENEME (1.OTURUM)"
                # Sağ kısım sınav adı olabilir ama bu satır sol sütunda sadece
                # "SINAV SONUÇ BELGESİ" içerir; sağ sütun kısmı ayrı word'lerden
                # oluşabilir — burada sadece marker kontrolü yapıyoruz.
                exam_name = text.strip()
            elif "/" in text and "SINAV" in text.upper():
                # "TEKİRDAĞ / ÇERKEZKÖY / SINAV KURS MERKEZİ"
                institution_name = text.strip()

        return {
            "exam_name": exam_name,
            "institution_name": institution_name,
            "exam_date": "",  # Bu formatta tarih yok
        }

    def _parse_student_meta(self, rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
        """Öğrenci adı, sıra numarası ve sınıf bilgisini çeker.

        Sol sütunda 'Öğrenci Numara Sınıf' başlığından sonraki satırda
        öğrenci adı (büyük harf), sıra numarası ve sınıf yer alır.

        Olası formatlar:
            "AHMET DURMUŞ 0"          →  ad=AHMET DURMUŞ, sıra=0, sınıf=""
            "AHMET ÇETİN 0 11"        →  ad=AHMET ÇETİN,  sıra=0, sınıf=11
            "NİSA DURSUN 0 11A"       →  ad=NİSA DURSUN,  sıra=0, sınıf=11A
            "NUR SENEM SARIKAYA 1072" →  ad=NUR SENEM SARIKAYA, sıra=1072, sınıf=""

        Kural: Büyük harfli adın arkasından rakam + (isteğe bağlı sınıf kodu) gelir.
        Sınıf kodu: rakamla başlar, harf içerebilir (11, 11A, 11B, 11F vb.).
        """
        full_name = ""
        student_code = ""
        student_class = ""
        tyt_score = None
        tyt_avg = None

        # Sınıf kodunu tanıyan regex: rakamla başlar, opsiyonel büyük harf içerir
        _class_re = re.compile(r"^\d+[A-ZÇĞŞÜÖİ]?$")

        found_header = False
        for row in rows:
            text = _row_to_text(row)

            # "Öğrenci Numara Sınıf" başlığını bul
            if "Öğrenci" in text and "Numara" in text and "Sınıf" in text:
                found_header = True
                continue

            if found_header and not full_name:
                tokens = text.split()
                if tokens and tokens[0][0].isupper():
                    # Tokenları sondan parse et:
                    # Son token → sınıf kodu (rakam+harf) veya sıra no
                    # Önceki token → sıra no (sadece rakam)
                    # Geri kalanlar → ad
                    remaining = list(tokens)

                    # Son token sınıf kodu mu? (11, 11A, 11B...)
                    if len(remaining) >= 2 and _class_re.match(remaining[-1]) and remaining[-2].isdigit():
                        student_class = remaining[-1]
                        remaining = remaining[:-1]  # sınıf kodunu çıkar

                    # Son token artık sıra/rank numarası (sadece rakam)
                    if remaining and remaining[-1].isdigit():
                        # sıra numarasını öğrenci adından ayır (student_code yok,
                        # bu PDF'te özgün ID bulunmuyor — sıra no kayda değmez)
                        remaining = remaining[:-1]

                    full_name = " ".join(remaining).strip()
                    found_header = False

            # TYT puanı: "240,678 212,510 2 6 63 64 439" gibi
            score_match = re.match(r"^(\d{1,3}[,\.]\d{3})\s+(\d{1,3}[,\.]\d{3})", text)
            if score_match:
                tyt_score = score_match.group(1)
                tyt_avg = score_match.group(2)

        return {
            "full_name": full_name.strip(),
            "student_code": student_code,
            "student_class": student_class,
            "tyt_score": tyt_score,
            "tyt_avg": tyt_avg,
        }

    def _parse_summary_table(
        self,
        rows: list[list[dict[str, Any]]],
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        """Sol sütundaki ders bazlı özet tabloyu çeker.

        Tablo format örneği (başlık satırı atlanır):
            Ders       Soru  Doğru  Yanlış  Net    %    ...
            Türkçe       40     22      16   18,00  45  ...
            Tarih-1       5      2       3    1,25  25  ...
            ...
            Toplam:     120     48      25   41,75  35  ...

        'Cevap Anahtarı' ve öğrenci cevap satırları atlanır.
        """
        subjects: list[dict[str, Any]] = []

        in_table = False  # "Ders Soru Doğru Yanlış Net" başlığını gördük mü?

        for row in rows:
            text = _row_to_text(row)

            # Cevap anahtarı / öğrenci işareti satırlarını atla
            if _should_skip_line(text):
                continue

            # Tablo başlığını tespit et
            if "Ders" in text and "Soru" in text and ("Doğru" in text or "Net" in text):
                in_table = True
                continue

            if not in_table:
                continue

            # Toplam satırı (özet tablo sonu)
            if text.startswith("Toplam:"):
                # Toplam satırını da kaydet ama tablo bitişini işaretle
                parts = text.split()
                if len(parts) >= 5:
                    try:
                        total_q = _safe_int(parts[1])
                        total_c = _safe_int(parts[2])
                        total_w = _safe_int(parts[3])
                        subjects.append(
                            {
                                "subject_name": "Toplam",
                                "total_questions": total_q,
                                "correct": total_c,
                                "wrong": total_w,
                                "blank": total_q - total_c - total_w,
                                "net": _safe_float(parts[4]) if len(parts) > 4 else 0.0,
                                "success_pct": _safe_float(parts[5]) if len(parts) > 5 else 0.0,
                                "is_total_row": True,
                            }
                        )
                    except Exception:  # noqa: BLE001
                        pass
                in_table = False
                continue

            # Boş veya çok kısa satırları atla
            tokens = text.split()
            if len(tokens) < 4:
                continue

            # Ders satırı tanıma: önce subject prefix kontrolü
            subject_name = self._detect_subject_name(text)
            if not subject_name:
                continue

            # Subject adından sonra kalan token'ları parse et
            # Format: <SubjectName> <Soru> <Doğru> <Yanlış> <Net> <Başarı%> [Ort. Snf] [Ort. Kurum] [Ort. Genel]
            rest = text[len(subject_name) :].split()
            if len(rest) < 3:
                continue

            try:
                total_q = _safe_int(rest[0])
                correct = _safe_int(rest[1])
                wrong = _safe_int(rest[2])
                blank = total_q - correct - wrong

                net = _safe_float(rest[3]) if len(rest) > 3 else 0.0
                success_pct = _safe_float(rest[4]) if len(rest) > 4 else 0.0

                subjects.append(
                    {
                        "subject_name": subject_name.strip(),
                        "total_questions": total_q,
                        "correct": correct,
                        "wrong": wrong,
                        "blank": blank,
                        "net": net,
                        "success_pct": success_pct,
                        "is_total_row": False,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Özet tablo satırı parse edilemedi: '{text[:60]}' — {exc}")

        return subjects

    def _detect_subject_name(self, text: str) -> str:
        """Satırın ders adıyla başlayıp başlamadığını kontrol eder.

        Eşleşme varsa ders adını (string) döndürür; yoksa boş string döner.
        Uzun prefix'ler önce denenir (örn. 'Din Kül. ve Ahl. Bil.' > 'Din').
        """
        # Uzunluğa göre sırala (uzun prefix önce — greedy eşleşme için)
        for prefix in sorted(_SUBJECT_PREFIXES, key=len, reverse=True):
            if text.startswith(prefix):
                return prefix
        return ""

    # ── Özel: Sağ sütun parser'ı ─────────────────────────────────────────────

    def _parse_analysis_section(
        self,
        rows: list[list[dict[str, Any]]],
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        """Sağ sütundaki 'DERSLERE GÖRE BAŞARI ANALİZİ' bölümünü çeker.

        Hiyerarşi: Ders başlığı → Konu/Kazanım satırları

        Her kazanım satırı format:
            <Konu/Kazanım Adı>  <Soru>  <Doğru>  <Yanlış>  <Başarı%>

        Returns:
            [
                {
                    "subject_name": str,
                    "outcome_description": str,
                    "total_questions": int,
                    "correct": int,
                    "wrong": int,
                    "blank": int,
                    "success_pct": float,   # negatif olabilir
                },
                ...
            ]
        """
        outcomes: list[dict[str, Any]] = []
        current_subject = ""

        for row in rows:
            text = _row_to_text(row)
            stripped = text.strip()

            if not stripped:
                continue

            # ── Başlık satırları atla ────────────────────────────────────────
            # "DERSLERE GÖRE BAŞARI ANALİZİ"
            if "DERSLERE GÖRE BAŞARI" in stripped:
                continue
            # "S D Y B%" sütun başlığı
            if re.match(r"^S\s+D\s+Y\s+B%?\s*$", stripped):
                continue
            # "Cevap Anahtarı" satırları
            if _should_skip_line(stripped):
                continue

            # ── Ders başlığı mı? ────────────────────────────────────────────
            # Sağ sütunda ders başlıkları şu formattadır:
            #   "Türkçe 402216 55"     (NumNo + Sınıf kodu)
            #   "Tarih-1 5 2 3 40"     (Soru+Doğru+Yanlış+Başarı% — 4 rakam)
            #   "TYT Sosyal 25127 48"
            # Ortak özellik: metin + 2-3 kısa sayısal token (sınıf no gibi) VE
            # sağ sütunun son 4 rakamı S D Y B% quadruple'ı değil.
            subject_match = self._detect_analysis_subject_header(stripped)
            if subject_match:
                current_subject = subject_match
                continue

            # ── Kazanım/Konu satırı mı? ─────────────────────────────────────
            # Son 4 token: Soru Doğru Yanlış Başarı% (son negatif olabilir)
            outcome = self._parse_outcome_row(stripped, current_subject, warnings)
            if outcome:
                outcomes.append(outcome)

        return outcomes

    def _detect_analysis_subject_header(self, text: str) -> str:
        """Sağ sütunda ders başlığı satırını tanır; ders adını döndürür.

        Ders başlığı: <DersAdı> <NumNo veya rakamlar>  (outcome quadruple yok)
        Kazanım satırı: <Açıklama> S D Y B%  (4 sayı ile biter)

        Ders adı 'Türkçe', 'Tarih-1' vb. ile başlamalı.
        """
        # 'TYT X' prefix'li olanlar — grup satırı (TYT Sosyal, TYT Türkçe vb.)
        tyt_group = re.match(r"^TYT\s+(Türkçe|Sosyal|Matematik|Fen)\s+\d+\s+\d+\s*$", text)
        if tyt_group:
            return f"TYT {tyt_group.group(1)}"

        # Ders başlığı: bilinen bir prefix ile başlıyor
        for prefix in sorted(_SUBJECT_PREFIXES, key=len, reverse=True):
            if text.startswith(prefix):
                # Geri kalan token'lar SADECE rakam olmalı (2-4 adet)
                rest = text[len(prefix) :].strip()
                rest_tokens = rest.split()
                if rest_tokens and all(re.match(r"^-?\d+$", t) for t in rest_tokens) and len(rest_tokens) <= 4:
                    return prefix.strip()

        return ""

    def _parse_outcome_row(
        self,
        text: str,
        current_subject: str,
        warnings: list[str],
    ) -> dict[str, Any] | None:
        """Tek bir konu/kazanım satırını parse eder.

        Format: <Açıklama> <Soru> <Doğru> <Yanlış> <Başarı%>
        Başarı% negatif olabilir.

        Returns:
            Outcome sözlüğü veya None (tanınamayan satır).
        """
        tokens = text.split()
        if len(tokens) < 5:
            return None

        # Son 4 token'ın sayısal olduğunu kontrol et
        # Başarı% negatif olabilir
        try:
            b_pct = float(tokens[-1])  # Başarı%
            wrong = int(tokens[-2])  # Yanlış
            correct = int(tokens[-3])  # Doğru
            total_q = int(tokens[-4])  # Soru
        except ValueError:
            return None

        # Negatif sayılar için doğrulama: Soru ve sayılar >= 0 olmalı,
        # ama Başarı% ve (nadir de olsa) net negatif olabilir.
        if total_q < 0 or correct < 0 or wrong < 0:
            return None

        description = " ".join(tokens[:-4]).strip()
        if not description:
            return None

        blank = total_q - correct - wrong
        # Boş negatif çıkabilir (veri hatası) — uyarı ekle ama kaydet
        if blank < 0:
            warnings.append(
                f"Ders '{current_subject}', kazanım '{description[:40]}': "
                f"Boş={blank} < 0 (Soru={total_q}, D={correct}, Y={wrong}). "
                "Veri tutarsız, blank=0 olarak işaretlendi."
            )
            blank = 0

        return {
            "subject_name": current_subject,
            "outcome_description": description,
            "total_questions": total_q,
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "success_pct": b_pct,
            "measured": total_q > 0,
        }

    # ── Özel: Normalize yardımcısı ────────────────────────────────────────────

    def _normalize_student(self, raw_s: dict[str, Any]) -> dict[str, Any]:
        """Tek öğrencinin ham verisini NormalizedExamData öğrenci formatına çevirir.

        analysis_subjects (kazanım detayı) varsa bunu kullanır;
        yoksa summary_subjects'ten fallback üretir.
        """
        full_name = raw_s.get("full_name", "")
        student_code = raw_s.get("student_code", "")
        analysis: list[dict[str, Any]] = raw_s.get("analysis_subjects", [])
        summary: list[dict[str, Any]] = raw_s.get("summary_subjects", [])

        subject_results: list[dict[str, Any]] = []

        if analysis:
            for item in analysis:
                subject_results.append(
                    {
                        "subject_name": item.get("subject_name", ""),
                        "topic_name": item.get("outcome_description", ""),
                        "outcome_code": None,
                        "outcome_description": item.get("outcome_description", ""),
                        "correct": item.get("correct", 0),
                        "wrong": item.get("wrong", 0),
                        "blank": item.get("blank", 0),
                        "total_questions": item.get("total_questions", 0),
                        "success_pct": item.get("success_pct", 0.0),
                        "measured": item.get("measured", True),
                    }
                )
        else:
            # Fallback: sadece özet tablo verisi var
            for item in summary:
                if item.get("is_total_row"):
                    continue
                total_q = item.get("total_questions", 0)
                subject_results.append(
                    {
                        "subject_name": item.get("subject_name", ""),
                        "topic_name": "",
                        "outcome_code": None,
                        "outcome_description": "",
                        "correct": item.get("correct", 0),
                        "wrong": item.get("wrong", 0),
                        "blank": item.get("blank", 0),
                        "total_questions": total_q,
                        "success_pct": item.get("success_pct", 0.0),
                        "measured": total_q > 0,
                    }
                )

        return {
            "student_code": student_code,
            "full_name": full_name,
            "student_class": raw_s.get("student_class", ""),
            "tyt_score": raw_s.get("tyt_score"),
            "subject_results": subject_results,
        }
